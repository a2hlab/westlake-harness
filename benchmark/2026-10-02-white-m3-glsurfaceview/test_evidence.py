import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('m3_collect', HERE / 'collect.py')
COLLECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECT)


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((HERE / 'results.json').read_text())
        cls.rows = {row['key']: row for row in cls.result['rows']}

    def test_three_single_session_children_precede_gl_exception(self):
        for key, session in zip(COLLECT.WHITE, [652, 664, 674]):
            with self.subTest(key=key):
                row = self.rows[key]
                summary = row['summary']
                self.assertEqual(summary['sessions'], [session])
                self.assertEqual(len(summary['children']), 1)
                self.assertEqual(len(summary['gl_errors']), 1)
                self.assertEqual(summary['children'][0]['session'], session)
                self.assertNotEqual(int(summary['children'][0]['pointer'], 16), 0)
                self.assertLess(summary['children'][0]['line'], summary['gl_errors'][0]['line'])
                self.assertEqual(summary['gl_thread_from_surface_calls'], [])
                self.assertEqual(summary['gl_thread_egl_pointer_calls'], [])
                self.assertTrue(all(item['pid'] in row['app_pids'] for item in row['events']))
                self.assertFalse(any('BBQ.getSurface: ohNativeWindow null' in item['text'] for item in row['events']))
                self.assertGreater(row['coverage']['gap_seconds'], 0)
                self.assertFalse(summary['last_session_read_instrumented'])
                self.assertFalse(summary['egl_jni_input_pointer_observed'])
                for library in self.result['libraries']:
                    self.assertTrue(any(library['sha256'] in pin['text'] for pin in row['fingerprint_pins']))
                self.assertTrue(any(self.result['framework']['jar_sha256'] in pin['text'] for pin in row['fingerprint_pins']))

    def test_lit_gl_failure_and_m1_controls(self):
        shader = self.rows[COLLECT.CONTROLS[0]]
        self.assertEqual(shader['signed']['verdict'], 'lit')
        self.assertEqual(len(shader['summary']['gl_errors']), 1)
        self.assertEqual(shader['summary']['sessions'], [951])
        m1 = self.rows['noice']
        self.assertEqual(m1['summary']['sessions'], [644, 645])
        self.assertTrue(any('ohNativeWindow null (sessionId=644' in item['text'] for item in m1['events']))
        self.assertTrue(any('session=645 target=' in item['text'] for item in m1['events']))

    def test_native_lookup_and_java_catch_are_not_a_device_unlock(self):
        native = (HERE / 'evidence/runtime-eglimpl-disassembly.txt').read_text()
        for address in ['1ddbc4:', '1ddbc8:', '1dd9a8:', '1dd9ac:', '1dd9b8:', '1dd9c0:', '1ddb54:']:
            self.assertIn(address, native)
        self.assertIn('dlsym@plt', native)
        java = json.loads((HERE / 'evidence/framework-methods.json').read_text())
        text = '\n'.join(item['text'] for item in java['lines'])
        self.assertIn('SurfaceHolder;.getSurface', text)
        self.assertIn('android/util/Log;.e', text)
        self.assertIn('IllegalArgumentException', text)
        self.assertIn('mSurface:Landroid/view/Surface;', text)
        self.assertIn('Landroid/view/Surface;.<init>', text)
        conclusion = self.result['conclusion']
        self.assertFalse(conclusion['same_as_m1_last_session_overwrite'])
        self.assertEqual(conclusion['m1_expected_gl_exception_moves'], 0)
        self.assertEqual(conclusion['m3_conditional_gl_exception_moves'], 3)
        self.assertEqual(conclusion['measured_unlocks'], 0)
        self.assertFalse(conclusion['candidate_built'])

    def test_workspace_portability_does_not_rewrite_a_sibling_as_repo(self):
        old_repo = COLLECT.REPO
        try:
            COLLECT.REPO = COLLECT.WS / 'westlake-harness'
            sibling = COLLECT.WS / 'westlake-harness-u7-executor/benchmark/record.json'
            self.assertEqual(COLLECT.portable(sibling), '$WORKSPACES/westlake-harness-u7-executor/benchmark/record.json')
        finally:
            COLLECT.REPO = old_repo


if __name__ == '__main__':
    unittest.main(verbosity=2)
