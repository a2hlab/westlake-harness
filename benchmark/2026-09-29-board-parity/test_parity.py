import tempfile
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess
import collect
import summarize

class ParityTests(unittest.TestCase):
    def test_inode_mismatch_cannot_verify_path_hash(self):
        row = {'inode': 100, 'device': '08:01', 'deleted': False}
        stat = {'device': 2049, 'inode': 101}
        self.assertEqual(collect.classify(row, None, None, stat, 'a'*64, True)['identity'], 'unverified')
        stat['inode'] = 100
        self.assertEqual(collect.classify(row, None, None, stat, 'a'*64, True)['identity'], 'process_root_inode_matched')
        self.assertEqual(collect.classify(row, stat, 'b'*64, stat, 'a'*64, True)['sha256'], 'b'*64)
        self.assertIsNone(collect.classify(row, stat, 'b'*64, stat, 'a'*64, False)['sha256'])
        row['deleted'] = True
        self.assertIsNone(collect.classify(row, None, None, stat, 'a'*64, True)['sha256'])

    def test_connect_failure_even_with_zero_exit(self):
        with tempfile.TemporaryDirectory() as temp, patch('collect.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', 'Connect server failed\n')):
            reader = collect.Reader('hdc', collect.SERIALS[0], Path(temp)/'board')
            result = reader.collect()
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['files'], {})
            self.assertEqual(len(reader.commands), 1)

    def test_maps_include_bind_source_and_no_truncation(self):
        lines = '123-456 r-xp 0000 08:01 100 /data/local/tmp/liboh_adapter_bridge.so\n789-abc r--p 0000 08:01 101 /system/android/framework/test.jar (deleted)\n'
        rows = collect.maps_rows(lines, {'liboh_adapter_bridge.so'})
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[1]['deleted'])
        self.assertEqual(rows[0]['path'], '/data/local/tmp/liboh_adapter_bridge.so')

    def test_missing_read_is_not_equality_or_confirmed_absence(self):
        path = '/system/android/lib64/x.so'
        boards = [{'serial': s, 'status': 'captured', 'files': {path: 'a'*64},
                   'trees': [{'root': '/system/android/lib64', 'complete': True}]} for s in collect.SERIALS]
        def verdict():
            return next(r['verdict'] for r in summarize.compare(boards) if r['path'] == path)
        self.assertEqual(verdict(), 'equal')
        boards[2]['files'] = {}
        self.assertEqual(verdict(), 'different')
        boards[2]['status'] = 'blocked'
        self.assertEqual(verdict(), 'incomplete')

    def test_inherited_ps_name_does_not_hide_hello_child(self):
        maps = '100-200 r--s 0 103:30 12 /data/app/el1/bundle/public/com.example.helloworld/android/base.apk'
        self.assertEqual(summarize.derive_role('com.example.hel', maps, 90, {90}), 'helloworld')
        self.assertIsNone(summarize.derive_role('com.example.hel', maps, 91, {90}))
        self.assertNotEqual(summarize.derive_role('com.example.hel', '', 90, {90}), 'helloworld')
        self.assertNotEqual(summarize.derive_role('unrelated', maps, 90, {90}), 'helloworld')

    def test_1446_receipts_reconcile_with_inventory_and_roles(self):
        root = Path(__file__).resolve().parent / 'evidence/collection-20260929T1446'
        path = root / 'collection.json'
        data = json.loads(path.read_text())
        for board in data['boards']:
            files = {}
            for name in ['tree-0', 'tree-1', 'tree-2', 'tree-3', 'single-files']:
                receipt = json.loads((root / board['serial'][:8] / (name+'.json')).read_text())
                self.assertTrue(receipt['transport_ok'])
                files.update(collect.hashes(receipt['stdout']))
            self.assertEqual(files, board['files'])
            self.assertEqual(len(files), 158)
            for proc in board['processes']:
                for f in proc['files']:
                    actual = collect.classify(f, f['mapped_stat'], f['mapped_sha256'], f['root_stat'], f['root_sha256'], proc['stable_process'] and proc['stable_maps'])
                    self.assertEqual(actual['identity'], f['identity'])
                    self.assertEqual(actual['sha256'], f['sha256'])
        rows = summarize.compare(data['boards'])
        self.assertEqual(sum(r['verdict'] == 'equal' for r in rows), 153)
        self.assertEqual(sum(r['verdict'] == 'different' for r in rows), 5)
        summarize.resolve_roles(data['boards'], path)
        hello = [(b['serial'][:8], p['pid']) for b in data['boards'] for p in b['processes'] if p['role'] == 'helloworld']
        self.assertEqual(hello, [('5ea34a45', 29584), ('61b06572', 14337)])
        self.assertTrue(all(summarize.disk_complete(b) for b in data['boards']))

    def test_boot_or_process_identity_not_fabricated(self):
        self.assertFalse(collect.UUID.fullmatch('Connect server failed'))
        text = '123 (a b) S ' + ' '.join(str(i) for i in range(4, 53))
        self.assertEqual(collect.start_time(text), '22')
        self.assertIsNone(collect.start_time(''))
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                collect.Reader('hdc', 'not-allowed', Path(temp)/'board')

if __name__ == '__main__':
    unittest.main()
