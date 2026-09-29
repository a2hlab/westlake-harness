#!/usr/bin/env python3
import hashlib,json,tempfile,unittest
from pathlib import Path
import profile_audit as audit

class Fixtures(unittest.TestCase):
    def setUp(self):
        self.profiles,self.package=audit.context()
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.board=self.profiles['r17o']['boards'][0]
        self.rollback=json.loads((audit.HERE/'execution-revision.json').read_text())['reported_hwui_sha256']

    def run_fixture(self,name='sample',hwui=None,jar=None,board=None):
        run=Path(self.tmp.name)/name/(board or self.board);run.mkdir(parents=True)
        profile=self.profiles['r17o']
        rows,_=audit.projected_hashes(self.package,profile)
        if hwui:rows[audit.HWUI]=hwui
        if jar:rows[audit.JAR]=jar
        boot='51812b02-0000-4000-8000-000000000000'
        installer=[f'capture boot={boot} foundation=979']
        for lib,digest in profile['installer_sha256'].items():
            path='/system/lib64/'+lib;rows[path]=digest
            installer.extend([f'{digest}  {path}',f'{digest}  /proc/979/root{path}'])
        body='\n'.join(f'{h}  {p}' for p,h in sorted(rows.items()))
        fingerprint=hashlib.sha256(body.encode()).hexdigest()[:12]
        (run/'runtime-fingerprint.txt').write_text(body+'\n')
        (run/'facts.txt').write_text(f'RUNTIME fingerprint={fingerprint} files={len(rows)} fixture=true\n')
        (run/'baseline.json').write_text(json.dumps({'boot_id':boot,'runtime_fingerprint':fingerprint}))
        (run/'installer-readback.txt').write_text('\n'.join(installer)+'\n')
        return run

class ProfileTests(Fixtures):
    def test_exact_profile_vs_rollback(self):
        exact=audit.inspect_run(self.run_fixture(),self.profiles,self.package)
        self.assertTrue(exact['same_profile_score_eligible'],exact)
        self.assertEqual(exact['classification'],'exact_frozen_projection')
        drift=audit.inspect_run(self.run_fixture('rollback',hwui=self.rollback),self.profiles,self.package)
        self.assertEqual(drift['classification'],'known_jar_profile_drift')
        self.assertEqual(drift['matching_jar_column'],'r17o')
        self.assertFalse(drift['same_profile_score_eligible'])
        self.assertEqual([x['path'] for x in drift['comparisons']['r17o']['changed']],[audit.HWUI])

    def test_unforecast_jar_has_no_column(self):
        unknown=audit.inspect_run(self.run_fixture(jar='e'*64,hwui=self.rollback),self.profiles,self.package)
        self.assertEqual(unknown['classification'],'unfrozen_or_missing_jar')
        self.assertIsNone(unknown['matching_jar_column'])
        self.assertEqual(unknown['actual_jar_sha256'],'e'*64)
        self.assertFalse(unknown['same_profile_score_eligible'])

    def test_strata_separate_components_and_boards(self):
        runs=[self.run_fixture('a',hwui=self.rollback),self.run_fixture('b',hwui=self.rollback),
              self.run_fixture('c'),self.run_fixture('d',hwui=self.rollback,board='61b06572')]
        result=audit.report(runs,self.profiles,self.package)
        self.assertEqual(len(result['strata']),3)
        self.assertEqual(sorted(len(s['runs']) for s in result['strata']),[1,1,2])
        self.assertEqual(sum(s['eligible_runs'] for s in result['strata']),1)
        self.assertTrue(all(s['same_profile_accuracy'] is None for s in result['strata']))
        self.assertFalse(result['outcomes_read'])

    def test_missing_installer_readback_is_not_verified(self):
        run=self.run_fixture();(run/'installer-readback.txt').unlink()
        result=audit.inspect_run(run,self.profiles,self.package)
        self.assertEqual(result['classification'],'exact_frozen_projection')
        self.assertFalse(result['same_profile_score_eligible'])

class IntegrityTests(Fixtures):
    def test_missing_and_inconsistent_facts_rejected(self):
        for damage in ('missing','fingerprint','baseline'):
            with self.subTest(damage=damage):
                run=self.run_fixture(damage)
                if damage=='missing':(run/'facts.txt').unlink()
                elif damage=='fingerprint':(run/'facts.txt').write_text('RUNTIME fingerprint=000000000000 files=1 fixture=true\n')
                else:(run/'baseline.json').write_text('{}')
                result=audit.inspect_run(run,self.profiles,self.package)
                self.assertEqual(result['classification'],'invalid_evidence')
                self.assertIsNone(result['projection_stratum'])
                self.assertFalse(result['same_profile_score_eligible'])

    def test_frozen_receipt_and_scorer_unchanged(self):
        receipt=audit.engine.verify(audit.FREEZE)
        self.assertEqual(len(receipt['hashes']),104)
        self.assertEqual(audit.engine.sha(audit.FREEZE/'freeze.json'),'f9d4881a121b8bd36603835604e42bca7ab3c59a68f1735c04721ac82ebd143b')
        self.assertEqual(audit.engine.sha(audit.ORIGINAL/'SHA256SUMS'),'b2961b66f88d7d6f4eb0c14c9f956d0ecbe298210f447548dcf480fa8756d41e')
        audit.context()

if __name__=='__main__':unittest.main()
