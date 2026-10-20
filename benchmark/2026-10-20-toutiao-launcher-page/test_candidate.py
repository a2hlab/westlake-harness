#!/usr/bin/env python3
"""Offline exact member/refusal tests; invokes no device or signer."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('package_sign',HERE/'package_sign.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
LOCK=json.loads((HERE/'inputs.lock.json').read_text())

class ClosureTests(unittest.TestCase):
    def test_source_closure(self):
        for n,h in LOCK['sources'].items():self.assertEqual(m.sha(HERE/n),h,n)
        old=(HERE/'sources/baseline/Index.js').read_text()
        new=(HERE/'sources/candidate/Index.js').read_text()
        start=old.index('        this.observeComponentCreation2(() => {\n            Text.create(')
        end=old.index('        Column.pop();',start)
        self.assertEqual(new,old[:start]+old[end:])
        self.assertNotIn('TextInput.create',new)
        self.assertIn("Column.backgroundColor('#fff4f6f8')",new)
    def test_public_receipt_closure(self):
        r=json.loads((HERE/'production-01.json').read_text())
        self.assertEqual(r['status'],'OFFLINE_SIGNED_CANDIDATE_VERIFIED_NOT_DEPLOYED')
        self.assertEqual(r['changed_members'],[m.INDEX])
        self.assertEqual(len(r['unchanged_members']),8)
        self.assertEqual(r['artifacts']['rollback-exact.hap']['sha256'],LOCK['original_hap']['sha256'])
        for a,b in [('original.cer','candidate.cer'),('original.p7b','candidate.p7b')]:self.assertEqual(r['artifacts'][a],r['artifacts'][b])
        self.assertEqual([x['rc'] for x in r['commands']],[0,0,0,0])
        self.assertFalse(r['deployment_accepted'])

class RefusalTests(unittest.TestCase):
    def setUp(self):
        self.old={k:k.encode() for k in LOCK['original_hap']['members']}
        self.new=copy.deepcopy(self.old);self.new[m.INDEX]=b'new-abc'
    def test_only_index_allowed(self):self.assertEqual(m.compare(self.old,self.new,b'new-abc',False),[m.INDEX])
    def test_resource_rejected(self):
        self.new['resources.index']=b'wrong'
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_PAYLOAD_CHANGE'):m.compare(self.old,self.new,b'new-abc',True)
    def test_entry_rejected(self):
        self.new['ets/entryability/EntryAbility.abc']=b'wrong'
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_PAYLOAD_CHANGE'):m.compare(self.old,self.new,b'new-abc',True)
    def test_module_rejected(self):
        self.new['module.json']=b'wrong'
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_PAYLOAD_CHANGE'):m.compare(self.old,self.new,b'new-abc',True)
    def test_missing_extra(self):
        for kind in ['missing','extra']:
            with self.subTest(kind=kind):
                n=dict(self.new)
                if kind=='missing':n.pop('resources.index')
                else:n['unexpected']=b'x'
                with self.assertRaisesRegex(ValueError,'MEMBER_SET'):m.compare(self.old,n,b'new-abc',True)
    def test_wrong_candidate(self):
        with self.assertRaisesRegex(ValueError,'CANDIDATE_INDEX'):m.compare(self.old,self.new,b'other',True)
    def test_meta_only_signed(self):
        self.new[m.META]=b'new-metadata'
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_PAYLOAD_CHANGE'):m.compare(self.old,self.new,b'new-abc',False)
        self.assertEqual(set(m.compare(self.old,self.new,b'new-abc',True)),{m.INDEX,m.META})
    def test_no_program_change_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_PAYLOAD_CHANGE'):m.compare(self.old,self.old,self.old[m.INDEX],True)
    def test_original_sha_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.hap';p.write_bytes(b'not exact old hap')
            with self.assertRaisesRegex(ValueError,'HAP_SHA'):m.original(p,LOCK)
    def test_source_receipt_drift(self):
        r={'status':'EXACT_BASELINE_AND_CANDIDATE_COMPILED','compiler':{'sha256':LOCK['compiler_sha256']},'source_pins':{}}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'receipt.json').write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'COMPILE_SOURCE_PINS'):m.compiled(p,LOCK,HERE)

if __name__=='__main__':unittest.main()
