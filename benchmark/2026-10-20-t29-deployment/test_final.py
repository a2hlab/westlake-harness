#!/usr/bin/env python3
"""Final data cross-links and deliberate drift; no device or transaction calls."""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('t29_final',P/'check_final.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
local=P.parents[1]
ROOT=Path(os.environ.get('T29_SOURCE_ROOT',str(local)))
if not (ROOT/'benchmark/2026-10-20-t29-production-peer').exists():ROOT=local.parent/'westlake-harness'
class Final(unittest.TestCase):
    def test_actual_refs(self):
        self.assertGreater(len(check.validate(P,[ROOT])),15)
    def test_drift_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in ('bridge-sha','shim-export','owner-slot','approval','fixed-four'):
                root=Path(tmp)/case;shutil.copytree(P,root,ignore=shutil.ignore_patterns('__pycache__'))
                name={'bridge-sha':'bridge-candidate.json','shim-export':'three-slot-admission.json',
                      'owner-slot':'bridge-binding-pending.json','approval':'admission.template.json','fixed-four':'parameters.json'}[case]
                x=check.load(root/name)
                if case=='bridge-sha':x['after_sha256']='f'*64
                if case=='shim-export':x['slots'][0]['candidate_export_offset']='0xd7e4'
                if case=='owner-slot':x['owner_slots']['OH_NativeWindow_NativeObjectReference']='0x1740a0'
                if case=='approval':x['approved_by']='outer(codex)'
                if case=='fixed-four':x['artifacts'][0]['after_sha256']='f'*64
                check.save(root/name,x)
                ad=check.load(root/'admission.template.json')
                for k,f in check.SELF_PINS.items():ad[k]=check.sha(root/f)
                check.save(root/'admission.template.json',ad)
                with self.subTest(case=case),self.assertRaises(AssertionError):check.validate(root,[ROOT])
if __name__=='__main__':unittest.main()
