#!/usr/bin/env python3
"""Unit + replay tests for the G3 gate bcp_duplicate_classes.py.

Run: python3 -m unittest scripts.lab.test_bcp_duplicate_classes  (or run this file).
The pure gate logic (find_duplicates / exit codes) is tested with synthetic class maps
so no dex/jars are needed. The dex parser and the real 9-jar replay are covered by an
integration test that is skipped when no generation package is on disk.
"""
import glob
import json
import os
import tempfile
import unittest
from pathlib import Path

import bcp_duplicate_classes as g


class FindDuplicatesTests(unittest.TestCase):
    def test_no_duplicates(self):
        cm = {'a': ['foo/A', 'foo/B'], 'b': ['foo/C']}
        self.assertEqual(g.find_duplicates(cm, allow=[]), [])

    def test_unexpected_duplicate_is_violation(self):
        cm = {'framework': ['android/net/NetworkInfo'], 'adapter-mainline-stubs': ['android/net/NetworkInfo']}
        dups = g.find_duplicates(cm, allow=[])
        self.assertEqual(dups, [('android/net/NetworkInfo',
                                 ['adapter-mainline-stubs', 'framework'], False)])

    def test_allowed_duplicate_not_violation(self):
        c = 'android/nfc/NfcFrameworkInitializer'
        cm = {'framework': [c], 'adapter-mainline-stubs': [c]}
        dups = g.find_duplicates(cm, allow=[c])
        self.assertEqual(dups, [(c, ['adapter-mainline-stubs', 'framework'], True)])

    def test_triple_definition_lists_all_jars_sorted(self):
        cm = {'core-oj': ['x/Y'], 'framework': ['x/Y'], 'okhttp': ['x/Y']}
        (c, jars, allowed), = g.find_duplicates(cm, allow=[])
        self.assertEqual((c, jars, allowed), ('x/Y', ['core-oj', 'framework', 'okhttp'], False))

    def test_default_allow_is_the_seven_initializers(self):
        # The built-in allow-list is exactly the v3c stubs-BCP overlap (see T7C doc).
        self.assertEqual(len(g.DEFAULT_ALLOW), 7)
        self.assertTrue(all(c.endswith('Initializer') for c in g.DEFAULT_ALLOW))


class MainExitCodeTests(unittest.TestCase):
    def _run_with_classmap(self, classmap, allow=None):
        with tempfile.TemporaryDirectory() as d:
            cmpath = Path(d) / 'cm.json'
            cmpath.write_text(json.dumps(classmap))
            argv = ['--classmap', str(cmpath)]
            if allow is not None:
                ap = Path(d) / 'allow.json'
                ap.write_text(json.dumps(allow))
                argv += ['--allow', str(ap)]
            return g.main(argv)

    def test_exit0_when_only_allowed(self):
        c = 'android/telephony/TelephonyFrameworkInitializer'
        rc = self._run_with_classmap({'framework': [c], 'adapter-mainline-stubs': [c]})
        self.assertEqual(rc, 0)

    def test_exit1_on_unexpected_duplicate(self):
        c = 'android/net/NetworkInfo'
        rc = self._run_with_classmap({'framework': [c], 'adapter-mainline-stubs': [c]})
        self.assertEqual(rc, 1)

    def test_exit0_when_no_duplicates(self):
        rc = self._run_with_classmap({'framework': ['a/B'], 'adapter-mainline-stubs': ['c/D']})
        self.assertEqual(rc, 0)

    def test_custom_allow_overrides_default(self):
        c = 'android/net/NetworkInfo'
        rc = self._run_with_classmap({'framework': [c], 'adapter-mainline-stubs': [c]}, allow=[c])
        self.assertEqual(rc, 0)

    def test_json_output(self):
        import io
        import contextlib
        c = 'x/Dup'
        with tempfile.TemporaryDirectory() as d:
            cmpath = Path(d) / 'cm.json'
            cmpath.write_text(json.dumps({'a': [c], 'b': [c]}))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = g.main(['--classmap', str(cmpath), '--json'])
            out = json.loads(buf.getvalue())
        self.assertEqual(rc, 1)
        self.assertEqual(out['violations'], 1)
        self.assertEqual(out['duplicates'][0]['class'], c)


def _find_framework_dir():
    """A v3c generation package's framework dir, for the real replay (else None)."""
    ws = Path(__file__).resolve().parents[3]  # .../orca/workspaces
    for p in sorted(glob.glob(str(ws / 'westlake-generation-*/payload/android/framework/adapter-mainline-stubs.jar'))):
        return str(Path(p).parent)
    return None


@unittest.skipUnless(_find_framework_dir(), 'no generation package on disk for the real-jar replay')
class ReplayIntegrationTests(unittest.TestCase):
    """Replay: run the gate on a real v3c BCP set; it must be clean (only the 7 allowed)."""
    def test_v3c_bcp_is_clean(self):
        fdir = _find_framework_dir()
        cm = g.build_classmap_from_dir(fdir)
        self.assertIn('adapter-mainline-stubs', cm)
        self.assertGreater(len(cm['framework']), 1000)  # dex parser really read framework.jar
        dups = g.find_duplicates(cm, g.DEFAULT_ALLOW)
        violations = [d for d in dups if not d[2]]
        self.assertEqual(violations, [], f'v3c BCP must have no unexpected duplicates; got {violations}')
        # every duplicate in a clean v3c set is one of the 7 allowed initializers
        self.assertTrue(all(c in g.DEFAULT_ALLOW for c, _, _ in dups))


if __name__ == '__main__':
    unittest.main()
