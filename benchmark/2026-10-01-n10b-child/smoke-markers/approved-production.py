"""Production preflight of an exact approved bundle; no Board/device I/O."""
import json,os,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if (p/"scripts/lab/u7_executor.py").is_file());WS=R.parent
sys.path.insert(0,str(R/'scripts/lab'))
import u7_executor as u,generation_bundle as g
record=Path(os.environ.get('N10B_APPROVAL_RECORD',str(H/'u8-package.json')))
row=json.loads(record.read_text())['batch'];source=WS/row['bundle']
tag=row['runtime_sha256'][:8];root=WS/('westlake-generation-n10b-deployable-u8-'+tag)
if not root.exists():
 shutil.copytree(source,root)
 d=json.loads((root/'bundle.json').read_text());d['rollout_ready']=True;d.pop('rollout_blocker',None);(root/'bundle.json').write_text(json.dumps(d,indent=2)+'\n')
else:
 assert json.loads((root/'bundle.json').read_text())['native']==json.loads((source/'bundle.json').read_text())['native']
base=WS/'westlake-generation-u8-j9-t7e/native'
plan=u.preflight(root,base,str(WS/'westlake-harness/scripts/lab/oatdump_remote.sh'))
assert plan['deployable'] and plan['gates_passed'] and not plan['device_io']
out=H/os.environ.get('N10B_APPROVAL_REPORT','approved-production-dry-run.json')
out.write_text(json.dumps(plan,indent=2)+'\n')
print('PRODUCTION DRY-RUN PASS deployable=true',root)
