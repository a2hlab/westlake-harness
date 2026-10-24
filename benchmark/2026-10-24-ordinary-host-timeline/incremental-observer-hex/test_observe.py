#!/usr/bin/env python3
"""Synthetic observations and actual local pipe/timeout tests; zero HDC."""
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('ordinary_observer',HERE/'observe.py')
o=importlib.util.module_from_spec(sp);sp.loader.exec_module(o)
BOOT='61aa5791-fd69-4bbb-a7b5-333b5d913c81'

def stat(pid,ppid,birth):
    a=['S',str(ppid)]+['0']*17+[str(birth)]+['0']*8
    return f'{pid} (name with spaces) '+' '.join(a)

def sample(p=b'',e=b'',psize=100,esize=50,child=None,birth=500):
    f={}
    for phase in ['pre','post']:
        f.update({f'boot_{phase}':BOOT,f'uptime_{phase}':'1000.00 0',f'parent_stat_{phase}':stat(5129,1,11126),f'parent_status_{phase}':'Name: main\nUid:\t0\t0\t0\t0',f'fd1_{phase}':o.PARENT_LOG,f'fd2_{phase}':o.PARENT_LOG})
        f[f'ps_{phase}']='PID PPID UID NAME\n1 0 0 init\n9 2 0 [name with spaces]'+(f'\n{child} 5129 {o.UID} {o.CHILD_NAME}' if child else '')
        if child:
            f[f'child_{phase}']=stat(child,5129,birth)
            f[f'child_status_{phase}']=f'Uid:\t{o.UID}\t{o.UID}\t{o.UID}\t{o.UID}'
            f[f'child_cmd_{phase}']=o.CHILD_NAME.encode()+b'\x00'
    f['child_id']=str(child) if child else ''
    for name,size,data,ino in [('parent',psize,p,11),('events',esize,e,12)]:
        f[name+'_pre']=f'1 {ino} {size} 81a4';f[name+'_post']=f[name+'_pre'];f[name+'_data']=data
    f['done']='complete'
    return f

def encode(f):
    out=b'@wire 11\nasciihex-v2\n'
    for k,v in f.items():
        b=v if isinstance(v,bytes) else v.encode()
        if k in ['parent_data','events_data','child_cmd_pre','child_cmd_post']:
            k+='_hex';b=str(len(b)).encode()+b':'+b.hex(' ').encode()
        out+=f'@{k} {len(b)}\n'.encode()+b+b'\n'
    return out

class ObserveTests(unittest.TestCase):
    def test_nul_stripping_transport_roundtrip(self):
        raw=b'\x00before\x00after\n\xff\x80'
        s=self.state();packet=encode(sample(raw,psize=100+len(raw),child=22035))
        self.assertNotIn(b'\x00',packet)
        self.assertTrue(packet.isascii())
        _,delta=s.accept(packet.replace(b'\x00',b''))
        self.assertEqual(delta['parent'],raw)
        # The accepted v1 raw framing really fails under the same transport loss.
        sp=importlib.util.spec_from_file_location('v1',HERE.parent/'incremental-observer/observe.py')
        v1=importlib.util.module_from_spec(sp);sp.loader.exec_module(v1)
        f=sample(child=22035);legacy=b''
        for k,v in f.items():
            b=v if isinstance(v,bytes) else v.encode()
            legacy+=f'@{k} {len(b)}\n'.encode()+b+b'\n'
        with self.assertRaises(v1.Stop):v1.State(v1.config(BOOT,5129,11126)).accept(legacy.replace(b'\x00',b''))

    def test_malformed_hex_rejected(self):
        packet=encode(sample())
        for bad in [b'1:00',b'0:*',b'0:zz',b'0:0000',b'0:\x00']:
            corrupt=packet.replace(b'@parent_data_hex 2\n0:\n',f'@parent_data_hex {len(bad)}\n'.encode()+bad+b'\n')
            with self.subTest(bad=bad),self.assertRaises(o.Stop):o.State(o.config(BOOT,5129,11126)).accept(corrupt)

    def state(self):
        s=o.State(o.config(BOOT,5129,11126));s.accept(encode(sample()));return s

    def test_baseline_then_increments_child(self):
        s=self.state();r,d=s.accept(encode(sample(b'one\n',b'evt',104,53,22035)))
        self.assertEqual(d,{'parent':b'one\n','events':b'evt'})
        self.assertEqual(r['child_identity'],(22035,5129,500));self.assertEqual(r['ranges']['parent']['start'],100)

    def test_unbound_birth_transition_retains_offset_then_binds(self):
        s=self.state();f=sample(b'accepted\n',b'spawn\n',109,56)
        f['ps_post']+=f'\n22035 5129 {o.UID} {o.CHILD_NAME}'
        result,raw=s.accept(encode(f))
        self.assertEqual(result['status'],'identity_transition/partial')
        self.assertIsNone(s.child);self.assertEqual(s.files['parent'][2],100)
        self.assertEqual(raw['parent'],b'accepted\n')
        result,raw=s.accept(encode(sample(b'accepted\n',b'spawn\n',109,56,22035)))
        self.assertEqual(result['status'],'stable');self.assertEqual(result['ranges']['parent']['start'],100)
        self.assertEqual(raw['parent'],b'accepted\n');self.assertEqual(s.child,(22035,5129,500))

    def test_loop_keeps_transition_raw_and_continues(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);transition=sample(b'new',b'evt',103,53)
            transition['ps_post']+=f'\n22035 5129 {o.UID} {o.CHILD_NAME}'
            values=[encode(sample()),encode(transition),encode(sample(b'new',b'evt',103,53,22035))]
            class Fake:
                n=0
                def run(self,argv):
                    if self.n==3:raise o.Stop('fixture_done')
                    data=values[self.n];(out/f'raw-{self.n}').write_bytes(data);self.n+=1;return data
            tr=Fake();r=o.observe(o.config(BOOT,5129,11126)|{'hdc':'unused'},out,tr,time.monotonic()+5,sleep=lambda _:None)
            self.assertEqual(tr.n,3);self.assertEqual(r['identity_transition_samples'],1);self.assertEqual(r['accepted_samples'],2)
            self.assertEqual((out/'raw-1').read_bytes(),values[1]);self.assertEqual(r['last_child_identity'],(22035,5129,500))

    def test_binary_marker_inside_log(self):
        s=self.state();b=b'\x00\n@done 8\ncomplete\n'
        _,d=s.accept(encode(sample(b,psize=100+len(b))));self.assertEqual(d['parent'],b)

    def test_truncation_and_rotation(self):
        for change in ['truncate','rotate','mode','posttruncate','postrotate']:
            with self.subTest(change=change):
                s=self.state();f=sample()
                if change=='truncate':f['parent_pre']=f['parent_post']='1 11 99 81a4'
                if change=='rotate':f['parent_pre']=f['parent_post']='1 99 100 81a4'
                if change=='mode':f['events_pre']=f['events_post']='1 12 50 21a4'
                if change=='posttruncate':f['parent_post']='1 11 99 81a4'
                if change=='postrotate':f['parent_post']='1 99 100 81a4'
                with self.assertRaises(o.Stop):s.accept(encode(f))
                self.assertEqual(s.files['parent'][2],100)

    def test_identity_drift(self):
        for key,value in [('boot_post','00000000-0000-0000-0000-000000000000'),('parent_stat_post',stat(5129,1,11127)),('parent_status_post','Uid: 0 1 0 0'),('fd2_post','/dev/null')]:
            s=self.state();f=sample();f[key]=value
            with self.subTest(key=key),self.assertRaises(o.Stop):s.accept(encode(f))

    def test_child_drift_and_absence(self):
        for change in ['gone','birth','uid','cmd','mid_sample','multiple']:
            s=self.state();s.accept(encode(sample(child=22035)));f=sample(child=22035)
            if change=='gone':f=sample()
            if change=='birth':f=sample(child=22035,birth=501)
            if change=='uid':f['child_status_post']='Uid: 1 1 1 1'
            if change=='cmd':f['child_cmd_post']='another.app'
            if change=='mid_sample':f['ps_post']='PID PPID UID NAME\n1 0 0 init'
            if change=='multiple':f['ps_pre']+=f'\n22036 5129 {o.UID} {o.CHILD_NAME}'
            with self.subTest(change=change),self.assertRaises(o.Stop):s.accept(encode(f))

    def test_short_frame_and_wrong_count(self):
        s=self.state()
        with self.assertRaises(o.Stop):s.accept(encode(sample())[:-4])
        with self.assertRaises(o.Stop):s.accept(encode(sample(b'a',psize=103)))

    def test_loop_stops_after_drift_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);f=sample();f['events_pre']=f['events_post']='1 12 49 81a4'
            class Fake:
                def __init__(self):self.n=0
                def run(self,argv):
                    self.n+=1
                    if self.n==1:return encode(sample())
                    if self.n==2:return encode(f)
                    raise AssertionError('must stop after drift')
            tr=Fake();r=o.observe(o.config(BOOT,5129,11126)|{'hdc':'unused'},out,tr,time.monotonic()+10,sleep=lambda _:None)
            self.assertIn('truncation',r['reason']);self.assertEqual(tr.n,2)
            before=(out/'sample-0000.json').read_bytes()
            with self.assertRaises(FileExistsError):o.save(out/'sample-0000.json',{})
            self.assertEqual(before,(out/'sample-0000.json').read_bytes())

    def test_actual_local_timeout_preserves_partial(self):
        with tempfile.TemporaryDirectory() as t,patch.object(o,'COMMAND_LIMIT',0.15):
            out=Path(t);tr=o.Transport(out,time.monotonic()+2)
            with self.assertRaisesRegex(o.Stop,'timeout'):
                tr.run([sys.executable,'-c','import time;print("partial",flush=True);time.sleep(5)'])
            self.assertEqual((out/'command-0000/stdout').read_bytes(),b'partial\n')
            r=json.loads((out/'command-0000/receipt.json').read_text());self.assertEqual(r['stop'],'timeout')

    def test_actual_local_combined_byte_cap(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);tr=o.Transport(out,time.monotonic()+3,cap=128)
            with self.assertRaisesRegex(o.Stop,'byte_cap'):
                tr.run([sys.executable,'-c','import os;os.write(1,b"x"*90);os.write(2,b"y"*90)'])
            self.assertEqual(sum((out/'command-0000'/n).stat().st_size for n in ['stdout','stderr']),128)
            with self.assertRaises(o.Stop):tr.run(['never-executed'])

    def test_actual_local_nonzero_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);tr=o.Transport(out,time.monotonic()+3)
            with self.assertRaisesRegex(o.Stop,'rc:7'):
                tr.run([sys.executable,'-c','import sys;print("failure");sys.exit(7)'])
            old=(out/'command-0000/stdout').read_bytes();tr2=o.Transport(out,time.monotonic()+3)
            with self.assertRaises(FileExistsError):tr2.run(['never-executed'])
            self.assertEqual(old,(out/'command-0000/stdout').read_bytes())

    def test_generated_shell_syntax_and_readonly_set(self):
        for files in [{},{'parent':(1,11,100,'81a4'),'events':(1,12,50,'81a4')}]:
            s=o.shell(o.config(BOOT,5129,11126),files)
            r=subprocess.run(['sh','-n'],input=s.encode(),capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)
            for banned in ['uitest','am start','kill ','watchdog','.env','reboot','chmod','dd of=','| awk','tr "','wc ']:
                self.assertNotIn(banned,s)

    def test_generated_shell_actual_local_fixture(self):
        # Run the actual shell producer against local synthetic proc/files.
        # Only paths and ps/stat platform adapters are substituted; no HDC.
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);procroot=root/'proc';binroot=root/'bin';binroot.mkdir()
            c=o.config(BOOT,5129,11126);f=sample(child=22035)
            for pid in [5129,22035]:
                q=procroot/str(pid);q.mkdir(parents=True)
                prefix='parent_stat' if pid==5129 else 'child'
                (q/'stat').write_text(f[prefix+'_pre']+'\n')
                (q/'status').write_text(f[('parent_status' if pid==5129 else 'child_status')+'_pre']+'\nPadding: '+'x'*1500+'\n')
                (q/'cmdline').write_bytes((o.CHILD_NAME if pid==22035 else 'appspawn-x').encode()+b'\x00')
            q=procroot/'sys/kernel/random';q.mkdir(parents=True);(q/'boot_id').write_text(BOOT+'\n')
            (procroot/'uptime').write_text('1000.00 0\n')
            q=procroot/'5129/fd';q.mkdir()
            for n in ['1','2']:(q/n).symlink_to(o.PARENT_LOG)
            psdata=root/'ps.txt'
            unrelated=''.join(f'{30000+i} 2 0 [unrelated name {i}]\n' for i in range(600))
            psdata.write_text(f['ps_pre']+'\n'+unrelated)
            self.assertGreaterEqual(psdata.stat().st_size,13*1024)
            (binroot/'ps').write_text('#!/bin/sh\nexec /bin/cat '+str(psdata)+'\n');(binroot/'ps').chmod(0o755)
            for tool in ['cat','readlink','dd','sh','python3']:
                (binroot/tool).symlink_to(shutil.which(tool))
            for forbidden in ['awk','tr','ip','route','wpa_cli','ndc','wc']:
                self.assertIsNone(shutil.which(forbidden,path=str(binroot)))
            (binroot/'stat').write_text('#!/usr/bin/env python3\nimport os,sys\ns=os.stat(sys.argv[-1]);print(s.st_dev,s.st_ino,s.st_size,format(s.st_mode,"x"))\n');(binroot/'stat').chmod(0o755)
            parent=root/'parent.log';events=root/'events.log';parent.write_bytes(b'old parent');events.write_bytes(b'old events')
            state=o.State(c)
            stream_sizes=[]
            def invoke():
                text=o.shell(c,state.files).replace('/proc/',str(procroot)+'/').replace(o.PARENT_LOG,str(parent)).replace(o.EVENT_ROOT+'/'+BOOT+'/events.log',str(events)).replace('/bin/od',shutil.which('od'))
                # fd readlink still returns the unmodified production path.
                r=subprocess.run(['/bin/sh','-c',text],env=dict(os.environ,PATH=str(binroot)),capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertNotIn(b'\x00',r.stdout)
                self.assertTrue(r.stdout.isascii())
                self.assertNotIn(b'unrelated',r.stdout)
                self.assertLess(len(o.frames(r.stdout)['ps_pre']),120)
                stream_sizes.append(len(r.stdout)+len(r.stderr))
                return state.accept(r.stdout.replace(b'\x00',b''))
            invoke()
            with parent.open('ab') as fp:fp.write(b'new\x00parent\n\xff')
            with events.open('ab') as fp:fp.write(b'new\x00event\n')
            result,deltas=invoke();self.assertEqual(deltas,{'parent':b'new\x00parent\n\xff','events':b'new\x00event\n'})
            self.assertEqual(result['child_identity'],(22035,5129,500))
            for _ in range(88):invoke()
            self.assertEqual(len(stream_sizes),90)
            self.assertLess(sum(stream_sizes),o.LIMIT)
            print('restricted-PATH budget:',psdata.stat().st_size,'ps bytes;',sum(stream_sizes),'captured bytes / 90 samples')

    def test_default_cli_plan_only_and_existing_out_refusal(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'plan';args=[sys.executable,str(HERE/'observe.py'),'--boot',BOOT,'--parent-pid','5129','--parent-birth','11126','--hdc','DO_NOT_RUN','--out',str(out)]
            r=subprocess.run(args,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
            before=(out/'plan.json').read_bytes();r=subprocess.run(args,capture_output=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual(before,(out/'plan.json').read_bytes())

if __name__=='__main__':unittest.main()
