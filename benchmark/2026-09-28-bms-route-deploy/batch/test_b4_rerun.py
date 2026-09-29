"""No real inputs/transport: all 66 keys exercise runner scheduling with FakeBoard."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import bms_batch as b
import b4_rerun as r
import test_bms_batch as fixtures


def smoke(destination):
    config, apps = r.load_plan()
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    inputs = root/'fixture-inputs'
    synthetic = []
    for entry in apps:
        directory = inputs/entry['key']; directory.mkdir(parents=True)
        (directory/'original.apk').write_bytes(('synthetic APK '+entry['key']).encode())
        app = dict(entry, package=fixtures.PKG, launch_activity=fixtures.ABILITY,
                   apk_sha256=b.sha(directory/'original.apk'))
        b.save(directory/'app-input.json', {'application': {'package':fixtures.PKG,'launch_activity':fixtures.ABILITY}, 'apk_sha256':app['apk_sha256']})
        synthetic.append(app)
    by_key = {a['key']:a for a in synthetic}
    plans = []
    with patch.object(subprocess, 'run', side_effect=AssertionError('offline smoke must not invoke any external process')):
        for shard in config['shards']:
            # The real corpus selection is planned using the exact dispatched args.
            args = [a for a in shard['runner_args'] if a != '--execute']
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                b.main(args)
            plan = json.loads(stream.getvalue())
            assert [a['key'] for a in plan['apps']] == shard['keys']
            out = root/'runs'/shard['relative_artifact_directory']; out.mkdir(parents=True)
            entries = [by_key[k] for k in shard['keys']]
            b.save(out/'plan.json', dict(apps=entries,run_id=shard['run_id'],serial=shard['serial'],options=plan['options']))
            board = fixtures.FakeBoard(); board.serial = shard['serial']
            clock = [0.0]
            # No fault in this success fixture; fault-attribution negative controls are separate tests.
            board.faults_before=[]; board.faults_after=[]
            with patch.object(b.time, 'monotonic', side_effect=lambda:clock[0]), patch.object(b.time, 'sleep', side_effect=lambda sec:clock.__setitem__(0,clock[0]+sec)), contextlib.redirect_stdout(io.StringIO()):
                records = b.run_batch(board, entries, inputs, out, shard['run_id'],20,**plan['options'])
            assert len(records)==22 and all(x['status']=='captured' for x in records)
            plans.append({'name':shard['name'],'serial':shard['serial'],'keys':shard['keys'],'plan':plan,
                          'simulated_records':len(records),'simulated_captures':sum(len(x['screenshots']) for x in records),
                          'external_subprocesses':0,'device_commands':0,'fake_board_calls':len(board.calls)})
        aggregate = r.aggregate(config,synthetic,root/'runs')
    aggregate['synthetic_fixture_only']=True
    aggregate['warning']='All runtime outcomes are fabricated by FakeBoard; this is NOT the real v4 histogram.'
    b.save(root/'fixture-v4.json',aggregate)
    b.save(root/'smoke.json',{'task':59,'synthetic_fixture_only':True,'plans':plans,'total':66,'device_commands':0})
    return config,synthetic,root/'runs',aggregate,plans


class RerunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.config,cls.apps,cls.runs,cls.output,cls.plans=smoke(cls.root)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def altered(self,shard_index=0):
        shard=self.config['shards'][shard_index]
        path=self.runs/shard['relative_artifact_directory']/'summary.json'
        return shard,path,r.read(path)
    def test_all_three_master_cli_plans_and_66_fake_records(self):
        self.assertEqual([p['simulated_records'] for p in self.plans],[22,22,22])
        self.assertEqual([p['simulated_captures'] for p in self.plans],[44,44,44])
        self.assertEqual(len({k for p in self.plans for k in p['keys']}),66)
        self.assertTrue(all(p['device_commands']==p['external_subprocesses']==0 for p in self.plans))
        self.assertEqual(self.output['category_histogram'],{'alive-at-sample':66})
        self.assertEqual(self.output['visual_verdict'],'pending_review')
    def test_known_wall_families_are_spread(self):
        families={k for s in self.config['shards'] for k in s['historical_family_histogram']}
        for family in families:
            counts=[s['historical_family_histogram'].get(family,0) for s in self.config['shards']]
            self.assertLessEqual(max(counts)-min(counts),1,family)
    def test_known_white_window_group_is_also_spread(self):
        overlay=self.config['additional_known_wall']
        counts=[len(set(overlay['keys'])&set(s['keys'])) for s in self.config['shards']]
        self.assertEqual(counts,[4,5,4])

    def test_duplicate_summary_key_rejected(self):
        shard,path,data=self.altered();changed=copy.deepcopy(data);changed['records'].append(changed['records'][0])
        with patch.object(r,'read',side_effect=lambda p:changed if Path(p)==path else json.loads(Path(p).read_text())):
            with self.assertRaisesRegex(ValueError,'duplicate'):r.aggregate(self.config,self.apps,self.runs)
    def test_wrong_serial_and_stale_run_plan_rejected(self):
        shard,path,_=self.altered();plan_path=path.with_name('plan.json');original=r.read(plan_path)
        for field,value in [('serial','wrong'),('run_id','old-round')]:
            changed=dict(original,**{field:value})
            with self.subTest(field=field),patch.object(r,'read',side_effect=lambda p:changed if Path(p)==plan_path else json.loads(Path(p).read_text())):
                with self.assertRaisesRegex(ValueError,'stale/wrong'):r.aggregate(self.config,self.apps,self.runs)
    def test_missing_shard_is_only_an_explicit_partial(self):
        shard,path,_=self.altered();renamed=path.with_suffix('.saved');path.rename(renamed)
        try:
            with self.assertRaisesRegex(ValueError,'missing shard'):r.aggregate(self.config,self.apps,self.runs)
            result=r.aggregate(self.config,self.apps,self.runs,partial=True)
            self.assertFalse(result['complete']);self.assertEqual(len(result['missing_keys']),22)
            self.assertEqual(result['category_histogram']['not-run'],22)
            self.assertTrue(all(x['first_blocker'] is None for x in result['records'] if x['category']=='not-run'))
        finally:renamed.rename(path)
    def test_manifest_and_runner_pin_drift_rejected(self):
        changed=copy.deepcopy(self.config);changed['runner_sha256']='0'*64
        with patch.object(r,'read',return_value=changed):
            with self.assertRaisesRegex(ValueError,'drift'):r.load_plan()
    def test_changed_image_bytes_refused(self):
        shard,path,data=self.altered();record=data['records'][0];app_dir=path.parent/record['key'];image=r.scoped_path(app_dir,record['screenshots'][0]['path']);original=image.read_bytes();image.write_bytes(b'changed')
        try:
            with self.assertRaisesRegex(ValueError,'changed evidence'):r.aggregate(self.config,self.apps,self.runs)
        finally:image.write_bytes(original)
    def test_aggregate_cli_partial_preserves_all_missing_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'partial.json'
            with contextlib.redirect_stdout(io.StringIO()),patch.object(subprocess,'run',side_effect=AssertionError('no commands')):
                self.assertEqual(r.main(['aggregate','--run-root',temp,'--out',str(output),'--allow-partial']),1)
            result=r.read(output)
            self.assertEqual(result['category_histogram'],{'not-run':66})
            self.assertFalse(result['complete'])
            with self.assertRaisesRegex(ValueError,'overwriting'):r.main(['aggregate','--run-root',temp,'--out',str(output),'--allow-partial'])

    def classified_fixture(self,alive=False,uid=20010055):
        directory=self.root/'classify-case';directory.mkdir(exist_ok=True)
        rec={'status':'foreground_unconfirmed','install':{'return_code':0,'success_text':True},'clicked':True,
             'observed_pids':[42] if alive else [],'package':fixtures.PKG,'bms':{'uid':uid},
             'screenshots':[{'captured':False,'foreground':{'observed_pids':[42],'confirmed':False}}]}
        return directory,rec
    def test_foreign_uid_fault_is_not_target_blocker(self):
        directory,rec=self.classified_fixture();f=directory/'crash-1';f.write_text('Uid:99999\n#00 pc 123 getSharedPreferences\n')
        rec['diagnostics']={'faultlogs':[{'path':str(f),'sha256':b.sha(f)}]}
        self.assertEqual(r.classify(rec,directory)['first_blocker'],'unknown')
    def test_exact_uid_crash_has_original_line_and_family(self):
        directory,rec=self.classified_fixture();f=directory/'crash-2';f.write_text('Uid:20010055\n#00 pc 123 getSharedPreferences\n')
        rec['diagnostics']={'faultlogs':[{'path':str(f),'sha256':b.sha(f)}]}
        result=r.classify(rec,directory)
        self.assertEqual(result['first_blocker'],'b6-family-context')
        self.assertEqual(result['fatal_observation']['line'],2)
    def test_hilog_filters_noise_foreign_pid_and_requires_fatal_text(self):
        directory,rec=self.classified_fixture();log=directory/'hilog.txt'
        log.write_text('09-29 12:00:00.001 42 42 I HDC_LOG: UnsatisfiedLinkError\n09-29 12:00:00.002 777 777 E Java: UnsatisfiedLinkError\n09-29 12:00:00.003 42 42 I Java: getSharedPreferences enter\n09-29 12:00:00.004 42 42 E Java: UnsatisfiedLinkError: SQLiteConnection.nativeOpen\n')
        rec['diagnostics']={'path':str(log),'sha256':b.sha(log),'faultlogs':[]}
        result=r.classify(rec,directory)
        self.assertEqual(result['first_blocker'],'unsatisfied-link');self.assertEqual(result['fatal_observation']['line'],4)
    def test_alive_with_fatal_is_kept_without_inventing_late_timing(self):
        directory,rec=self.classified_fixture(alive=True);f=directory/'crash-3';f.write_text('Uid:20010055\n#00 pc 123 fdsan_error\n')
        rec['diagnostics']={'faultlogs':[{'path':str(f),'sha256':b.sha(f)}]}
        result=r.classify(rec,directory)
        self.assertEqual(result['category'],'alive-at-sample');self.assertTrue(result['alive_with_fatal_evidence'])
        self.assertIsNone(result['first_blocker'])
    def test_interrupted_install_failed_and_unlaunched_not_counted_as_exit(self):
        directory,rec=self.classified_fixture()
        for update,expected in [({'status':'batch_interrupted'},'interrupted'),({'install':{'return_code':0,'success_text':False}},'rerun956-install-failed'),({'clicked':False},'collection-failed'),({'status':'app_failed','observed_pids':[42]},'collection-failed')]:
            self.assertEqual(r.classify(dict(rec,**update),directory)['category'],expected)


if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--smoke-out':
        smoke(Path(sys.argv[2]))
    else:
        unittest.main(verbosity=2)
