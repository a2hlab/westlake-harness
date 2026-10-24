#!/usr/bin/env python3
"""Offline tests for publish_once (extracted by AST from the reviewed file; the module itself is not imported/executed)."""
import ast, hashlib, json, multiprocessing as mp, os, sys, tempfile, threading, time, unittest, uuid
from pathlib import Path
from unittest import mock
SRC = Path(os.environ.get('PUBLISH_SRC', Path(__file__).resolve().parents[1]/'2026-10-24-existing-demo-reentry/recorder-fix/review_wait.py'))
def load():
    text = SRC.read_text(); tree = ast.parse(text)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'publish_once')
    ns = {'Path': Path, 'json': json, 'os': os, 'uuid': uuid}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SRC), 'exec'), ns)
    return ns['publish_once'], hashlib.sha256(text.encode()).hexdigest()
publish_once, SRC_SHA = load()
def temps(d): return sorted(p.name for p in Path(d).iterdir() if p.name.startswith('.'))
def _race(path, i, q):
    try: publish_once(path, {'writer': i, 'pad': 'x' * 20000}); q.put(('ok', i))
    except FileExistsError: q.put(('exists', i))
def _big_writer(path): publish_once(path, {'pad': ['y' * 1000] * 20000})
class T(unittest.TestCase):
    def setUp(self): self.td = tempfile.TemporaryDirectory(); self.d = Path(self.td.name); self.p = self.d/'r.json'
    def tearDown(self): self.td.cleanup()
    def test_new_target_complete_and_no_temp(self):
        publish_once(self.p, {'a': 1}); self.assertEqual(json.loads(self.p.read_text()), {'a': 1}); self.assertEqual(temps(self.d), [])
    def test_existing_regular_target_not_overwritten(self):
        self.p.write_text('ORIGINAL'); st = os.stat(self.p)
        with self.assertRaises(FileExistsError): publish_once(self.p, {'a': 2})
        self.assertEqual(self.p.read_text(), 'ORIGINAL'); self.assertEqual(os.stat(self.p).st_ino, st.st_ino); self.assertEqual(temps(self.d), [])
    def test_existing_symlink_target_not_followed_or_replaced(self):
        victim = self.d/'victim.json'; victim.write_text('V'); self.p.symlink_to(victim)
        with self.assertRaises(FileExistsError): publish_once(self.p, {'a': 3})
        self.assertTrue(self.p.is_symlink()); self.assertEqual(victim.read_text(), 'V'); self.assertEqual(temps(self.d), [])
    def test_dangling_symlink_target_not_replaced(self):
        self.p.symlink_to(self.d/'missing.json')
        with self.assertRaises(FileExistsError): publish_once(self.p, {'a': 4})
        self.assertTrue(self.p.is_symlink()); self.assertFalse((self.d/'missing.json').exists()); self.assertEqual(temps(self.d), [])
    def test_serialization_error_leaves_nothing(self):
        with self.assertRaises(TypeError): publish_once(self.p, {'bad': object()})
        self.assertFalse(self.p.exists()); self.assertEqual(temps(self.d), [])
    def test_link_unsupported_fails_closed_and_cleans(self):
        with mock.patch('os.link', side_effect=OSError(45, 'Operation not supported')):
            with self.assertRaises(OSError): publish_once(self.p, {'a': 5})
        self.assertFalse(self.p.exists()); self.assertEqual(temps(self.d), [])
    def test_interrupt_after_link_target_complete_temp_removed(self):
        real = os.link
        def link_then_interrupt(a, b, *k, **kw): real(a, b); raise KeyboardInterrupt
        with mock.patch('os.link', side_effect=link_then_interrupt):
            with self.assertRaises(KeyboardInterrupt): publish_once(self.p, {'a': 6})
        self.assertEqual(json.loads(self.p.read_text()), {'a': 6}); self.assertEqual(temps(self.d), [])
    def test_concurrent_processes_single_winner(self):
        q = mp.Queue(); ps = [mp.Process(target=_race, args=(str(self.p), i, q)) for i in range(16)]
        [p.start() for p in ps]; [p.join(30) for p in ps]; res = [q.get(timeout=5) for _ in ps]
        wins = [i for s, i in res if s == 'ok']; self.assertEqual(len(wins), 1); self.assertEqual(sum(s == 'exists' for s, _ in res), 15)
        self.assertEqual(json.loads(self.p.read_text())['writer'], wins[0]); self.assertEqual(temps(self.d), [])
    def test_reader_never_sees_partial_json(self):
        w = mp.Process(target=_big_writer, args=(str(self.p),)); w.start(); seen = 0; t_end = time.time() + 30
        while w.is_alive() or not self.p.exists():
            if self.p.exists():
                json.loads(self.p.read_text()); seen += 1
            if time.time() > t_end: break
        w.join(30); json.loads(self.p.read_text()); self.assertEqual(temps(self.d), [])
if __name__ == '__main__':
    print('reviewed source sha256', SRC_SHA); unittest.main(verbosity=2)
