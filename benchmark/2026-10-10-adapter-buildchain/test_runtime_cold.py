#!/usr/bin/env python3
"""Safety known answers for fresh-directory preparation; no compiler/board invoked."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cold', HERE/'prepare_runtime_cold.py')
cold=importlib.util.module_from_spec(spec); spec.loader.exec_module(cold)
W=Path(os.environ.get('WORKSPACES', HERE.parents[2]))

class RuntimeColdPreparationTests(unittest.TestCase):
    def test_reused_directory_rejects_before_historical_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'reused'):
                cold.prepare('/nonexistent', tmp)

    @unittest.skipUnless((W/'westlake-inputs/generations/u13-runtime-m1-v1/build/u13/recipe.sh').is_file(), 'historical inputs not installed')
    def test_real_preparation_redirects_every_output_and_retains_flags(self):
        b=W/'westlake-harness-bms-deploy'
        witness=b/'benchmark/2026-09-30-n4-native/egl-object.txt'
        before=witness.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            out=cold.prepare(W, Path(tmp)/'fresh')
            n4=(out/'n4.sh').read_text(); n2=(out/'n2.sh').read_text()
            self.assertIn('> "$OUT/egl-object.txt"', n4)
            self.assertNotIn('> "$HERE/egl-object.txt"', n4)
            self.assertIn('> "$OUT/gl-identities.txt"', n2)
            self.assertIn('cmp "$OUT/gl_forwarders.c"', n2)
            recipe=(out/'recipe.sh').read_text()
            self.assertNotIn('bms/src/.work/n4-native/gl/EGLImpl.o', recipe)
            self.assertNotIn('bms/src/.work/n2-native/gl/GLImpl.o', recipe)
            self.assertNotIn('u13-runtime-m1-v1/build/u13/runtime-objects/n10b-', recipe)
            self.assertIn('N3B_WITH_PUBLICATION=1', (out/'driver.sh').read_text())
            self.assertEqual(6, (out/'emboss.sh').read_text().count(' -c '))
        self.assertEqual(before, witness.read_bytes())

if __name__=='__main__': unittest.main()
