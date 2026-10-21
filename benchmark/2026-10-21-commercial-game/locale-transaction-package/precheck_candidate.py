#!/usr/bin/env python3
"""Read and hash a completed G30 receipt. Never assembles or accepts a candidate."""
import argparse,json
from pathlib import Path
from inspect_inputs import sha,save
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--workspaces',type=Path,required=True);a=p.parse_args();w=a.workspaces.resolve();r=w/'westlake-harness-t4/benchmark/2026-10-21-commercial-game/locale-abi-candidate/.private/candidate-01/receipt.json';d=json.loads(r.read_text());rows=[]
def alias(p):return str(p).replace(str(w),'$WORKSPACES').replace(str(Path.home()),'$HOME')
for n,v in d['inputs'].items():
 f=Path(n);assert sha(f)==v['sha256'] and f.stat().st_size==v['bytes'];rows.append({'path':alias(f),**v})
for n,v in d['outputs'].items():
 f=r.parent/n;assert sha(f)==v['sha256'] and f.stat().st_size==v['bytes'];rows.append({'path':alias(f),**v})
assert all(c['rc']==0 for c in d['commands'])
h=d['outputs']['libwestlake_native_abi.so']['sha256'];assert h=='4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b'
save(D/'candidate-precheck.json',{'status':'READ_ONLY_PRECHECK_NOT_ACCEPTED','candidate_assembled':False,'candidate_sha256':h,'bytes':41984,'receipt':{'path':alias(r),'sha256':sha(r),'bytes':r.stat().st_size},'inputs_hashed':len(d['inputs']),'outputs_hashed':len(d['outputs']),'commands':d['commands'],'old_objects_byte_identical_reported':d['old_objects_byte_identical'],'outer_final_acceptance':False,'pins':rows})
print(json.dumps({'status':'READ_ONLY_PRECHECK','inputs':len(d['inputs']),'outputs':len(d['outputs']),'candidate_assembled':False}))
