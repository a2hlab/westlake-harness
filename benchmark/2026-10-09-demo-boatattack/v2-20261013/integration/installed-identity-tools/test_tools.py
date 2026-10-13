#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file())
os.environ.setdefault('WORKSPACES',str(ROOT.parent))
import collect_actual as col
import assemble_request as ass
BOOT='35da6f13-e7b1-4472-a36a-5c4a69d5f191'

class Tools(unittest.TestCase):
    def fake(self,argv,**kwargs):
        self.assertEqual(argv[1:4],['-t',col.SERIAL,'shell'])
        cmd=shlex.split(argv[-1])[2].removesuffix(';')
        marker=re.search(r'__EXACT_READ_RC_[a-f0-9]+__',argv[-1])[0]
        apps,_=col.plan(BOOT)
        if cmd.startswith('cat '):body=BOOT+'\n'
        elif cmd=='bm dump -a':body='ID: 100:\n'+''.join('\t'+a['package']+'\n' for a in apps)
        elif cmd.startswith('sha256sum '):
            bypath={'/data/app/el1/bundle/public/'+a['package']+'/android/base.apk':a['apk_sha256'] for a in apps}
            body=''.join(bypath[p]+'  '+p+'\n' for p in shlex.split(cmd)[1:])
        else:raise AssertionError('unexpected command')
        return subprocess.CompletedProcess(argv,0,(body+'\n'+marker+'0\n').encode(),b'')

    def test_preview_never_calls_subprocess(self):
        with tempfile.TemporaryDirectory() as t,patch.object(col.subprocess,'run',side_effect=AssertionError('device call')):
            out=Path(t)/'not-created'
            with patch.object(sys,'argv',['collector','--boot-id',BOOT,'--out',str(out)]),contextlib.redirect_stdout(io.StringIO()) as log:
                self.assertEqual(col.main(),0)
            self.assertIn('PREVIEW_NO_DEVICE_CALLS',log.getvalue());self.assertFalse(out.exists())

    def test_recording_collector_11_reads_and_unchanged_compiler_compatibility(self):
        spec=importlib.util.spec_from_file_location('compiler_tests',HERE.parent/'installed-identity-5ea/test_compile_index.py')
        fixturemod=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixturemod)
        fixture=fixturemod.CompileIndex('test_synthetic_full128_preserves_driver_interface');fixture.setUp()
        try:
            out=fixture.dir/'captured'
            with patch.object(col.subprocess,'run',side_effect=AssertionError('unmocked device call')):
                result=col.collect(out,BOOT,runner=self.fake)
            self.assertEqual(result['matching'],128);self.assertFalse(result['issues'])
            self.assertEqual(len(result['raw_readings']),11)
            fixture.req['final']=col.read(out/'final.json')
            index=fixture.run_compile();self.assertEqual(len(index),128)
        finally:fixture.doCleanups()

    def test_rc0_connect_failure_stays_incomplete(self):
        def bad(argv,**kw):return subprocess.CompletedProcess(argv,0,b'',b'Connect server failed\n')
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'capture';r=col.collect(out,BOOT,runner=bad)
            self.assertEqual(r['status'],'READONLY_CAPTURE_INCOMPLETE')
            self.assertFalse((out/'final.json').exists())
            self.assertEqual((out/'boot-before.stderr.txt').read_text(),'Connect server failed\n')

    def test_actual_pain_nine_original_time_bindings(self):
        rows,missing,audit=ass.discover([ass.OUTER/'pain-control-completion/install',ass.OUTER/'missing-nine-install'],BOOT)
        self.assertEqual(len(rows),10);self.assertEqual(missing,['fd-noice'])
        for row in audit:self.assertLessEqual(row['before'],row['install']);self.assertLessEqual(row['install'],row['after']);self.assertLessEqual(row['after'],row['record_finished_at'])
        receipt=col.read(ass.PREFLIGHT/'bundles.json');self.assertIsInstance(receipt['time'],float)

    def test_missing_noice_prevents_request(self):
        with self.assertRaisesRegex(ValueError,'fd-noice'):
            ass.build(None,[ass.OUTER/'pain-control-completion/install',ass.OUTER/'missing-nine-install'],BOOT)

    def test_duplicate_install_roots_rejected(self):
        with self.assertRaisesRegex(ValueError,'ambiguous actual install'):
            ass.discover([ass.OUTER/'pain-control-completion/install']*2,BOOT)

if __name__=='__main__':unittest.main(verbosity=2)
