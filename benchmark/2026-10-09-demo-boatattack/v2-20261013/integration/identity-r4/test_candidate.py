"""Offline current root window3 r4 inputs; no old live result is accepted."""
import ast, copy, json, tempfile, unittest
from pathlib import Path
import candidate_identity as c
import compile_candidate as compiler

class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name)
        from prepare_actual import prepare
        request_path=prepare(cls.out/'inputs');request=c.read(request_path);request['_request_path']=request_path
        cls.request=request;cls.proof=compiler.build(request,cls.out/'compiled')
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_full319_and_four_exact_replacements(self):
        d=self.proof;e=c.validate(d);b=c.read(c.BASE)['expected'];self.assertTrue(set(b)<=set(e));self.assertEqual(len([p for p in b if b[p]!=e[p]]),4);self.assertEqual(e[c.RUNTIME],c.CHANGES[c.RUNTIME]);self.assertEqual(len(d['generation_sha256']),64)
    def test_old_runtime_rejected(self):
        d=copy.deepcopy(self.proof);d['expected'][c.RUNTIME]='adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130'
        with self.assertRaises(ValueError):c.validate(d)
    def test_missing_untouched_rejected(self):
        d=copy.deepcopy(self.proof);del d['expected']['/system/bin/appspawn-x']
        with self.assertRaises(ValueError):c.validate(d)
    def test_routeb_drift_rejected(self):
        d=copy.deepcopy(self.proof);d['expected']['/system/etc/init/01_westlake_u13_toutiao.cfg']='f'*64
        with self.assertRaises(ValueError):c.validate(d)
    def test_smoke_preserves_predicates(self):
        old=c.read(c.pinned(self.request['baseline_smoke']));new=c.read(c.pinned(self.proof['smoke']))
        for k in ['groups','fixes']:self.assertEqual(old[k],new[k])
        for k,v in old['probe'].items():
            if k!='files':self.assertEqual(v,new['probe'][k])
        self.assertEqual(new['expect']['runtime_fp'],self.proof['fingerprints']['runtime_sha256'][:12]);self.assertNotEqual(new['expect']['runtime_fp'],'452447a4a0ba')
    def test_duplicate_missing_sha_rejected(self):
        with self.assertRaises(ValueError):c.parse_hashes('a'*64+'  /system/a\n'+'a'*64+'  /system/a')
        with self.assertRaises(ValueError):c.parse_hashes('cat: missing')
    def test_runner_all_gate_sites(self):
        s=(c.HERE/'run_candidate_post_reboot.py').read_text();ast.parse(s)
        self.assertNotIn("HERE / 'round_identity.py'",s);self.assertEqual(s.count('portable(CANDIDATE_HOOK)'),4);self.assertIn('str(CANDIDATE_HOOK)',s);self.assertIn("'boatattack': {'enabled': False",s)
    def test_real128_disabled_prepare(self):
        import importlib.util, contextlib, io
        spec=importlib.util.spec_from_file_location('candidate_driver',c.HERE/'run_candidate_post_reboot.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
        proof_path=self.out/'compiled/candidate-proof.json';round_path=self.out/'round-128'
        with contextlib.redirect_stdout(io.StringIO()):
            config=driver.prepare(driver.BASE/'demo-manifest.json',driver.HERE/'shot-tiers.json',driver.BASE/'t3/install-index-final.json',round_path,'00000000-0000-0000-0000-000000000000',c.pinned(self.proof['smoke']),serial=self.proof['serial'],candidate_proof=proof_path,candidate_sha=c.sha(proof_path))
        self.assertEqual(config['apps'],128);self.assertFalse(config['execution_enabled']);self.assertFalse(config['special_slots']['boatattack']['enabled'])
        for row in config['window_bindings']:
            plan=c.read(c.expand(row['path']));self.assertFalse(plan['execution_enabled'])
            for key in ['after_lock','before_unlock']:self.assertEqual(Path(c.expand(plan[key][1])).name,'candidate_identity.py')
    def test_recording_full_readback(self):
        proof=self.proof;expected=proof['expected'];base=c.read(c.BASE)['expected'];runtime,boot=c.parts({p:expected[p] for p in base})
        class RecordingReader:
            def absent(self,target):
                assert target==c.ROUTEB;return True
            def shell(self,cmd):
                if cmd=='cat /proc/sys/kernel/random/boot_id':return 0,'11111111-1111-1111-1111-111111111111'
                if cmd.startswith('sha256sum '):
                    rows=boot if 'arm64/*' in cmd else runtime if '*.so' in cmd else {p:expected[p] for p in cmd.split()[1:]}
                    return 0,'\n'.join(h+'  '+p for p,h in rows.items())
                if cmd=='ps -A -o PID,PPID,UID,NAME':return 0,'PID PPID UID NAME\n300 1 0 appspawn-x\n400 1 0 appspawn-x'
                if cmd=='readlink /proc/300/exe':return 0,'/system/bin/appspawn-x'
                if cmd=='readlink /proc/400/exe':return 0,'/data/local/tmp/asx/appspawn-x'
                if cmd=='df -k /data':return 0,'recorded fixture storage'
                if cmd=='param get const.ohos.fullname':return 0,'OpenHarmony-6.1.0.31'
                raise AssertionError(cmd)
        out=self.out/'recording';out.mkdir();r=c.check(RecordingReader(),proof,out,'00000000-0000-0000-0000-000000000000');self.assertTrue(r['passed']);self.assertEqual(r['parent_pids'],['300'])
if __name__=='__main__':unittest.main()
