import copy,json,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from policy import *
from guard import Guard
from engine import Engine
HERE=Path(__file__).resolve().parent

def admission():
 root='/data/local/tmp/wl-debug-compat-00000000-0123456789abcdef'
 return {'schema':'r12-admission-v1','execution_enabled':True,'approved_by':'outer(codex)','serial':SERIAL,'port':5039,'boot':'00000000-0000-0000-0000-000000000001','created_at':1000,'expires_at':1600,'remote_root':root,'kernel':'Linux fixture aarch64','selinux':'Permissive','holder':'outer(codex) 20 time','host':{'path':'unknown','sha256':HOST_SHA},'hdc':{'path':'unknown','sha256':'1'*64},'lock_script':{'path':'unknown','sha256':'2'*64},'probe':{'pid':123,'birth':12,'uid':0,'remote_path':root+'/probe','local_path':str(HERE/'payload/probe'),'sha256':PROBE_SHA,'device':66352,'inode':55},'server':{'pid':124,'birth':13,'uid':0,'remote_path':root+'/lldb-server','sha256':SERVER_SHA,'device':66352,'inode':56}}
def table(inode=None):
 return 'sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n'+('0: 0100007F:13AF 00000000:0000 0A 00000000:00000000 00:00000000 00000000 0 0 '+str(inode)+'\n' if inode else '')
def statline(pid,birth):return f'{pid} (r12) '+ ' '.join(['S','1']+['0']*17+[str(birth)])
def maps(a):
 b=(HERE/'payload/probe').read_bytes();off=struct.unpack_from('<Q',b,32)[0];sz,n=struct.unpack_from('<HH',b,54);out=[]
 for i in range(n):
  typ,flags,fo,va,_,fs,ms,al=struct.unpack_from('<IIQQQQQQ',b,off+i*sz)
  if typ!=1 or not fs:continue
  start=0x700000+(va&~4095);end=0x700000+((va+fs+4095)&~4095);major,minor=linux_dev(a['probe']['device'])
  out.append(f'{start:x}-{end:x} '+('r-xp' if flags&1 else 'rw-p')+f' {fo&~4095:08x} {major:x}:{minor:x} 55 '+a['probe']['remote_path'])
 return '\n'.join(out)
def live(a,drift=None,after=False):
 d={'BOOT':a['boot'],'BOOT_END':a['boot'],'KERNEL':a['kernel'],'SELINUX':a['selinux'],'MAPS':maps(a),'COUNTS':'R12_COUNT 1\nR12_COUNT 2','TCP':table(999),'TCP6':table(),'FDS':'socket:[999]'}
 for role in ['probe'] if after else ['probe','server']:
  r=a[role];d[role+'_STAT']=d[role+'_END']=statline(r['pid'],r['birth']);d[role+'_STATUS']='Uid: 0 0 0 0\nTracerPid: '+str(0 if after or role=='server' else 124)
  argv=[r['remote_path']] if role=='probe' else [r['remote_path'],'gdbserver','127.0.0.1:5039','--attach','123']
  d[role+'_CMD']=(b'\0'.join(x.encode() for x in argv)+b'\0').hex();d[role+'_EXE']=r['remote_path'];d[role+'_SHA']=r['sha256']+' path';d[role+'_INODE']=f'{r["device"]}:{r["inode"]}'
 if drift:d.update(drift)
 return ('\n'.join('R12_'+k+'\n'+v for k,v in d.items())+'\nR12_RC=0\n').encode()

class Guards(unittest.TestCase):
 def test_default_cli_zero_calls(self):
  import observe
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a';p.write_text(json.dumps(admission()))
   with patch.object(sys,'argv',['observe','--admission',str(p),'--out',str(Path(d)/'out')]),patch('observe.subprocess.Popen') as run:
    self.assertEqual(observe.main(),2);run.assert_not_called()
 def test_fixed_identity_and_budget(self):
  a=admission();validate(a,now=1001,files=False)
  for k,v in [('execution_enabled',False),('max_seconds',61),('max_hits',3),('serial','61b'),('port',5040),('remote_root','/data/local/tmp/existing')]:
   b=copy.deepcopy(a);b[k]=v
   with self.subTest(k=k),self.assertRaises((Refuse,KeyError)):validate(b,now=1001,files=False)
  for role,key,v in [('probe','sha256','1'*64),('server','sha256',SERVER_SHA[:8]),('probe','birth',None),('host','sha256',None)]:
   b=copy.deepcopy(a);b[role][key]=v
   with self.subTest(role=role,key=key),self.assertRaises((Refuse,KeyError)):validate(b,now=1001,files=False)
 def test_actual_preflight_port_and_old_pid(self):
  with tempfile.TemporaryDirectory() as d:
   a=admission();p=Path(d)/'pre'
   for change in [None,{'TCP':table(900)},{'ROOT':'PRESENT'},{'PIDS':'/proc/1 /proc/123'}]:
    rows={'BOOT':a['boot'],'BOOT_END':a['boot'],'KERNEL':a['kernel'],'SELINUX':a['selinux'],'ROOT':'ABSENT','TCP':table(),'TCP6':table(),'PIDS':'/proc/1 /proc/2'}
    if change:rows.update(change)
    p.write_text('\n'.join('R12_'+k+'\n'+v for k,v in rows.items())+'\nR12_RC=0\n');a['preflight']={'path':str(p),'sha256':sha(p)}
    if change:
     with self.assertRaises(Refuse):preflight(a)
    else:preflight(a)
 def test_runtime_guard_real_parser(self):
  a=admission()
  for drift in [None,{'BOOT_END':'other'},{'probe_END':statline(123,999)},{'server_CMD':b'foreign\0'.hex()},{'FDS':'socket:[888]'},{'probe_SHA':'0'*64+' file'},{'probe_STATUS':'Uid: 0 0 0 0\nTracerPid: 0'}]:
   with tempfile.TemporaryDirectory() as d:
    replies=[NS(returncode=0,stdout=a['holder'].encode(),stderr=b''),NS(returncode=0,stdout=live(a,drift),stderr=b'')]
    with patch('guard.subprocess.run',side_effect=replies) as run:
     g=Guard(a,d,10**12)
     if drift:
      with self.assertRaises(Refuse):g.capture('pre-connect')
     else:self.assertEqual(g.capture('pre-connect')['marker'],0x700000+MARKER)
     self.assertEqual(run.call_args.args[0][1:3],['-t',SERIAL]);self.assertIn('od -An -v -tx1',run.call_args.args[0][-1])
class Events(unittest.TestCase):
 def test_actual_elf_and_mapping(self):
  self.assertEqual(sha(HERE/'payload/probe'),PROBE_SHA);self.assertEqual(marker(HERE/'payload/probe'),MARKER);a=admission();self.assertEqual(mapped_marker(maps(a),a),0x700000+MARKER)
  with self.assertRaises(Refuse):mapped_marker(maps(a).replace(' 55 ',' 77 '),a)
 def test_real_hit_decision(self):
  h=Hits();h.add(10,100,2,4,100,3);h.add(10,100,3,6,100,4)
  with self.assertRaises(Refuse):h.add(10,100,4,7,100,6)
  for row in [(11,100,3,6),(10,101,3,6),(10,100,2,6),(10,100,3,4)]:
   h=Hits();h.add(10,100,2,4,100,3)
   with self.assertRaises(Refuse):h.add(*row,100,4)
class Error:
 def Success(self):return True
 def GetCString(self):return None
class Cleanup(unittest.TestCase):
 def bare(self,d):
  e=Engine.__new__(Engine);e.out=Path(d);e.a=admission();e.owned={1};e.r={'cleanup':{}};e.resume_id=None;e.deadline=100;e.hits=Hits();e.sleep=lambda _:None
  ticks=[0]
  def clock():ticks[0]+=.1;return ticks[0]
  e.clock=clock;e.L=NS(eStateStopped=1,eStateDetached=2,eStateInvalid=3,eStateExited=4,eStateCrashed=5,SBEvent=lambda:None,SBProcess=NS(EventIsProcessEvent=lambda _:False))
  return e
 def test_stale_stop_after_continue(self):
  with tempfile.TemporaryDirectory() as d:
   e=self.bare(d);p=NS(stop=3,GetStopID=lambda:p.stop,GetState=lambda:1,Continue=lambda:Error());e.proc=p;e.resume()
   def wait(*_):p.stop=4;return False
   e.db=NS(GetListener=lambda:NS(WaitForEvent=wait));e.wait(10);self.assertEqual(p.stop,4)
   p.stop=3;e.db=NS(GetListener=lambda:NS(WaitForEvent=lambda *_:False))
   with self.assertRaises(Refuse):e.wait(e.clock()+.3)
 def test_cleanup_needs_detach_and_counter_progress(self):
  for advance,deleted in [(True,True),(False,True),(True,False)]:
   with tempfile.TemporaryDirectory() as d:
    e=self.bare(d);state=[1];e.proc=NS(IsValid=lambda:True,GetState=lambda:state[0]);e.target=NS(FindBreakpointByID=lambda _:NS(IsValid=lambda:True),BreakpointDelete=lambda _:deleted)
    cmds=[]
    def command(c):cmds.append(c);state[0]=2
    e.command=command;rs=iter([{'last_count':5},{'last_count':6 if advance else 5}]);e.guard=NS(capture=lambda *_,**kw:next(rs));e.cleanup()
    self.assertEqual(cmds,['process detach --keep-stopped false']);self.assertEqual(e.r['cleanup']['verified'],advance and deleted)
 def test_software_breakpoint_refused_owned_retained(self):
  with tempfile.TemporaryDirectory() as d:
   e=self.bare(d);e.owned=set();bs=[];e.target=NS(GetNumBreakpoints=lambda:len(bs),GetBreakpointAtIndex=lambda i:bs[i],FindBreakpointByID=lambda _:bs[0])
   def cmd(c):self.assertIn('--hardware',c);bs.append(NS(GetID=lambda:7,IsValid=lambda:True,IsHardware=lambda:False,GetNumLocations=lambda:1))
   e.command=cmd
   with self.assertRaises(Refuse):e.install(0x100)
   self.assertEqual(e.owned,{7})
class Runtime(unittest.TestCase):
 def test_real_engine_two_hits_and_failure_paths(self):
  import time
  for variant in ['ok','flat_counter','software','connect_fail']:
   with self.subTest(variant=variant),tempfile.TemporaryDirectory() as d:
    a=admission();a['expires_at']=time.time()+300;commands=[];bps=[]
    class Ret:
     def Succeeded(self):return True
     def GetOutput(self):return ''
     def GetError(self):return ''
    class Process:
     state=1;stop=10;count=1
     def IsValid(self):return variant!='connect_fail'
     def GetState(self):return self.state
     def GetProcessID(self):return 123
     def GetStopID(self):return self.stop
     def Continue(self):self.stop+=1;self.count+=0 if variant=='flat_counter' else 1;return Error()
     def GetNumThreads(self):return 1
     def GetThreadAtIndex(self,i):
      def register(name):
       value=0x701af0 if name=='pc' else self.count
       return NS(IsValid=lambda:True,GetError=lambda:Error(),GetValueAsUnsigned=lambda *args:value)
      frame=NS(IsValid=lambda:True,FindRegister=register)
      return NS(GetStopReason=lambda:3,GetStopReasonDataCount=lambda:2,GetStopReasonDataAtIndex=lambda n:1,GetThreadID=lambda:555,GetFrameAtIndex=lambda _:frame)
    proc=Process()
    loc=NS(IsResolved=lambda:True,GetLoadAddress=lambda:0x701af0,GetID=lambda:1)
    bp=NS(GetID=lambda:1,IsValid=lambda:True,IsHardware=lambda:variant!='software',GetNumLocations=lambda:1,GetLocationAtIndex=lambda _:loc)
    def delete(i):bps.clear();return True
    target=NS(IsValid=lambda:True,GetPlatform=lambda:NS(GetName=lambda:'remote-ohos'),ConnectRemote=lambda *args:proc,GetNumBreakpoints=lambda:len(bps),GetBreakpointAtIndex=lambda i:bps[i],FindBreakpointByID=lambda i:bp,BreakpointDelete=delete)
    def command(text,ret):
     commands.append(text)
     if text.startswith('breakpoint set'):bps.append(bp)
     if text=='process detach --keep-stopped false':proc.state=2
    db=NS(GetCommandInterpreter=lambda:NS(HandleCommand=command),SetAsync=lambda _:None,CreateTargetWithFileAndArch=lambda *args:target,SetSelectedTarget=lambda _:None,GetListener=lambda:NS(WaitForEvent=lambda *args:False))
    L=NS(eStateStopped=1,eStateDetached=2,eStateInvalid=4,eStateExited=5,eStateCrashed=6,eStopReasonNone=0,eStopReasonInvalid=1,eStopReasonBreakpoint=3,SBCommandReturnObject=Ret,SBError=Error,SBDebugger=NS(GetVersionString=lambda:'fake SDK15'),SBEvent=lambda:None,SBProcess=NS(EventIsProcessEvent=lambda _:False))
    class G:
     def __init__(self,*args):self.count=0
     def capture(self,phase,after=False):self.count+=1;return {'marker':0x701af0,'last_count':self.count,'tracer':0 if after else 124,'state':'S'}
    e=Engine(L,db,a,d,guard_factory=G,sleep=lambda _:None);r=e.run()
    if variant=='ok':
     self.assertTrue(r['two_hits']);self.assertTrue(r['cleanup']['verified']);self.assertEqual(len(r['hits']),2)
     self.assertEqual(r['hits'][1]['stop_id'],12);self.assertEqual(r['hits'][1]['x0'],3)
    else:self.assertEqual(r['status'],'FAILED_OR_UNKNOWN')
    if variant!='connect_fail':self.assertIn('process detach --keep-stopped false',commands)
    self.assertLess(commands.index('platform select remote-ohos'),len(commands));self.assertTrue((Path(d)/'result.json').exists())
class Receipt(unittest.TestCase):
 def test_build_receipt_and_pins(self):
  r=json.loads((HERE/'build-public.json').read_text());self.assertEqual(r['build_rc'],0);self.assertEqual(r['probe_sha256'],PROBE_SHA);self.assertEqual(r['source_sha256'],sha(HERE/'probe.c'));self.assertEqual(r['recipe_sha256'],sha(HERE/'build_probe.py'))
if __name__=='__main__':unittest.main()
