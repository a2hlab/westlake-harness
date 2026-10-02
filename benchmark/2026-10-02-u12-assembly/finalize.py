#!/usr/bin/env python3
"""Archive exact raw evidence outside git and create portable public report copies."""
import hashlib,json,shutil,re
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 c=json.loads((H/'composition.json').read_text());archive=W/'westlake-inputs/generations/u12-assembly-evidence-6d908fd9-v3'
 assert not archive.exists(),'fresh evidence archive required'
 archive.mkdir(parents=True);records=[];previous={r['public']:r for r in json.loads((H/'raw-evidence.json').read_text())} if (H/'raw-evidence.json').exists() else {}
 for p in sorted(H.rglob('*')):
  if not p.is_file() or '__pycache__' in p.parts or (p.suffix not in ['.txt','.json'] and p.name!='executor'):continue
  if p.name in ['raw-evidence.json','results.json','landing-paths.txt','preflight.txt']:continue
  rel=p.relative_to(H)
  if str(rel) in previous and previous[str(rel)]['public_sha256']==sha(p):records.append(previous[str(rel)]);continue
  dst=archive/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
  text=p.read_text();portable=text.replace(str(W),'$WORKSPACES').replace(str(Path.home()),'$MAC_HOME');portable=re.sub(r'/home/[^/\s"\']+','$VM_HOME',portable);p.write_text(portable)
  records.append({'public':str(rel),'raw_path':str(dst).replace(str(W),'$WORKSPACES'),'raw_sha256':sha(dst),'public_sha256':sha(p),'normalization':'workspace/home prefixes only; raw original retained'})
 (H/'raw-evidence.json').write_text(json.dumps(records,indent=2)+'\n')
 summaries={s:json.loads((H/'gates'/s/'summary.json').read_text()) for s in ['mac','vm']};classification=json.loads((H/'exception-classification.json').read_text());plans=json.loads((H/'plan-summary.json').read_text())
 result={'status':'DRAFT_COMPLETE_EXECUTION_DISABLED','native_manifest_sha256':c['native_manifest_sha256'],'bundle_sha256':c['bundle_sha256'],'package':c['package'],'base':'U10.1T8','rollout_ready':False,'execution_enabled':False,'device_access':False,'locks_taken':0,'exception_registry_written':False,'native_gate_classification':classification,'surfaces':summaries,'plans':plans,'restore_identity_assertions':318,'native_path_changes':4,'native_root_additions':1,'pending':c['pending']+['new native member production-static admission','final reviewed apply/finish hook and smoke binding'],'honesty':'Mac+VM production dry-run refuse rc2; no candidate board verdict or lighting gain is claimed','late_other_lane_delivery':'Java/stubs rebake reported at19:26 but not incorporated; N11h-r2 reported blocked for source/idempotence prerequisite. Both remain pending final composition.'}
 (H/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'native_manifest_sha256':c['native_manifest_sha256'],'bundle_sha256':c['bundle_sha256'],'auto_identical':classification['identical'],'genuinely_new':classification['genuinely_new'],'N2_all_103_identical':classification['N2_all_103_identical'],'production_rc':{s:d['production_dry_run_exit_code'] for s,d in summaries.items()},'keys':plans['keys'],'restore':'U10.1T8 318','execution_enabled':False},indent=2))
if __name__=='__main__':main()
