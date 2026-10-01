import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
spec = importlib.util.spec_from_file_location('cutoff_batch', ROOT / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py')
batch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = batch
spec.loader.exec_module(batch)


class Cutoff(unittest.TestCase):
    def exercise(self, clock):
        board = Mock(boot='boot')
        board.shell.return_value = (0, 'OpenHarmony-6.1.0.31')
        entries = [{'key': 'one'}, {'key': 'two'}]
        captured = []
        def collect(_board, entry, _root, directory, *args, **kwargs):
            directory.mkdir()
            captured.append(entry['key'])
            return {'key': entry['key'], 'status': 'captured'}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            with patch.object(batch, 'preflight', return_value={}), patch.object(batch.installation_chain, 'collect', return_value={'verdict': 'match'}), patch.object(batch, 'runtime_fingerprint', return_value={}), patch.object(batch, 'boot_image_fingerprint', return_value={}), patch.object(batch, 'collect_app', side_effect=collect), patch.object(batch, 'write_facts', return_value='TOTAL recorded'), patch.object(batch.time, 'time', side_effect=clock):
                records = batch.run_batch(board, entries, 'inputs', out, 'run', 20, stop_new_keys_at=101)
            return captured, records, json.loads((out / 'summary.json').read_text())

    def test_finishes_current_then_does_not_start_next_at_cutoff(self):
        keys, records, summary = self.exercise([100, 101])
        self.assertEqual(keys, ['one'])
        self.assertEqual(len(records), 1)
        self.assertEqual(summary['not_run'], ['two'])
        self.assertTrue(summary['stopped_at_new_key_deadline'])

    def test_elapsed_window_does_not_start_any_key(self):
        keys, records, summary = self.exercise([101])
        self.assertEqual((keys, records), ([], []))
        self.assertEqual(summary['not_run'], ['one', 'two'])


if __name__ == '__main__':
    unittest.main()
