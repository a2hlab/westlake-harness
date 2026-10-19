"""R12 SDK15 client engine; outer explicitly invokes after exact server attach."""
import json,signal,time,traceback
from pathlib import Path
from policy import *
from guard import Guard
class Engine:
 def __init__(self,L,db,a,out,guard_factory=Guard,clock=time.monotonic,sleep=time.sleep):
  self.L=L;self.db=db;self.a=a;self.out=Path(out);self.clock=clock;self.sleep=sleep;self.start=clock();self.deadline=min(self.start+60,self.start+max(0,a['expires_at']-time.time()))
  self.guard=guard_factory(a,out,self.deadline);self.target=None;self.proc=None;self.owned=set();self.resume_id=None;self.hits=Hits()
  self.r={'schema':'r12-observation-v1','status':'FAILED','toutiao':'UNKNOWN_NOT_TESTED','playback':'UNKNOWN_NOT_TESTED','host_version':L.SBDebugger.GetVersionString(),'limits':{'seconds':60,'hits':2},'cleanup':{'verified':False},'hits':self.hits.rows}
 def command(self,s):
  r=self.L.SBCommandReturnObject();self.db.GetCommandInterpreter().HandleCommand(s,r)
  with (self.out/'commands.jsonl').open('a') as f:f.write(json.dumps({'command':s,'ok':r.Succeeded(),'stdout':r.GetOutput(),'stderr':r.GetError()})+'\n')
  need(r.Succeeded(),'LLDB command failed: '+str(r.GetError()))
 def budget(self):need(self.clock()<self.deadline,'60 second deadline')
 def wait(self,end):
  L=self.L
  while self.clock()<end:
   state=self.proc.GetState()
   if state==L.eStateStopped and (self.resume_id is None or self.proc.GetStopID()>self.resume_id):return
   need(state not in (L.eStateInvalid,L.eStateDetached,L.eStateExited,L.eStateCrashed),'not inspectable')
   e=L.SBEvent()
   if self.db.GetListener().WaitForEvent(1,e) and L.SBProcess.EventIsProcessEvent(e):
    p=L.SBProcess.GetProcessFromEvent(e);need(p.GetProcessID()==self.a['probe']['pid'] and p.GetUniqueID()==self.proc.GetUniqueID(),'foreign event')
  raise Refuse('stop wait timeout')
 def resume(self):
  self.budget();self.resume_id=self.proc.GetStopID();err=self.proc.Continue();need(err.Success(),'Continue '+str(err.GetCString()))
 def guard_now(self,phase):
  self.budget();r=self.guard.capture(phase)
  if self.proc is not None:need(self.proc.GetProcessID()==self.a['probe']['pid'],'connected wrong process')
  return r
 def install(self,addr):
  old={self.target.GetBreakpointAtIndex(i).GetID() for i in range(self.target.GetNumBreakpoints())}
  try:self.command('breakpoint set --hardware --address '+hex(addr))
  finally:
   for i in range(self.target.GetNumBreakpoints()):
    b=self.target.GetBreakpointAtIndex(i)
    if b.GetID() not in old:self.owned.add(b.GetID())
  need(len(self.owned)==1,'one owned breakpoint');bid=next(iter(self.owned));b=self.target.FindBreakpointByID(bid)
  need(b.IsValid() and b.IsHardware() and b.GetNumLocations()==1,'hardware-only required');loc=b.GetLocationAtIndex(0)
  need(loc.IsResolved() and loc.GetLoadAddress()==addr,'hardware location mismatch');return bid,loc.GetID()
 def reg(self,f,name):
  v=f.FindRegister(name);need(v.IsValid() and v.GetError().Success(),'register '+name);e=self.L.SBError();n=v.GetValueAsUnsigned(e,0);need(e.Success(),'register read '+name);return n
 def hit(self,addr,bid,locid):
  found=[];L=self.L
  for i in range(self.proc.GetNumThreads()):
   t=self.proc.GetThreadAtIndex(i);why=t.GetStopReason()
   if why in (L.eStopReasonNone,L.eStopReasonInvalid):continue
   need(why==L.eStopReasonBreakpoint and t.GetStopReasonDataCount()==2,'unexpected stop')
   need((t.GetStopReasonDataAtIndex(0),t.GetStopReasonDataAtIndex(1))==(bid,locid),'foreign breakpoint')
   b=self.target.FindBreakpointByID(bid);need(b.IsHardware(),'hardware type changed');f=t.GetFrameAtIndex(0);need(f.IsValid(),'missing frame')
   raw={'pc':self.reg(f,'pc'),'x0':self.reg(f,'x0'),'tid':t.GetThreadID(),'stop_id':self.proc.GetStopID()}
   with (self.out/'raw-hits.jsonl').open('a') as o:o.write(json.dumps(raw)+'\n')
   found.append(raw)
  need(len(found)==1,'one marker hit per stop');r=found[0];self.hits.add(r['tid'],r['pc'],r['x0'],r['stop_id'],addr,self.resume_id)
 def cleanup(self):
  c=self.r['cleanup'];c.update(deleted=False,detached=False,verified=False)
  try:
   need(self.proc is not None and self.proc.IsValid(),'no connected process: outer recovery')
   if self.proc.GetState()!=self.L.eStateStopped:
    self.proc.SendAsyncInterrupt();self.resume_id=None;self.wait(self.clock()+4)
   for bid in list(self.owned):
    b=self.target.FindBreakpointByID(bid)
    if b.IsValid():need(self.target.BreakpointDelete(bid),'delete failed')
    self.owned.remove(bid)
   c['deleted']=True
  except Exception as ex:c['error']=str(ex)
  finally:
   if self.proc is not None and self.proc.IsValid():
    try:self.command('process detach --keep-stopped false');c['detached']=self.proc.GetState()==self.L.eStateDetached
    except Exception as ex:c['detach_error']=str(ex)
   try:
    one=self.guard.capture('after-detach-1',after=True);self.sleep(.6);two=self.guard.capture('after-detach-2',after=True)
    c['progress']=[one,two];c['verified']=c['deleted'] and c['detached'] and two['last_count']>one['last_count']
   except Exception as ex:c['external_error']=str(ex)
   c['outer_owned_process_recovery_required']=not c['verified']
 def run(self):
  try:
   self.guard_now('pre-connect');self.db.SetAsync(True)
   for c in ['settings set target.require-hardware-breakpoint true','settings set target.process.disable-memory-cache true','settings set plugin.process.gdb-remote.packet-timeout 4','platform select remote-ohos']:self.command(c)
   self.target=self.db.CreateTargetWithFileAndArch('','aarch64');need(self.target.IsValid() and self.target.GetPlatform().GetName()=='remote-ohos','target platform');self.db.SetSelectedTarget(self.target)
   e=self.L.SBError();self.proc=self.target.ConnectRemote(self.db.GetListener(),'connect://127.0.0.1:5039','gdb-remote',e);need(e.Success() and self.proc.IsValid(),'connect '+str(e.GetCString()));need(self.proc.GetProcessID()==self.a['probe']['pid'],'wrong attached PID')
   self.wait(min(self.deadline,self.clock()+6));g=self.guard_now('attached');addr=g['marker'];bid,locid=self.install(addr);self.r['marker']=hex(addr);self.r['hardware_breakpoint_id']=bid
   for i in range(2):
    self.resume();self.wait(self.deadline);self.guard_now('hit-'+str(i+1));self.hit(addr,bid,locid)
   self.r['two_hits']=True
  except Exception as ex:
   self.r['error']=str(ex);(self.out/'exception.txt').write_text(traceback.format_exc())
  finally:
   self.r['observation_elapsed_s']=self.clock()-self.start;self.cleanup();self.r['status']='PROBE_COMPATIBILITY_ONLY_PENDING_OUTER_FORWARD_CLEANUP' if self.r.get('two_hits') and self.r['cleanup']['verified'] else 'FAILED_OR_UNKNOWN'
   (self.out/'result.json').write_text(json.dumps(self.r,indent=2)+'\n')
  return self.r

def entry(a_path,out):
 import lldb,sys,os
 a=json.loads(Path(a_path).read_text());validate(a);engine=Engine(lldb,lldb.debugger,a,out)
 def cancel(*_):engine.deadline=engine.clock()
 signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
 r=engine.run()
 if not r['cleanup']['verified']:sys.stdout.flush();sys.stderr.flush();os._exit(2)
