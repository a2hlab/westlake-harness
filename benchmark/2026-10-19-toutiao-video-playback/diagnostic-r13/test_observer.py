import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import core
from core import *
from observer import Session
from identity import Guard

def admission():
    return {'schema':'r13-admission-v1','execution_enabled':True,'approved_by':'outer(codex)','serial':SERIAL,'created_at':1000,'expires_at':1300,'holder':'outer(codex) 123 timestamp','identity':{'boot':'00000000-0000-0000-0000-000000000001','parent':10,'parent_birth':20,'parent_uid':0,'child':11,'child_birth':21,'uid':20011206,'child_exe_sha256':EXE_SHA,'parent_exe_sha256':EXE_SHA},'server':{'pid':12,'birth':22,'uid':0,'sha256':SERVER_SHA},'host':{'path':'unknown','sha256':HOST_SHA},'hdc':{'path':'unknown','sha256':'1'*64},'lock_script':{'path':'unknown','sha256':'2'*64},'modules':{k:{'local_path':'unknown','remote_path':'/data/'+k+'.so','sha256':v,'device':66352,'inode':100+i} for i,(k,v) in enumerate(PINS.items())}}

class Identity(unittest.TestCase):
    def test_old_server_and_schema_refused(self):
        a=admission();validate(a,now=1001,files=False)
        a['server']['sha256']='d6d9a233fd3b9bd2ff60a69eec78aa2e70eaf4d94b98e0cbb55fae90706fb229'
        with self.assertRaisesRegex(Refuse,'tool pin'):validate(a,now=1001,files=False)
        a=admission();a['schema']='r11-admission-v1'
        with self.assertRaisesRegex(Refuse,'authorization'):validate(a,now=1001,files=False)
    def test_admission_fixed_values(self):
        a=admission();validate(a,now=1001,files=False)
        mutations=[('max_seconds',121),('max_fromSurface',5),('max_lock',5),('serial','other'),('execution_enabled',False)]
        for k,v in mutations:
            b=copy.deepcopy(a);b[k]=v
            with self.subTest(key=k),self.assertRaises(Refuse):validate(b,now=1001,files=False)
        for owner,key,value in [('host','sha256',None),('server','sha256',SERVER_SHA[:8]),('identity','parent_uid',20011206),('identity','child_birth',None),('identity','child_exe_sha256','0'*64),('identity','parent_uid',False)]:
            b=copy.deepcopy(a);b[owner][key]=value
            with self.subTest(key=key),self.assertRaises((Refuse,TypeError)):validate(b,now=1001,files=False)
        b=copy.deepcopy(a);b['modules']['shim']['sha256']=PINS['shim'][:8]
        with self.assertRaises(Refuse):validate(b,now=1001,files=False)
        del b['identity']['parent']
        with self.assertRaises((KeyError,Refuse)):validate(b,now=1001,files=False)
    def test_actual_file_sha_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'not-elf';p.write_text('wrong')
            a=admission()
            for m in a['modules'].values():m['local_path']=str(p)
            with self.assertRaisesRegex(Refuse,'local module'):validate(a,now=1001)
    def test_return_association_budget(self):
        c=Calls();c.tail(8,100,200,300)
        for vals in [(9,100,200),(8,101,200),(8,100,201)]:
            with self.assertRaises(Refuse):c.returned(*vals)
            self.assertIsNotNone(c.pending)
        c.returned(8,100,200)
        for _ in range(3):c.tail(8,100,200,300);c.returned(8,100,200)
        with self.assertRaises(Refuse):c.tail(8,100,200,300)
        for _ in range(4):c.lock()
        with self.assertRaises(Refuse):c.lock()
        self.assertTrue(c.complete())
    def test_magic_order_unknown(self):
        calls=[]
        def read(a,n):calls.append((a,n));return {100:(0x5f776e64).to_bytes(4,'little'),300:(0x414e5731).to_bytes(4,'little'),292:(999).to_bytes(8,'little')}[a]
        self.assertEqual(wrapper(read,100)['class'],'AdapterAnw_layout_matches');self.assertEqual(calls,[(100,4),(300,4),(292,8)])
        calls.clear()
        def wrong(a,n):calls.append(a);return b'\x00'*n
        self.assertEqual(wrapper(wrong,100)['reason'],'magic_mismatch');self.assertEqual(calls,[100])
        self.assertEqual(wrapper(lambda *_:(_ for _ in ()).throw(OSError('EIO')),100)['reason'],'read_failed')
    def test_live_guard_bookends(self):
        a=admission()
        def stat(pid,ppid,birth,state='S'):return f'{pid} (name with space) '+ ' '.join([state,str(ppid)]+['0']*17+[str(birth)])
        def payload(drift=None):
            d={'BOOT':a['identity']['boot'],'BOOT_END':a['identity']['boot'],'SERVER_SHA':SERVER_SHA+' exe','PARENT_EXE':EXE_SHA+' exe','CHILD_EXE':EXE_SHA+' exe'}
            for name,pid,ppid,birth,uid in [('PARENT',10,1,20,0),('CHILD',11,10,21,20011206),('SERVER',12,1,22,0)]:
                d[name+'_STAT']=d[name+'_END']=stat(pid,ppid,birth)
                d[name+'_STATUS']=f'Uid:\t{uid}\t{uid}\t{uid}\t{uid}\nTracerPid:\t{12 if name=="CHILD" else 0}'
            lines=[]
            for i,(k,m) in enumerate(a['modules'].items()):
                lo=0x10000+i*0x2000;major,minor=linux_dev(m['device']);lines.append(f'{lo:x}-{lo+4096:x} r-xp 00000000 {major:x}:{minor:x} {m["inode"]} {m["remote_path"]}')
                d['SHA_'+k]=m['sha256']+' file';d['INODE_'+k]=f'{m["device"]}:{m["inode"]}'
            d['MAPS']='\n'.join(lines)
            if drift:d.update(drift)
            return ('\n'.join('R13_'+k+'\n'+v for k,v in d.items())+'\nR13_REMOTE_RC=0\n').encode()
        for drift in [None,{'BOOT_END':'bad'},{'CHILD_END':stat(11,10,999)},{'SHA_shim':'0'*64+' file'},{'PARENT_STATUS':'Uid: 1 1 1 1\nTracerPid: 0'},{'CHILD_STATUS':'Uid: 20011206 20011206 20011206 20011206\nTracerPid: 99'},{'CHILD_STATUS':'Uid: 20011206 20011206 20011206 20011206\nTracerPid: 0'}]:
            with tempfile.TemporaryDirectory() as tmp:
                outputs=[NS(returncode=0,stdout=(a['holder']+'\n').encode(),stderr=b''),NS(returncode=0,stdout=payload(drift),stderr=b'')]
                with patch('identity.subprocess.run',side_effect=outputs) as run:
                    g=Guard(a,tmp,10**12)
                    if drift:
                        with self.assertRaises(Refuse):g.capture('test')
                    else:self.assertEqual(g.capture('test')['child_birth'],21)
                    argv=run.call_args.args[0];self.assertEqual(argv[1:3],['-t',SERIAL]);self.assertIn('R13_REMOTE_RC=0',argv[-1]);self.assertNotIn('kill',argv[-1])

class FakeErr:
    def Success(self):return True
    def GetCString(self):return None
class Clock:
    def __init__(self):self.n=0
    def __call__(self):self.n+=0.1;return self.n
class Cleanup(unittest.TestCase):
    def bare(self,tmp):
        s=Session.__new__(Session);s.out=Path(tmp);s.clock=Clock();s.start=0;s.deadline=100;s.cancel=False;s.owned={};s.calls=Calls();s.ignored=0;s.resume_stop_id=None
        s.a=admission();s.result={'events':[],'cleanup':{}};s.L=NS(eStateStopped=1,eStateRunning=2,eStateDetached=3,eStateExited=4,eStateInvalid=5,eStateCrashed=6,SBEvent=lambda:None,SBProcess=NS(EventIsProcessEvent=lambda _:False))
        return s
    def test_continue_stale_stop_is_not_event(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.bare(d);p=NS(stop=7,GetStopID=lambda:p.stop,GetState=lambda:1,Continue=lambda:FakeErr());s.proc=p;s.resume()
            def wait(*_):p.stop=8;return False
            s.db=NS(GetListener=lambda:NS(WaitForEvent=wait));s.wait_stop(20);self.assertEqual(p.stop,8)
            p.stop=7;s.db=NS(GetListener=lambda:NS(WaitForEvent=lambda *_:False))
            with self.assertRaisesRegex(Refuse,'timeout'):s.wait_stop(s.clock()+.5)
    def test_raw_unknown_and_nonplayer_filter(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.bare(d);s.proc=NS(GetStopID=lambda:4);s.owned={1:{'kind':'fromSurface_tailcall','address':100,'tid':None}}
            regs={'pc':100,'sp':200,'x30':300,'x2':400,'x0':500};s.reg=lambda _,n:regs[n]
            frame=NS(IsValid=lambda:True);t=NS(GetFrameAtIndex=lambda _:frame,GetThreadID=lambda:9)
            bp=NS(GetLocationAtIndex=lambda _:NS(GetID=lambda:1),IsHardware=lambda:True);s.target=NS(FindBreakpointByID=lambda _:bp)
            s.module=lambda addr: {'role':'android'} if addr==100 else {'role':'bridge'}
            s.on_hit(t,1,1);self.assertEqual(s.calls.from_count,0);self.assertEqual(s.result['events'][-1]['kind'],'ignored_nonplayer')
            def module(addr):
                if addr==400:raise Refuse('unadmitted')
                return {'role':'player' if addr==300 else 'android'}
            s.module=module
            with self.assertRaises(Refuse):s.on_hit(t,1,1)
            self.assertEqual(s.result['events'][-2]['x2'],'0x190');self.assertEqual(s.result['events'][-1]['winner']['classification'],'unknown')
            s.module=lambda _: {'role':'android'};s.ignored=15
            with self.assertRaisesRegex(Refuse,'ignored caller limit'):s.on_hit(t,1,1)
    def test_cleanup_detach_explicit_and_external_required(self):
        for external_ok,delete_ok in [(True,True),(False,True),(True,False)]:
            with tempfile.TemporaryDirectory() as d:
                s=self.bare(d);state=[1];s.proc=NS(IsValid=lambda:True,GetState=lambda:state[0]);s.owned={4:{}}
                def delete(i):
                    if not delete_ok:raise Refuse('delete failed')
                    s.owned.pop(i)
                s.delete_bp=delete;commands=[]
                def command(c):commands.append(c);state[0]=3
                s.command=command
                def capture(*args,**kw):
                    if not external_ok:raise Refuse('still traced')
                    return {'tracer_pid':0,'state':'S'}
                s.guard=NS(capture=capture);s.cleanup()
                self.assertEqual(commands,['process detach --keep-stopped false']);self.assertEqual(s.result['cleanup']['verified'],external_ok and delete_ok)
    def test_real_run_platform_and_install_failure_finally(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.bare(d);s.proc=None;s.target=None;s.result['cleanup']={};commands=[];external=[]
            proc=NS(IsValid=lambda:True,GetProcessID=lambda:11,GetState=lambda:1,GetStopID=lambda:1)
            def connect(*args):
                self.assertIn('platform select remote-ohos',commands)
                return proc
            target=NS(IsValid=lambda:True,GetPlatform=lambda:NS(GetName=lambda:'remote-ohos'),GetTriple=lambda:'aarch64-unknown-linux-unknown',ConnectRemote=connect)
            s.db=NS(SetAsync=lambda _:None,CreateTargetWithFileAndArch=lambda *args:target,SetSelectedTarget=lambda _:None,GetListener=lambda:None)
            s.L.SBError=FakeErr
            s.checked_identity=lambda phase:external.append(phase)
            s.command=lambda c:commands.append(c)
            s.prepare_addresses=lambda:s.selected.update(android=100,shim=200)
            s.selected={}
            def fail(*_):raise Refuse('hardware unsupported')
            s.add_bp=fail;s.guard=NS(capture=lambda *args,**kw:{'tracer_pid':0,'state':'S'})
            result=s.run(5039)
            self.assertEqual(result['error'],'hardware unsupported')
            self.assertEqual(commands[-1],'process detach --keep-stopped false')
            self.assertEqual(external,['pre-connect','attached-stopped'])
            self.assertEqual(result['status'],'OUTER_RECOVERY_REQUIRED') # fake has not detached
            self.assertTrue((Path(d)/'result.json').exists())
    def test_hardware_failure_records_owned_for_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.bare(d);bps=[]
            s.target=NS(GetNumBreakpoints=lambda:len(bps),GetBreakpointAtIndex=lambda i:bps[i],FindBreakpointByID=lambda _:bps[0])
            def command(c):
                self.assertIn('--hardware',c);bps.append(NS(GetID=lambda:7,IsValid=lambda:True,IsHardware=lambda:False,GetNumLocations=lambda:1))
            s.command=command
            with self.assertRaisesRegex(Refuse,'hardware'):s.add_bp('lock_entry',100)
            self.assertIn(7,s.owned)

class Receipt(unittest.TestCase):
    def test_cli_invalid_is_zero_subprocess(self):
        import observe
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.json';a=admission();a['execution_enabled']=False;f.write_text(json.dumps(a))
            with patch.object(sys,'argv',['observe','--admission',str(f),'--out',str(Path(d)/'out'),'--port','5039','--execute']),patch('observe.subprocess.Popen') as popen:
                self.assertEqual(observe.main(),2);popen.assert_not_called()
                self.assertTrue((Path(d)/'out/refusal.json').exists())
if __name__=='__main__':unittest.main()
