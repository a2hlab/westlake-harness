import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import trace_ability_stage as trace


class AbilityStageEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((trace.HERE / 'ability-stage-results.json').read_text())

    def test_wrong_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input'
            path.write_bytes(b'wrong generation')
            with self.assertRaises(ValueError):
                trace.identity(path, trace.JAR_HASH)

    def test_pinned_sources_and_disassembly(self):
        self.assertEqual(self.data['jar']['sha256'], trace.JAR_HASH)
        inputs = [self.data['jar'], *self.data['native_inputs'].values(), *self.data['source_inputs']]
        for source in inputs:
            self.assertEqual(hashlib.sha256(Path(source['path']).read_bytes()).hexdigest(), source['sha256'])
        no_reply = (trace.OUT / 'no_reply-native.txt').read_text()
        reply = (trace.OUT / 'reply-native.txt').read_text()
        # Full callback bodies were dumped, not just a selected tail instruction.
        self.assertIn('00000000000c8044', no_reply)
        self.assertIn('00000000000cae58', no_reply)
        self.assertEqual(no_reply.count('<HiLogPrint@plt>'), 2)
        self.assertNotIn('addAbilityStageDone', no_reply)
        self.assertNotIn('scheduleAcceptWantDone', no_reply)
        self.assertIn('c4478:', reply)
        self.assertIn('c72c4:', reply)
        self.assertIn('addAbilityStageDoneEv@plt', reply)
        self.assertIn('scheduleAcceptWantDoneER', reply)

    def test_layout_fingerprints_do_not_claim_full_identity(self):
        items = self.data['fingerprints']
        self.assertEqual(len(items), 10)
        for item in items:
            expected = 'reply' if item['key'] == 'helloworld' else 'no_reply'
            for candidate in item['candidates']:
                self.assertFalse(candidate['deployed_whole_file_hash_verified'])
                self.assertEqual(candidate['base_page_aligned'], candidate['candidate'] == expected)
                if candidate['candidate'] == expected:
                    self.assertEqual(candidate['function_entry_matches'], candidate['observed_count'])
                    self.assertEqual(candidate['observed_count'], 50 if expected == 'reply' else 49)
            self.assertEqual(hashlib.sha256(Path(item['source']['path']).read_bytes()).hexdigest(), item['source']['sha256'])

    def test_b5_bind_and_native_stage_paths_are_separate(self):
        smali = (trace.OUT / 'b5-bridge-smali.txt').read_text()
        runnable = (trace.OUT / 'b5-bind-runnable-smali.txt').read_text()
        self.assertIn('Handler;->post(Ljava/lang/Runnable;)Z', smali)
        self.assertIn('handleBindApplication', smali)
        self.assertIn('sBindAppDone:Z', smali)
        self.assertIn('catchall', runnable)
        self.assertIn('ensureBindApplication', runnable)
        self.assertNotIn('AddAbilityStageDone', smali + runnable)
        self.assertNotIn('addAbilityStageDone', smali + runnable)
        self.assertEqual(self.data['r2']['repair_on_device'], 'unverified')


if __name__ == '__main__':
    unittest.main()
