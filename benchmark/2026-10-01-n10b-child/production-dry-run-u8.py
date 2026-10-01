"""Run real image/provenance checks; record strict native rejection without approval."""
import json,os,sys,contextlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as g,u7_executor as u
row=json.loads((H/'u8-package.json').read_text())['batch'];root=R.parent/row['bundle'];base=R.parent/'westlake-generation-u8-j9-t7e/native';oatdump=str(R.parent/'westlake-harness/scripts/lab/oatdump_remote.sh')
plan=u.prepare(root,base);image=g.image_checks(root,oatdump)
try:
 with (H/'batch-u8-production-preflight.log').open('w') as output, contextlib.redirect_stdout(output):
  checked=u.preflight(root,base,oatdump)
 result={'production_preflight':'passed','plan':checked}
except RuntimeError as e:
 result={'production_preflight':'refused','reason':str(e),'plan':plan}
result.update(device_io=False,image_gates=image,deployable=False)
(H/'batch-u8-production-dry-run.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['production_preflight','reason','device_io','deployable']},indent=2))

assert image['G1'] and image['G2'], image
assert plan['build_receipt']['status']=='verified-with-exception'
assert not plan['rollout_ready']
assert result['production_preflight']=='refused'
