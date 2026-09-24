"""Known-answer cache invalidation and corpus-boundary checks; no board or APK scanner."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('static_pipeline', ROOT / 'tools/static_pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class StaticPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for sub in ['scans', 'oh', 'maps', 'logs']:
            (self.root / sub).mkdir()
        self.apps = {}
        for key in ['alpha', 'beta']:
            apk = self.root / (key + '.apk')
            apk.write_bytes(key.encode())
            runtime = self.root / (key + '-runtime.json')
            runtime.write_text(json.dumps({'runtime_lock_id': 'lock-1', 'classes': {}}))
            self.apps[key] = {'input': str(apk), 'runtime_index': str(runtime)}
        self.calls = []
        self.version = {'package': 'fixture-v1', 'implementation_sha256': 'implementation-1'}
        self.addCleanup(patch.stopall)
        patch.object(pipeline, 'run', side_effect=self.fake_run).start()

    def fake_run(self, command, log):
        stage = command[1]
        output = Path(command[command.index('--out') + 1])
        key = log.name.split('.')[0]
        self.calls.append((key, stage))
        identity = pipeline.fingerprint(self.apps[key], self.root, self.version)
        if stage == 'scan':
            value = {'apk': {'sha256': identity['input_sha256']}, 'runtime_lock_id': identity['runtime_lock_id'],
                     'inventory': {'native_resolution': {'target_abi': 'arm64-v8a', 'abi_status': 'target-abi-available'}}}
        elif stage == 'oh-resolve':
            value = {'apps': {key: {}}}
        else:
            output.mkdir(exist_ok=True)
            output = output / 'gap-map.json'
            value = {'app': {'apk_sha256': identity['input_sha256']}, 'rows': []}
        output.write_text(json.dumps(value))
        return 0

    def run_all(self):
        result = {key: pipeline.one(key, app, self.root, self.version)[1] for key, app in self.apps.items()}
        self.assertTrue(all(v.startswith('ok (') for v in result.values()), result)
        return result

    def warm(self):
        self.run_all()
        self.assertEqual(len(self.calls), 6)
        self.calls.clear()

    def test_unchanged_cache_and_single_app_runtime_change(self):
        self.warm()
        self.assertTrue(all('cached' in s for s in self.run_all().values()))
        self.assertEqual(self.calls, [])
        runtime = Path(self.apps['alpha']['runtime_index'])
        runtime.write_text(json.dumps({'runtime_lock_id': 'lock-2', 'classes': {}}))
        self.run_all()
        self.assertEqual(self.calls, [('alpha', 'scan'), ('alpha', 'oh-resolve'), ('alpha', 'gap-map')])
        receipt = json.loads((self.root / 'maps/alpha/pipeline-state.json').read_text())
        self.assertEqual(receipt['fingerprint']['runtime_lock_id'], 'lock-2')

    def test_input_bytes_change_at_same_path_invalidates_only_that_app(self):
        self.warm()
        Path(self.apps['beta']['input']).write_bytes(b'replacement APK')
        self.run_all()
        self.assertEqual(self.calls, [('beta', 'scan'), ('beta', 'oh-resolve'), ('beta', 'gap-map')])

    def test_changed_runtime_bytes_even_with_same_lock_id_invalidate(self):
        self.warm()
        Path(self.apps['alpha']['runtime_index']).write_text(json.dumps({'runtime_lock_id': 'lock-1', 'classes': {'new': {}}}))
        self.run_all()
        self.assertEqual({key for key, _ in self.calls}, {'alpha'})
        self.assertEqual(len(self.calls), 3)

    def test_changed_tool_implementation_invalidates_all_apps(self):
        self.warm()
        self.version['implementation_sha256'] = 'implementation-2'
        self.run_all()
        self.assertEqual(len(self.calls), 6)

    def test_legacy_files_without_receipt_are_not_trusted(self):
        self.warm()
        (self.root / 'maps/alpha/pipeline-state.json').unlink()
        self.run_all()
        self.assertEqual({key for key, _ in self.calls}, {'alpha'})
        self.assertEqual(len(self.calls), 3)
        self.assertTrue(list((self.root / 'history/alpha').iterdir()))

    def test_corrupt_oh_rebuilds_oh_and_downstream_only(self):
        self.warm()
        (self.root / 'oh/alpha.json').write_text('{invalid')
        self.run_all()
        self.assertEqual(self.calls, [('alpha', 'oh-resolve'), ('alpha', 'gap-map')])

    def test_failed_stage_cannot_be_cached_and_upstream_can_resume(self):
        def failure(command, log):
            if command[1] == 'oh-resolve':
                Path(command[command.index('--out') + 1]).write_text('{partial')
                return 1
            return self.fake_run(command, log)
        with patch.object(pipeline, 'run', side_effect=failure):
            _, status = pipeline.one('alpha', self.apps['alpha'], self.root, self.version)
        self.assertEqual(status, 'oh failed')
        self.assertFalse((self.root / 'oh/alpha.json').exists())
        self.calls.clear()
        _, status = pipeline.one('alpha', self.apps['alpha'], self.root, self.version)
        self.assertTrue(status.startswith('ok ('), status)
        self.assertEqual(self.calls, [('alpha', 'oh-resolve'), ('alpha', 'gap-map')])

    def test_tampered_app_receipt_runtime_lock_is_not_reused(self):
        self.warm()
        path = self.root / 'maps/beta/pipeline-state.json'
        state = json.loads(path.read_text())
        state['fingerprint']['runtime_lock_id'] = 'wrong-lock'
        path.write_text(json.dumps(state))
        self.run_all()
        self.assertEqual(self.calls, [('beta', 'scan'), ('beta', 'oh-resolve'), ('beta', 'gap-map')])


class AggregateGapsTests(unittest.TestCase):
    def test_outside_map_is_ignored_even_if_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apps = {f'app-{i:03d}': {'stack': 'java'} for i in range(100)}
            for key in apps:
                path = root / 'maps' / key
                path.mkdir(parents=True)
                (path / 'gap-map.json').write_text(json.dumps({'rows': [{'id': 'common', 'verdict': 'missing'}]}))
            extra = root / 'maps' / 'not-in-corpus'
            extra.mkdir()
            (extra / 'gap-map.json').write_text('deliberately malformed: must not be parsed')
            corpus = root / 'corpus.json'
            corpus.write_text(json.dumps({'apps': apps}))
            result = subprocess.run([sys.executable, str(ROOT / 'tools/aggregate_gaps.py'), str(root), str(corpus)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            leaderboard = json.loads((root / 'leaderboard.json').read_text())
            self.assertEqual(set(leaderboard['apps']), set(apps))
            self.assertEqual(leaderboard['ignored_apps'], ['not-in-corpus'])
            self.assertEqual(leaderboard['gaps'][0]['apps'], 100)
            md = (root / 'LEADERBOARD.md').read_text()
            self.assertIn('— 100 apps', md.splitlines()[0])
            self.assertIn('`not-in-corpus`', md)

    def test_missing_corpus_map_fails_instead_of_reporting_smaller_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'maps').mkdir()
            corpus = root / 'corpus.json'
            corpus.write_text(json.dumps({'apps': {'missing': {}}}))
            result = subprocess.run([sys.executable, str(ROOT / 'tools/aggregate_gaps.py'), str(root), str(corpus)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('missing corpus maps: missing', result.stderr)
            self.assertFalse((root / 'leaderboard.json').exists())


if __name__ == '__main__':
    unittest.main()
