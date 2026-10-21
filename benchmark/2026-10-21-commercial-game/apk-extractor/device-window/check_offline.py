#!/usr/bin/env python3
"""Offline negative tests: no subprocess/device/build operations."""
import copy
import datetime
import json
from pathlib import Path
import unittest
from test_transaction import Transactions
from policy import Refuse,guard,maps_snapshot,check_coverage

HERE=Path(__file__).resolve().parent
class Gates(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads((HERE/'plan.disabled.json').read_text())
        self.cfg['bindings'].update(holder='outer 42 2026-10-21T17:00:00+08:00',lane='outer')
        self.now=datetime.datetime.fromisoformat('2026-10-21T17:01:00+08:00').timestamp()
    def test_exact_guard(self):
        self.assertEqual(guard(self.cfg,self.cfg['bindings']['holder'],self.cfg['expected_boot'],self.now),60)
    def test_boot_holder_budget_refuse(self):
        for held,boot,now,new in [(self.cfg['bindings']['holder'],'oldboot',self.now,False),('outer 43 2026-10-21T17:00:00+08:00',self.cfg['expected_boot'],self.now,False),(self.cfg['bindings']['holder'],self.cfg['expected_boot'],self.now+1800,False),(self.cfg['bindings']['holder'],self.cfg['expected_boot'],self.now+1200,True)]:
            with self.subTest(held=held,boot=boot,now=now),self.assertRaises(Refuse):guard(self.cfg,held,boot,now,new)
    def test_unknown_maps_never_empty(self):
        for text in ['', 'PROC_COUNT=0\n','BEGIN_PROC /proc/3\nMAPS_RC=1\nEND_PROC /proc/3\nPROC_COUNT=1\n']:
            with self.subTest(text=text),self.assertRaises(Refuse):maps_snapshot(text)
    def test_raw_complete_snapshot_and_faults(self):
        raw=Path.home()/'.local/share/westlake/commercial-game-20261021/apk-extractor/fresh-next-01'
        if not raw.is_dir():self.skipTest('private outer snapshot unavailable')
        text=(raw/'all-process-maps.stdout').read_text();snap=maps_snapshot(text)
        self.assertEqual(snap['count'],345);self.assertEqual(snap['hits'],[])
        self.assertTrue(check_coverage(snap,(raw/'processes-before.stdout').read_text(),(raw/'processes-after.stdout').read_text()))
        with self.assertRaises(Refuse):maps_snapshot(text.replace('MAPS_RC=0','MAPS_RC=1',1))
        with self.assertRaises(Refuse):check_coverage(snap,(raw/'processes-before.stdout').read_text()+'\n99999 1 3060 installs\n',(raw/'processes-after.stdout').read_text())
    def test_disabled_no_broad_restart(self):
        self.assertIs(self.cfg['execution_enabled'],False);self.assertEqual(self.cfg['default_service_actions'],[])
        text=(HERE/'window_impl.py').read_text()
        self.assertNotIn('stop_service foundation',text);self.assertNotIn('tr "',text)
        self.assertIn('od -An -v -tx1',text);self.assertIn("'--git',str(repo)",text)

if __name__=='__main__':unittest.main()
