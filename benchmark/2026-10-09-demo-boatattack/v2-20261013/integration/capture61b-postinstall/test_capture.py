"""Run the unchanged collector against a synthetic full-shape local transport; no HDC."""
import contextlib, hashlib, io, json, os, re, runpy, shlex, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
REL=Path('benchmark/2026-10-09-demo-boatattack/v2-20261013/integration')
SERIAL='61b0657200000000000000000324012c'
BOOT='11111111-2222-4333-8444-555555555555'
PACKAGE='com.Unity3d.BoatAttackDay'
CFG='/system/etc/init/00_westlake_u13_recover-v3.cfg'
# Whitespace is intentional: stripping any edge must fail the separately read file SHA.
CFG_BYTES=' \n{ "services": [] }\n\n'
def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(p.read_text())

class CaptureTests(unittest.TestCase):
    def fixture(self,case='ok',execute=True):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td);root=ws/'westlake-harness';entry=root/REL/'capture61b-postinstall';entry.mkdir(parents=True)
            shutil.copyfile(HERE/'capture_readonly.py',entry/'capture_readonly.py')
            cap=read(HERE/'capture.request.json');cap['synthetic']=True
            if case=='serial':cap['serial']='5cd1e3dd00000000000000000923012c'
            (entry/'capture.request.json').write_text(json.dumps(cap))
            identity=root/REL/'final-v2-candidate-r2/boat_identity.py';identity.parent.mkdir(parents=True)
            shutil.copyfile(REPO/REL/'final-v2-candidate-r2/boat_identity.py',identity)
            baseline_path=Path('benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json')
            baseline=read(HERE/'baseline319.fixture.json')['expected'];self.assertEqual(len(baseline),319)
            (root/baseline_path).parent.mkdir(parents=True);(root/baseline_path).write_text(json.dumps({'expected':baseline}))
            self.assertEqual(len(cap['files']),497)
            rows={p:{'sha256':sha(p.encode()),'mode':'644','uid':0,'gid':0,'label':'u:object_r:system_file:s0'} for p in cap['files']}
            rows[CFG]['sha256']=sha(CFG_BYTES.encode())
            rows['/data/app/el1/bundle/public/'+PACKAGE+'/android/base.apk']['sha256']='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
            uid=20011001  # synthetic fixture identity, never a real61b observation
            bundle={'name':PACKAGE,'uid':uid,'applicationInfo':{'name':PACKAGE,'uid':uid},'userInfo':[{'bundleName':PACKAGE,'uid':uid,'bundleUserInfo':{'userId':100}}],'versionCode':1,'versionName':'0.9'}
            if case=='uid':bundle.pop('uid')
            calls=[];boots=0
            def fake(argv,**kw):
                nonlocal boots
                self.assertEqual(argv[:4],['/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','-t',SERIAL,'shell'])
                cmd=shlex.split(argv[4])[2].removesuffix(';');calls.append(cmd)
                marker=re.search(r'(__CAPTURE_RC_[a-f0-9]+__)%s',argv[4]).group(1)
                if cmd=='cat /proc/sys/kernel/random/boot_id':
                    boots+=1;body=('wrong-boot' if case=='boot' or (case=='bookend' and boots==2) else BOOT)+'\n'
                elif cmd=='bm dump -a':body='ID: 100:\n'+PACKAGE+'\n'
                elif cmd=='bm dump -n '+PACKAGE:body=PACKAGE+':\n'+json.dumps(bundle)+'\n'
                elif cmd=='cat '+CFG:body=CFG_BYTES.strip() if case=='stripcfg' else CFG_BYTES
                elif cmd.startswith('set -e; for p in '):
                    targets=shlex.split(cmd.split('for p in ',1)[1].split('; do ',1)[0]);body=''
                    for p in targets:
                        r=rows[p];body+=f"TARGET={p}\n{r['sha256']}  {p}\n{r['mode']}:{r['uid']}:{r['gid']}\n{r['label']} {p}\n"
                elif cmd.startswith('test -d '):
                    p=shlex.split(cmd)[2];self.assertIn(p,cap['route_b_directories']);body=f'755:20011000:20011000\nu:object_r:appdat:s0 {p}\n'
                elif cmd.startswith('if test -e '):body='PRESENT' if case=='root' else 'ABSENT'
                elif cmd.startswith('sha256sum '):body=''.join(baseline[p]+'  '+p+'\n' for p in shlex.split(cmd)[1:])
                else:self.fail('unexpected device command '+cmd)
                remote_rc=9 if case=='remote_rc' else 0
                return subprocess.CompletedProcess(argv,0,(body+'\n'+marker+str(remote_rc)+'\n').encode(),b'transport failure' if case=='stderr' else b'')
            out=ws/'capture';argv=['capture_readonly.py','--out',str(out),'--expected-boot',BOOT]+(['--execute'] if execute else [])
            stream=io.StringIO();error=None
            with patch.dict(os.environ,{'WORKSPACES':str(ws),'PYTHONDONTWRITEBYTECODE':'1'}),patch.object(sys,'argv',argv),patch('subprocess.run',side_effect=fake),contextlib.redirect_stdout(stream):
                try:runpy.run_path(str(entry/'capture_readonly.py'),run_name='__main__')
                except SystemExit as e:
                    if e.code not in (0,None):error=e
                except (AssertionError,ValueError,KeyError) as e:error=e
            result=read(out/'capture.json') if (out/'capture.json').exists() else None
            if result:
                for ref in result['raw']:
                    p=Path(ref['path'].replace('$WORKSPACES',str(ws)));self.assertEqual(sha(p.read_bytes()),ref['sha256'])
                if result['complete']:
                    self.assertEqual((out/'current-recover.cfg').read_bytes(),CFG_BYTES.encode())
                    self.assertEqual(result['boat_uid'],uid)
                    self.assertEqual(set(result['boat_identity']),{'boot_before','bundle','boot_after'})
                    self.assertEqual(read(out/'baseline319.json')['actual'],baseline)
            return error,result,calls,stream.getvalue(),out.exists()

    def test_delta_and_preview(self):
        original=(REPO/REL/'final-v2-f28/capture5cd/capture_readonly.py').read_bytes()
        expected=original.replace(b'Original5cd postinstall',b'Original61b postinstall').replace(b"SERIAL='5cd1e3dd00000000000000000923012c'",b"SERIAL='61b0657200000000000000000324012c'").replace(b"cap['schema']=='boat-5cd-capture/v1'",b"cap['schema']=='boat-61b-capture/v1'")
        self.assertEqual((HERE/'capture_readonly.py').read_bytes(),expected)
        sources=read(HERE/'source.json');self.assertEqual(sha(original),sources['collector']['sha256'])
        self.assertEqual(sha((HERE/'capture.request.json').read_bytes()),sources['request']['sha256'])
        error,result,calls,text,exists=self.fixture(execute=False)
        self.assertIsNone(error);self.assertIsNone(result);self.assertFalse(calls);self.assertFalse(exists)
        self.assertEqual(json.loads(text)['status'],'DISABLED_READONLY_PREVIEW')

    def test_complete_full_shape(self):
        error,result,calls,text,exists=self.fixture();self.assertIsNone(error)
        self.assertTrue(result['complete']);self.assertEqual(len(result['files']),497)
        self.assertEqual(result['boot_before'],result['boot_after']);self.assertFalse(result['pending'])
        self.assertEqual(len(calls),61)

    def test_wrong_serial(self):
        error,result,calls,_,_=self.fixture('serial');self.assertIsNotNone(error);self.assertIsNone(result);self.assertFalse(calls)

    def test_wrong_boot(self):
        error,result,calls,_,_=self.fixture('boot');self.assertIsNotNone(error);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertIn('fresh expected boot mismatch',str(error))

    def test_changed_bookend(self):
        error,result,calls,_,_=self.fixture('bookend');self.assertIsNotNone(error);self.assertIsNone(result);self.assertEqual(len(calls),61)

    def test_stripped_cfg(self):
        error,result,calls,_,_=self.fixture('stripcfg');self.assertIsNotNone(error);self.assertIsNone(result);self.assertEqual(len(calls),36);self.assertEqual(calls[-1],'cat '+CFG)

    def test_missing_uid(self):
        error,result,calls,_,_=self.fixture('uid');self.assertIsNotNone(error);self.assertIsNone(result);self.assertEqual(len(calls),3);self.assertIn('BMS application UID invalid/inconsistent',str(error))

    def test_remote_failure(self):
        for case in ['remote_rc','stderr']:
            with self.subTest(case=case):
                error,result,calls,_,_=self.fixture(case);self.assertIsNotNone(error);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertIn('capture read failed boot-before',str(error))

    def test_root_present(self):
        error,result,_,_,_=self.fixture('root');self.assertIsInstance(error,SystemExit);self.assertEqual(error.code,2)
        self.assertFalse(result['complete']);self.assertTrue(result['root_absent']['exists']);self.assertTrue(result['pending'])

if __name__=='__main__':unittest.main()
