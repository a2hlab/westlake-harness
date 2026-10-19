"""SDK LLDB15 engine. Called by observe.py inside pinned SDK host, never imported by HDC."""
import json, signal, time, traceback
from pathlib import Path
from core import *
from identity import Guard

class Session:
    def __init__(self,L,debugger,a,out,guard_factory=Guard,clock=time.monotonic):
        self.L=L;self.db=debugger;self.a=a;self.out=Path(out);self.clock=clock
        self.start=clock();self.deadline=min(self.start+MAX_SECONDS,self.start+max(0,a['expires_at']-time.time()))
        self.guard=guard_factory(a,out,self.deadline);self.target=None;self.proc=None;self.owned={};self.calls=Calls();self.rows=[];self.selected={};self.cancel=False;self.resume_stop_id=None;self.ignored=0
        self.result={'schema':'r11-result-v1','playback':'UNKNOWN_NOT_TESTED','audio':'UNKNOWN','events':[],'tool_version':L.SBDebugger.GetVersionString(),'requested_identity':a['identity'],'limits':{'seconds':120,'fromSurface':4,'lock':4},'cleanup':{'verified':False,'outer_recovery_required':True}}
    def emit(self,e):
        e['elapsed_s']=self.clock()-self.start;self.result['events'].append(e)
        with (self.out/'events.jsonl').open('a') as f:f.write(json.dumps(e)+'\n');f.flush()
    def command(self,text):
        ret=self.L.SBCommandReturnObject();self.db.GetCommandInterpreter().HandleCommand(text,ret)
        with (self.out/'lldb-commands.jsonl').open('a') as f:f.write(json.dumps({'command':text,'success':ret.Succeeded(),'stdout':ret.GetOutput(),'stderr':ret.GetError()})+'\n')
        need(ret.Succeeded(),'LLDB command '+text+': '+str(ret.GetError()));return ret
    def remaining(self):need(not self.cancel,'interrupted');need(self.clock()<self.deadline,'observation deadline')
    def checked_identity(self,phase):
        self.remaining();v=self.guard.capture(phase);self.rows=v['rows']
        if self.proc is not None:need(self.proc.GetProcessID()==self.a['identity']['child'],'LLDB PID drift')
        return v
    def read(self,addr,size):
        need(len(containing(self.rows,addr,size))==1,'unreadable or ambiguous address')
        err=self.L.SBError();b=self.proc.ReadMemory(addr,size,err)
        need(err.Success() and isinstance(b,(bytes,bytearray)) and len(b)==size,'memory read error/short: '+str(err.GetCString()))
        return bytes(b)
    def reg(self,frame,name):
        v=frame.FindRegister(name);need(v.IsValid() and v.GetError().Success(),'register unavailable '+name)
        err=self.L.SBError();n=v.GetValueAsUnsigned(err,0);need(err.Success(),'register error '+name);return n
    def module(self,address):
        hits=[]
        for role,m in self.a['modules'].items():
            if any(r['lo']<=address<r['hi'] and 'x' in r['perms'] for r in mapped_module(self.rows,m)):
                valid=[b for b in biases(self.rows,m) if any(b+va<=address<b+va+(end-off) and flags&1 for off,va,end,flags in segments(m['local_path']))]
                need(len(valid)==1,'winner/caller ELF bias ambiguous')
                hits.append({'role':role,'sha256':m['sha256'],'device':m['device'],'inode':m['inode'],'bias':hex(valid[0]),'elf_address':hex(address-valid[0]),'address':hex(address)})
        need(len(hits)==1,'unadmitted executable pointer');return hits[0]
    def prepare_addresses(self):
        p=self.a['modules']['player'];bs=biases(self.rows,p);need(len(bs)==1,'ambiguous player instance');pb=bs[0]
        for role,slot,expected,pc in [('android',0x472688,0x3b9c,0x3bd4),('shim',0x472490,0x5e48,0x5e48)]:
            actual=int.from_bytes(self.read(pb+slot,8),'little');winner=self.module(actual)
            need(winner['role']==role and int(winner['elf_address'],16)==expected,'actual player GOT drift '+role)
            self.selected[role]=int(winner['bias'],16)+pc
            self.emit({'kind':'actual_binding','slot':hex(pb+slot),'provider':winner})
    def add_bp(self,kind,address,tid=None):
        self.remaining();before={self.target.GetBreakpointAtIndex(i).GetID() for i in range(self.target.GetNumBreakpoints())}
        cmd='breakpoint set --hardware --address '+hex(address)
        if tid is not None:cmd+=' --thread-id '+str(tid)
        # Record newly created IDs even if command fails, for cleanup.
        try:self.command(cmd)
        finally:
            for i in range(self.target.GetNumBreakpoints()):
                bp=self.target.GetBreakpointAtIndex(i)
                if bp.GetID() not in before:self.owned[bp.GetID()]={'kind':kind,'address':address,'tid':tid}
        new=set(self.owned)-before;need(len(new)==1,'unexpected new breakpoint count')
        bid=new.pop();bp=self.target.FindBreakpointByID(bid)
        need(bp.IsValid() and bp.IsHardware() and bp.GetNumLocations()==1,'not exact hardware breakpoint')
        loc=bp.GetLocationAtIndex(0);need(loc.IsResolved() and loc.GetLoadAddress()==address,'breakpoint unresolved/moved')
        return bid
    def delete_bp(self,bid):
        bp=self.target.FindBreakpointByID(bid)
        if bp.IsValid():need(self.target.BreakpointDelete(bid),'BreakpointDelete failed')
        self.owned.pop(bid,None)
    def wait_stop(self,deadline):
        L=self.L;listener=self.db.GetListener()
        while self.clock()<deadline:
            state=self.proc.GetState()
            if state==L.eStateStopped and (self.resume_stop_id is None or self.proc.GetStopID()>self.resume_stop_id):return
            need(state not in (L.eStateExited,L.eStateDetached,L.eStateInvalid,L.eStateCrashed),'process not inspectable: '+str(state))
            ev=L.SBEvent()
            if not listener.WaitForEvent(1,ev):continue
            if not L.SBProcess.EventIsProcessEvent(ev):continue
            p=L.SBProcess.GetProcessFromEvent(ev)
            need(p.GetUniqueID()==self.proc.GetUniqueID() and p.GetProcessID()==self.a['identity']['child'],'foreign process event')
            if L.SBProcess.GetRestartedFromEvent(ev):continue
            if L.SBProcess.GetStateFromEvent(ev)==L.eStateStopped and self.proc.GetState()==L.eStateStopped and (self.resume_stop_id is None or self.proc.GetStopID()>self.resume_stop_id):return
        raise Refuse('wait stopped timeout')
    def resume(self):
        self.remaining();self.resume_stop_id=self.proc.GetStopID();err=self.proc.Continue();need(err.Success(),'Continue: '+str(err.GetCString()))
    def stopped_events(self):
        L=self.L;hits=[]
        for i in range(self.proc.GetNumThreads()):
            t=self.proc.GetThreadAtIndex(i);why=t.GetStopReason()
            if why in (L.eStopReasonNone,L.eStopReasonInvalid):continue
            need(why==L.eStopReasonBreakpoint,'unexpected stop reason '+str(why))
            n=t.GetStopReasonDataCount();need(n>0 and n%2==0,'stop reason pairs')
            for j in range(0,n,2):
                bid=t.GetStopReasonDataAtIndex(j);locid=t.GetStopReasonDataAtIndex(j+1)
                need(bid in self.owned,'unowned breakpoint stop')
                hits.append((t,bid,locid))
        need(bool(hits),'stopped without owned breakpoint');return hits
    def on_hit(self,t,bid,locid):
        meta=self.owned[bid];frame=t.GetFrameAtIndex(0);need(frame.IsValid(),'frame missing')
        tid=t.GetThreadID();pc=self.reg(frame,'pc');sp=self.reg(frame,'sp');need(pc==meta['address'],'wrong breakpoint PC')
        bp=self.target.FindBreakpointByID(bid);loc=bp.GetLocationAtIndex(0);need(loc.GetID()==locid and bp.IsHardware(),'breakpoint location/type')
        if meta['tid'] is not None:need(tid==meta['tid'],'return thread mismatch')
        # Persist raw registers before classification; unknown pointers are evidence.
        raw={'kind':'raw_hit','breakpoint_kind':meta['kind'],'tid':tid,'pc':hex(pc),'sp':hex(sp),'stop_id':self.proc.GetStopID()}
        for name in ('x0','x2','x30'):raw[name]=hex(self.reg(frame,name))
        self.emit(raw)
        event={'kind':meta['kind'],'tid':tid,'pc':hex(pc),'sp':hex(sp),'pc_module':self.module(pc),'stop_id':self.proc.GetStopID()}
        ret=int(raw['x30'],16)
        if meta['kind'] in ('fromSurface_tailcall','lock_entry'):
            try:caller=self.module(ret)
            except Refuse:caller={'role':'unknown','address':hex(ret)}
            if caller['role']!='player':
                self.ignored+=1;self.emit({'kind':'ignored_nonplayer','caller':caller,'raw':raw,'count':self.ignored})
                need(self.ignored<16,'ignored caller limit');return
        if meta['kind']=='fromSurface_tailcall':
            winner=int(raw['x2'],16)
            try:event['winner']=self.module(winner)
            except Refuse as ex:
                event['winner']={'address':hex(winner),'classification':'unknown','reason':str(ex)}
                self.emit(event);raise
            p=self.calls.tail(tid,sp,ret,winner);event.update({'call_seq':p['seq'],'return_pc':hex(ret),'x2':hex(winner)})
            self.add_bp('fromSurface_return',ret,tid)
            if self.calls.from_count==MAX_FROM:bp.SetEnabled(False)
        elif meta['kind']=='fromSurface_return':
            p=self.calls.returned(tid,sp,pc);value=int(raw['x0'],16)
            event.update({'call_seq':p['seq'],'object':wrapper(self.read,value),'winner_address':hex(p['winner'])});self.delete_bp(bid)
        elif meta['kind']=='lock_entry':
            event.update({'lock_seq':self.calls.lock(),'caller':caller,'object':wrapper(self.read,int(raw['x0'],16)),'cross_event_object_identity':'unknown'})
            if self.calls.lock_count==MAX_LOCK:bp.SetEnabled(False)
        self.emit(event)
    def cleanup(self):
        c=self.result['cleanup'];c.update({'breakpoints_deleted':False,'detached':False,'verified':False})
        try:
            if self.proc is None or not self.proc.IsValid():
                # Connect may have failed while server already owns the child: never claim clean.
                c['error']='no valid LLDB process; outer owns server/attach recovery';return
            if self.proc.GetState()!=self.L.eStateStopped:
                self.proc.SendAsyncInterrupt();self.resume_stop_id=None;self.wait_stop(self.clock()+5)
            for bid in list(self.owned):self.delete_bp(bid)
            c['breakpoints_deleted']=True
        except Exception as ex:c['breakpoint_cleanup_error']=str(ex)
        finally:
            if self.proc is not None and self.proc.IsValid():
                try:
                    self.command('process detach --keep-stopped false');c['detached']=self.proc.GetState()==self.L.eStateDetached; c['detach_error']=None
                except Exception as ex:c['detach_error']=str(ex)
            try:
                proof=self.guard.capture('after-detach',after=True);c['external_identity']= {k:v for k,v in proof.items() if k!='rows'}
                c['verified']=c['detached'] and c['breakpoints_deleted'] and proof['tracer_pid']==0 and proof['state'] not in ('T','t')
            except Exception as ex:c['external_verify_error']=str(ex)
            c['outer_recovery_required']=not c.get('verified',False)
    def run(self,port):
        try:
            self.checked_identity('pre-connect')
            self.db.SetAsync(True)
            self.command('settings set target.require-hardware-breakpoint true')
            self.command('settings set plugin.process.gdb-remote.packet-timeout 5')
            self.command('settings set target.process.disable-memory-cache true')
            self.command('platform select remote-ohos')
            self.target=self.db.CreateTargetWithFileAndArch('', 'aarch64');need(self.target.IsValid(),'target creation')
            need(self.target.GetPlatform().GetName()=='remote-ohos','wrong target platform')
            self.emit({'kind':'target_platform','name':self.target.GetPlatform().GetName(),'triple':self.target.GetTriple()})
            self.db.SetSelectedTarget(self.target)
            err=self.L.SBError();self.proc=self.target.ConnectRemote(self.db.GetListener(),'connect://127.0.0.1:'+str(port),'gdb-remote',err)
            need(err.Success() and self.proc.IsValid(),'connect: '+str(err.GetCString()))
            need(self.proc.GetProcessID()==self.a['identity']['child'],'wrong attached PID')
            self.wait_stop(min(self.deadline,self.clock()+8));self.checked_identity('attached-stopped')
            self.prepare_addresses();self.add_bp('fromSurface_tailcall',self.selected['android']);self.add_bp('lock_entry',self.selected['shim'])
            self.resume()
            while not self.calls.complete():
                self.remaining();self.wait_stop(self.deadline);self.checked_identity('event-stopped')
                hits=self.stopped_events()
                for t,bid,locid in hits:self.on_hit(t,bid,locid)
                if not self.calls.complete():self.resume()
            self.result['exit_reason']='event_budget_complete'
        except Exception as ex:
            self.result['exit_reason']='stopped_or_refused';self.result['error']=str(ex)
            (self.out/'exception.txt').write_text(traceback.format_exc())
        finally:
            self.result['observation_elapsed_s']=self.clock()-self.start
            self.cleanup();self.result['fromSurface_count']=self.calls.from_count;self.result['lock_count']=self.calls.lock_count
            self.result['pending_return']=self.calls.pending
            self.result['status']='OBSERVATION_ONLY' if self.result['cleanup']['verified'] else 'OUTER_RECOVERY_REQUIRED'
            self.result['same_object_generation']='UNKNOWN_NOT_TRACKED'
            (self.out/'result.json').write_text(json.dumps(self.result,indent=2)+'\n')
        return self.result

def entry(admission,out,port):
    import lldb
    a=json.loads(Path(admission).read_text());validate(a)
    s=Session(lldb,lldb.debugger,a,out)
    def cancel(signum,frame):s.cancel=True;s.deadline=min(s.deadline,time.monotonic())
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    result=s.run(port)
    if not result['cleanup']['verified']:
        # Do not run LLDB's later implicit quit/process teardown on unknown attachment.
        # Persistent result requires outer server/target recovery; only this host exits.
        import os,sys
        sys.stdout.flush();sys.stderr.flush();os._exit(2)
