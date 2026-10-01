"""Run only after outer approves this manifest and the 61b observation plan."""
import json,os,sys,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=Path(os.environ.get('WORKSPACES',R.parent))
sys.path.insert(0,str(R/'scripts/lab'))
import u7_executor as u
BUNDLE=W/'westlake-inputs/generations/n11g-u9-sealed-owner-v1/bundle'
BASE=W/'westlake-generation-u9-j10g-238ffc14/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sys.argv[1:]==['--outer-approved'], 'explicit outer approval required'
 summary=H/'package.json';old_summary=summary.read_bytes();old_bundle=(BUNDLE/'bundle.json').read_bytes()
 meta=json.loads(old_summary);assert meta['bundle_sha256']==sha(BUNDLE/'bundle.json')
 assert meta['native_manifest_sha256']==sha(BUNDLE/'native/package.json')
 # Strict native, image and frozen gates must pass before arming anything.
 u.preflight(BUNDLE,BASE,R/'scripts/lab/oatdump_remote.sh')
 try:
  b=json.loads(old_bundle);b['rollout_ready']=True;b['rollout_blocker']='outer-approved N11g <=30min observation only; unconditional U9 rollback'
  (BUNDLE/'bundle.json').write_text(json.dumps(b,indent=2)+'\n')
  meta['rollout_ready']=True;meta['bundle_sha256']=sha(BUNDLE/'bundle.json');summary.write_text(json.dumps(meta,indent=2)+'\n')
  result=u.preflight(BUNDLE,BASE,R/'scripts/lab/oatdump_remote.sh');assert result['deployable']
  # Omit absolute paths from the review receipt, never mutate gate output.
  text=json.dumps(result,indent=2).replace(str(W),'$WORKSPACES')
  (H/'approved-production-dry-run.json').write_text(text+'\n')
 except BaseException:
  (BUNDLE/'bundle.json').write_bytes(old_bundle);summary.write_bytes(old_summary);raise
 print('armed',meta['bundle_sha256'])
if __name__=='__main__':main()
