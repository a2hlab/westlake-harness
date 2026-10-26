"""Transport-boundary tests; actual SSH acceptance is recorded separately."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / 'artifact_fetch.py'
spec = importlib.util.spec_from_file_location('artifact_fetch', FILE)
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.sha = hashlib.sha256(b'known demo bytes').hexdigest()
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'schema': 'westlake-artifact-release/v1',
            'release_id': 'test-demo', 'files': [{'path': 'runtime/demo.so',
            'sha256': self.sha, 'size': 16, 'mode': 420, 'role': 'runtime'}]}))
        self.args = argparse.Namespace(manifest=str(self.manifest), manifest_sha256=None,
            remote='test-host', remote_store='artifact-store', cache=str(self.root/'cache'),
            dest=str(self.root/'dest'), receipt=str(self.root/'receipt.json'))

    def test_remote_source_rejects_command_syntax(self):
        for host, root in [('host;echo', 'store'), ('-oProxyCommand=x', 'store'),
                           ('host', 'a/../b'), ('host', '$HOME/store'), ('host', 'a b')]:
            with self.subTest(host=host, root=root), self.assertRaises(ValueError):
                fetch.transport_source(host, root)

    def test_remote_store_supports_relative_and_absolute_paths(self):
        self.assertEqual(fetch.transport_source('lab', 'artifacts'), 'lab:artifacts/')
        self.assertEqual(fetch.transport_source('lab', '/srv/artifacts/'), 'lab:/srv/artifacts/')

    def test_existing_paths_are_preserved(self):
        for name in ('cache', 'dest', 'receipt'):
            with self.subTest(name=name):
                path = Path(getattr(self.args, name)); path.write_bytes(b'keep')
                with self.assertRaises(ValueError): fetch.fetch(self.args)
                self.assertEqual(path.read_bytes(), b'keep'); path.unlink()

    def test_symlink_parent_rejected(self):
        link = self.root / 'link'; link.symlink_to(self.root, target_is_directory=True)
        self.args.cache = str(link/'new-cache')
        with self.assertRaises(ValueError): fetch.fetch(self.args)

    def test_manifest_pin_checked_before_transfer(self):
        self.args.manifest_sha256 = '0'*64
        with patch.object(fetch, 'execute') as execute:
            with self.assertRaises(ValueError): fetch.fetch(self.args)
            execute.assert_not_called()
        self.assertFalse(Path(self.args.receipt).exists())

    def test_invalid_manifest_cannot_create_paths(self):
        for value in [[], {}, {'schema': 'westlake-artifact-release/v1', 'files':
                              [{'sha256': '../../escape'}]}]:
            self.manifest.write_text(json.dumps(value))
            with self.assertRaises(ValueError): fetch.fetch(self.args)
            self.assertFalse(Path(self.args.cache).exists())

    def test_transfer_failure_does_not_fallback_to_local_source(self):
        (self.root/'local-original.so').write_bytes(b'known demo bytes')
        with patch.object(fetch, 'execute', side_effect=RuntimeError('remote object missing')) as execute:
            result = fetch.fetch(self.args)
        self.assertFalse(result['success']); self.assertFalse(result['local_fallback'])
        self.assertFalse(Path(self.args.dest).exists())
        self.assertEqual(execute.call_count, 1)
        self.assertFalse(json.loads(Path(self.args.receipt).read_text())['success'])

    def test_filelist_contains_only_hash_object_paths(self):
        with patch.object(fetch, 'execute', side_effect=RuntimeError('stop at transport')):
            fetch.fetch(self.args)
        lines = (Path(self.args.cache)/'requested-objects.txt').read_text().splitlines()
        self.assertEqual(lines, ['objects/sha256/'+self.sha[:2]+'/'+self.sha])

    def test_transport_fixture_with_real_verify_and_restore(self):
        # Only the network boundary is substituted. The production verifier/restorer run normally.
        original_execute = fetch.execute
        def transfer(argv, report, timeout=3600):
            if argv[0] != 'rsync': return original_execute(argv, report, timeout)
            cache = Path(self.args.cache)
            obj = cache/'objects/sha256'/self.sha[:2]/self.sha
            obj.parent.mkdir(parents=True); obj.write_bytes(b'known demo bytes')
            report['commands'].append({'argv': argv, 'rc': 0, 'test_double': 'local transport fixture'})
        with patch.object(fetch, 'execute', side_effect=transfer):
            result = fetch.fetch(self.args)
        self.assertTrue(result['success'], result)
        self.assertEqual((Path(self.args.dest)/'runtime/demo.so').read_bytes(), b'known demo bytes')
        self.assertEqual(len(result['commands']), 3)


if __name__ == '__main__':
    unittest.main()
