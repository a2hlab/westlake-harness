#!/usr/bin/env python3
"""Create a read-only evidence view; interrupted fitness is superseded, never deleted."""
import importlib.util,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
serial='61b0657200000000000000000324012c'
runs=[R/'runs'/n/serial for n in ('installer-r17p-61b','installer-r17p-61b-resume')]
assert (runs[0]/'runtime-fingerprint.txt').read_bytes()==(runs[1]/'runtime-fingerprint.txt').read_bytes()
out=R/'combined';out.mkdir(exist_ok=False)
selection={}
for key in (R/'keys.txt').read_text().strip().split(','):
    candidates=[r/key for r in runs if (r/key/'record.json').exists()]
    src=candidates[-1]
    record=json.loads((src/'record.json').read_text())
    assert record['status']!='batch_interrupted',key
    (out/key).symlink_to(src,target_is_directory=True);selection[key]=str(src)
for name in ('runtime-fingerprint.txt','preflight.json'):shutil.copy2(runs[1]/name,out/name)
(out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('master_batch',Path('/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
print(b.write_facts(out))
