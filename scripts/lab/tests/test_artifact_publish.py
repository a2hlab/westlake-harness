"""Exercise the actual server publication path on private temporary stores."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import artifact_publish as publish


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.incoming = self.root/'incoming'; self.incoming.mkdir()
        self.store = self.root/'store'
        self.data = b'verified object'
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.rel = Path('objects/sha256')/self.sha[:2]/self.sha
        self.obj = self.incoming/self.rel
        self.obj.parent.mkdir(parents=True); self.obj.write_bytes(self.data)
        self.doc = {'schema': 'westlake-artifact-release/v1', 'release_id': 'demo-1',
                    'files': [{'path': 'lib/a.so', 'sha256': self.sha,
                               'size': len(self.data), 'mode': 420, 'role': 'runtime'}]}
        self.manifest = self.incoming/'manifest.json'
        self.manifest.write_text(json.dumps(self.doc))
        self.args = argparse.Namespace(incoming=str(self.incoming), store=str(self.store))

    def test_publish_and_idempotent_retry(self):
        self.assertTrue(publish.server_publish(self.args)['success'])
        self.assertTrue(publish.server_publish(self.args)['success'])
        self.assertEqual((self.store/self.rel).read_bytes(), self.data)
        self.assertEqual((self.store/'releases/demo-1.json').read_bytes(), self.manifest.read_bytes())

    def test_missing_upload_does_not_publish(self):
        self.obj.unlink()
        with self.assertRaises(RuntimeError): publish.server_publish(self.args)
        self.assertFalse((self.store/'releases/demo-1.json').exists())

    def test_corrupt_existing_object_never_overwritten(self):
        dest = self.store/self.rel; dest.parent.mkdir(parents=True); dest.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): publish.server_publish(self.args)
        self.assertEqual(dest.read_bytes(), b'corrupt')
        self.assertFalse((self.store/'releases/demo-1.json').exists())

    def test_release_id_conflict_never_overwrites(self):
        dest = self.store/'releases/demo-1.json'; dest.parent.mkdir(parents=True)
        dest.write_bytes(b'old manifest')
        with self.assertRaises(ValueError): publish.server_publish(self.args)
        self.assertEqual(dest.read_bytes(), b'old manifest')

    def test_symlink_store_rejected(self):
        actual = self.root/'actual'; actual.mkdir()
        self.store.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(ValueError): publish.server_publish(self.args)


if __name__ == '__main__': unittest.main()
