#!/usr/bin/env python3
"""Synthetic boundary fixtures only: never real runtime/deploy acceptance."""
import copy,json,re,subprocess,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import binding as b
BOOT='11111111-2222-3333-4444-555555555555'
class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=b.HERE);self.root=Path(self.tmp.name)
        self.q=b.read(b.HERE/'request.disabled.json');self.c,self.p=b.artifact(self.q);self.origin,self.epoch=b.origin(self.q,self.c,self.p)
    def tearDown(self):self.tmp.cleanup()
    def put(self,name,j):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(j,indent=2)+'\n' if not isinstance(j,str) else j);return b.pin(p)
    def test_main_preview_cli_disabled(self):
        r=subprocess.run(['python3',str(b.HERE/'binding.py'),'--request',str(b.HERE/'request.disabled.json'),'--out',str(self.root/'preview')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);j=json.loads(r.stdout)
        self.assertFalse(j['execution_enabled']);self.assertIsNone(j['candidate_boot']);self.assertEqual(j['device_calls'],0)
        with self.assertRaises(ValueError):b.deployment(self.q,self.c,self.p)
    def test_actual_origin_bookends_and_recv_failures(self):
        boot,finished=b.origin(self.q,self.c,self.p)
        cap=b.read(b.pinned(self.q['origin_evidence']['capture']));self.assertEqual(boot,cap['boot_id']);self.assertGreater(finished,0)
        for case in ('boot','serial','drop_recv','bad_remote_marker','metadata_after','recv_sha','recv_serial','program'):
            q=copy.deepcopy(self.q);e=q['origin_evidence']
            if case in ('boot','serial','recv_sha'):
                j=b.read(b.pinned(e['capture']))
                if case=='boot':j['boot_id']=BOOT
                elif case=='serial':j['serial']='61b0657200000000000000000324012c'
                else:j['files'][0]['sha256']='0'*64
                e['capture']=self.put(case+'-capture.json',j)
            elif case=='drop_recv':e['recv_commands'].pop()
            elif case=='program':e['program']['sha256']='0'*64
            elif case=='recv_serial':
                j=b.read(b.pinned(e['recv_commands'][0]['receipt']));j['argv'][2]='61b0657200000000000000000324012c';e['recv_commands'][0]['receipt']=self.put('recv-wrong-serial.json',j)
            else:
                r=e['probe_command'] if case=='bad_remote_marker' else e['metadata_after_command'];text=b.pinned(r['stdout']).read_text()
                text=text.replace('CAPTURE_RC=0','CAPTURE_RC=1') if case=='bad_remote_marker' else text.replace(boot,BOOT)
                r['stdout']=self.put(case+'.stdout',text);j=b.read(b.pinned(r['receipt']));j['stdout_sha256']=r['stdout']['sha256'];r['receipt']=self.put(case+'.receipt.json',j)
            with self.subTest(case=case),self.assertRaises(ValueError):b.origin(q,self.c,self.p)
    def test_retry_origin_derived_without_code_change(self):
        # Replayed fixture only. All origin raw bookends are consistently replaced;
        # actual read identity still comes exclusively from its pinned receipts.
        q=copy.deepcopy(self.q);e=q['origin_evidence'];new='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        for name in ('probe_command','metadata_before_command','metadata_after_command'):
            r=e[name];text=b.pinned(r['stdout']).read_text().replace(self.origin,new);r['stdout']=self.put('retry-'+name+'.stdout',text)
            j=b.read(b.pinned(r['receipt']));j['stdout_sha256']=r['stdout']['sha256'];r['receipt']=self.put('retry-'+name+'.receipt.json',j)
        j=b.read(b.pinned(e['capture']));j['boot_id']=new;e['capture']=self.put('retry-cap.json',j)
        j=b.read(b.pinned(e['probe']));raw=b.pinned(e['probe_command']['stdout']).read_text().split('\nCAPTURE_RC=')[0].rstrip('\n')+'\n'
        import hashlib
        j['stdout_sha256']=hashlib.sha256(raw.encode()).hexdigest();e['probe']=self.put('retry-probe.json',j)
        self.assertEqual(b.origin(q,self.c,self.p)[0],new)
    def test_prepare_origin_cli(self):
        e=self.q['origin_evidence'];cap=b.pinned(e['capture'])
        r=subprocess.run(['python3',str(b.HERE/'prepare_origin.py'),'--request',str(b.HERE/'request.disabled.json'),'--readonly-dir',str(cap.parent.parent),'--capture-program',str(b.pinned(e['program'])),'--out',str(self.root/'derived-request.json')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['origin_boot'],self.origin)
        self.assertIsNone(b.read(self.root/'derived-request.json')['candidate_boot'])
    def capture(self):
        q=copy.deepcopy(self.q);q['candidate_boot']=BOOT;p=self.p;c=self.c
        expected=p['expected'];runtime,boot=c.parts({k:expected[k] for k in b.read(c.pinned(p['baseline']))['expected']})
        upstream=b.load(p['programs']['reader'],'fixture_original_reader');absence=b.load(p['programs']['absence_reader'],'fixture_original_absence');rows=[]
        out=self.root/'original-reader';out.mkdir()
        def record(argv,**kwargs):
            command=argv[-1];marker=re.findall(r'__(?:DEMO|BOAT_ABSENCE)_RC_[a-f0-9]{32}__',command)[0]
            if '__BOAT_ABSENCE' in marker:value='ABSENT'
            elif command.startswith('cat /proc/'):value=BOOT
            elif command.startswith('ps '):value='PID PPID UID NAME\n42 1 0 appspawn-x'
            elif command.startswith('readlink '):value='/system/bin/appspawn-x'
            elif command.startswith('df '):value='Filesystem 1K-blocks Used Available Use% Mounted on\n/data 20000 1000 19000 5% /data'
            elif command.startswith('param '):value='OpenHarmony-6.1.0.31'
            elif '*' in command:value='\n'.join(h+'  '+k for k,h in (runtime if command.startswith('sha256sum /system/bin/appspawn-x') else boot).items())
            else:
                targets=command.split('; x=')[0].split()[1:];value='\n'.join(expected[k]+'  '+k for k in targets)
            stdout=value+'\n'+marker+'0\n';n=len(rows)
            rows.append(dict(argv=argv,rc=0,started=self.epoch+100+n,finished=self.epoch+100+n+.5,stdout=self.put('raw-%02d.stdout'%n,stdout),stderr=self.put('raw-%02d.stderr'%n,'')))
            return SimpleNamespace(returncode=0,stdout=stdout,stderr='')
        with patch('subprocess.run',record):identity=c.check(absence.with_absence(upstream.Reader)(out,b.SERIAL),p,out,self.origin)
        cap=dict(schema='r6-original-reader-capture/v1',serial=b.SERIAL,origin_boot=self.origin,candidate_boot=BOOT,proof=q['artifact']['proof'],collector=b.pin(b.HERE/'fresh_read.py'),binding=b.pin(b.__file__),started=self.epoch+100,finished=self.epoch+200,commands=rows,identity=b.pin(out/'identity.json'))
        q['fresh_capture']=self.put('capture.json',cap);return q,cap
    def rerun(self,q):
        out=self.root/('replay-'+str(time.time_ns()));out.mkdir()
        return b.replay(q,self.c,self.p,out,self.epoch+99)
    def test_complete_original337_reader_replay(self):
        q,cap=self.capture();identity,n=self.rerun(q)
        self.assertTrue(identity['passed']);self.assertEqual(identity['candidate_paths'],len(self.p['expected']));self.assertEqual(n,24)
        self.assertEqual(identity['absent_targets'],[self.c.ROUTEB])
    def test_original_failures_rejected(self):
        q,cap=self.capture()
        for case in ('host_rc','remote_rc','marker','serial','missing_sha','wrong_sha','absence','version','boot','trailing'):
            with self.subTest(case=case):
                changed=copy.deepcopy(cap)
                if case=='host_rc':changed['commands'][0]['rc']=1
                elif case=='serial':changed['commands'][0]['argv'][3]='61b0657200000000000000000324012c'
                elif case=='trailing':changed['commands'].append(changed['commands'][-1])
                else:
                    n=1 if case=='absence' else 2 if case in ('missing_sha','wrong_sha') else len(changed['commands'])-2 if case=='version' else 0
                    r=changed['commands'][n];text=b.pinned(r['stdout']).read_text()
                    if case=='remote_rc':text=text[:-2]+'1\n'
                    elif case=='marker':text=text.split('\n__')[0]+'\n'
                    elif case=='missing_sha':text='\n'.join(text.splitlines()[1:])+'\n'
                    elif case=='wrong_sha':text='0'*64+text[64:]
                    elif case=='absence':text=text.replace('ABSENT','PRESENT')
                    elif case=='version':text=text.replace('OpenHarmony-6.1.0.31','OpenHarmony-7')
                    elif case=='boot':text=text.replace(BOOT,self.origin)
                    r['stdout']=self.put('bad-'+case+'.stdout',text)
                bad=copy.deepcopy(q);bad['fresh_capture']=self.put('cap-'+case+'.json',changed)
                with self.assertRaises((ValueError,RuntimeError)):self.rerun(bad)
    def fixture_deploy(self):
        q=copy.deepcopy(self.q);q['candidate_boot']=BOOT;old=b.read(self.c.pinned(self.p['successor_plan']))
        source=self.c.pinned(self.p['successor_program']).read_text().replace("BOOT = '35da6f13-e7b1-4472-a36a-5c4a69d5f191'","BOOT = '"+self.origin+"'")
        exe=self.put('new-successor.py',source);plan=copy.deepcopy(old);plan.update(boot_id=self.origin,execution_enabled=True,executor=exe)
        pref=self.put('stage-plan.json',plan);auth=dict(approved_by='outer(codex)',action='apply',plan_sha256=pref['sha256'],serial=b.SERIAL,origin_boot_id=self.origin,boot_id=self.origin,live_runtime_sha256='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354',expires_epoch=self.epoch+50)
        aref=self.put('auth.json',auth);backups=[];intents=[];placed=[];backuprefs=[]
        for i,r in enumerate(plan['members']):
            backups.append(dict(target=r['target'],before=r['before'],backup='backup-%03d'%i,candidate_sha256=r['sha256']))
            f=self.root/('backup-%03d'%i);f.write_bytes(b.path(r['before']['source']).read_bytes());backuprefs.append(b.pin(f))
            intents.append(self.put('intent-%03d.json'%i,dict(plan_sha256=pref['sha256'],serial=b.SERIAL,boot_id=self.origin,target=r['target'],candidate_sha256=r['sha256'],before=r['before'])))
            placed.append(self.put('placed-%03d.json'%i,dict(target=r['target'],sha256=r['sha256'])))
        tx=self.put('transaction.json',dict(plan_sha256=pref['sha256'],serial=b.SERIAL,boot_id=self.origin,backups=backups))
        def cmd(name,argv,start,stdout=''):
            return dict(receipt=self.put(name+'.json',dict(argv=argv,rc=0,started=self.epoch+start,finished=self.epoch+start+.5)),stdout=self.put(name+'.stdout',stdout),stderr=self.put(name+'.stderr',''))
        apply=cmd('apply',['python3',str(b.pinned(exe)),'run','--plan',str(b.pinned(pref)),'--action','apply','--execute','--authorization',str(b.pinned(aref)),'--authorization-sha256',aref['sha256'],'--out',str(self.root)],1)
        ready='state=READY\nlayers=56\nboot_id='+BOOT+'\ntrue \nPermissive';bound='state=BOUND\nlayers=7\nboot_id='+BOOT
        d=dict(plan=pref,authorization=aref,transaction=tx,intents=intents,placed_members=placed,backups=backuprefs,placed=self.put('placed.json',dict(state='PLACED_ONLY',ui_accepted=False,seal_signed=False,reboots=0)),source_result=self.put('source-apply.json',dict(state='SOURCE_STAGED_COLD_BOOT_REQUIRED',success=True,live_runtime_sha256=auth['live_runtime_sha256'],reboots=0,binds=0,app_signals=0,complete_runtime_rollback=False)),apply_command=apply,boot_intent=self.put('boot-intent.json',dict(serial=b.SERIAL,origin_boot=self.origin,epoch=self.epoch+2,authorization=dict(approved_by='outer(codex)',serial=b.SERIAL,origin_boot_id=self.origin,allow_candidate_boot=True,experiment_expires_epoch=self.epoch+50))),boot_result=self.put('boot-result.json',dict(boot_id=BOOT,ready=True,raw=ready,bound=bound)),boot_command=cmd('boot',[plan['hdc'],'-t',b.SERIAL,'target','boot'],3))
        import shlex
        for name,command,text,stamp in [('ready_command','cat /data/westlake-demo/u13/receipt.env; param get sys.westlake.demo.u13.ready; getenforce',ready,4),('bound_command','cat /data/westlake-demo/u13/boat-v2-20261013-r4/boat-'+BOOT+'.receipt',bound,5)]:
            script='/system/bin/sh -c '+shlex.quote(command)+'; rc=$?; printf "\\nR6_RC=%s\\n" "$rc"'
            d[name]=cmd(name,[plan['hdc'],'-t',b.SERIAL,'shell',script],stamp,text+'\nR6_RC=0\n')
        q['deployment']=d;return q
    def test_new_original_transaction_protocol(self):
        q=self.fixture_deploy();self.assertEqual(b.deployment(q,self.c,self.p),self.epoch+5.5)
        for case in ('old_boot','drop_intent','wrong_plan','wrong_source','apply_argv','ready_marker'):
            bad=copy.deepcopy(q)
            if case=='old_boot':bad['candidate_boot']=self.origin
            elif case=='drop_intent':bad['deployment']['intents'].pop()
            elif case=='wrong_plan':bad['deployment']['plan']['sha256']='0'*64
            elif case=='wrong_source':bad['deployment']['source_result']=self.put('wrong-source.json',dict(success=True))
            elif case=='apply_argv':
                j=b.read(b.pinned(bad['deployment']['apply_command']['receipt']));j['argv'][6]='rollback';bad['deployment']['apply_command']['receipt']=self.put('wrong-argv.json',j)
            else:bad['deployment']['ready_command']['stdout']=self.put('wrong-ready.stdout','state=READY\n')
            with self.subTest(case=case),self.assertRaises(ValueError):b.deployment(bad,self.c,self.p)
    def test_collect_default_refuses_without_transport(self):
        import fresh_read
        with patch('subprocess.run',side_effect=AssertionError('transport forbidden')):
            with self.assertRaises(ValueError):fresh_read.collect(self.q,self.root/'collector')
    def test_replay_cli_disabled_synthetic_only(self):
        q,cap=self.capture();q['deployment']=self.fixture_deploy()['deployment'];qref=self.put('complete-synthetic-request.json',q)
        r=subprocess.run(['python3',str(b.HERE/'binding.py'),'--request',str(b.pinned(qref)),'--out',str(self.root/'cli-replayed'),'--replay'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);j=json.loads(r.stdout)
        self.assertEqual(j['state'],'FRESH_BOUND_DISABLED');self.assertFalse(j['execution_enabled']);self.assertEqual(j['device_calls'],0)
        self.assertEqual(j['observed_marker'],{'boot_id':BOOT})
if __name__=='__main__':unittest.main(verbosity=2)
