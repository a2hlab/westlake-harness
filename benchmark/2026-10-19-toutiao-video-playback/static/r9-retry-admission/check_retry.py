#!/usr/bin/env python3
"""Pure source extraction: never import executor/Board or execute emitted shell."""
import ast,hashlib,json,sys
from pathlib import Path
main=Path(sys.argv[1]); base=Path(sys.argv[2]); out=Path(__file__).resolve().parent
rel='benchmark/2026-10-19-toutiao-video-playback/candidate-r9/video_guarded_window_r9.py'
s=(main/rel).read_text(); tree=ast.parse(s); sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(s.encode())=='ffa3969a4752ed84f2b4293b35bc5cdaa145a39028d6d1d5ea76ce2e97de6e4a'
old=json.loads((base/'video-r9-apply/plan.json').read_text())
boot='4117236f-c834-4f70-82fd-c39929d76573'
from types import SimpleNamespace
const={}
for n in tree.body:
 if isinstance(n,ast.Assign):
  try:v=ast.literal_eval(n.value)
  except (ValueError,TypeError):continue
  for t in n.targets:
   if isinstance(t,ast.Name):const[t.id]=v
# Evaluate only actual filename assignment expressions, with synthetic host output paths.
def assigned(name,mode,tag):
 env=dict(const,sha=sha,a=SimpleNamespace(boot=boot,mode=mode,out=Path(tag)),apply_plan=old)
 found=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets):
   if name in ('backup','media_backup','player_backup') and 'apply_plan' in ast.unparse(n.value):continue
   found.append(eval(compile(ast.Expression(n.value),'actual-name-expression','eval'),env))
 assert len(found)==1,(name,found)
 return found[0]
new={k:assigned(k,'apply','retry-a/apply') for k in ('backup','media_backup','player_backup')}
prior={k:old['runtime']+'/'+n+'.ttvideo-before-'+old['boot'][:8] for k,n in [('backup','run.sh'),('media_backup',const['MEDIA']),('player_backup',const['PLAYER'])]}
assert set(new.values()).isdisjoint(prior.values())
assert new=={k:assigned(k,'apply','retry-b/apply') for k in new},'backup must remain boot-only'
assert assigned('stage','apply','retry-a/apply')!=assigned('stage','apply','retry-b/apply')
assert assigned('stage','apply','retry-a/apply')!=assigned('stage','rollback','retry-a/apply')
assert 'a.out.mkdir(parents=True,exist_ok=False)' in s
assert "test ! -e {q(backup)}" in s and "test ! -e {q(media_backup)}" in s and "test ! -e {q(player_backup)}" in s
assert "backup=RT+'/run.sh.ttvideo-before-'+apply_plan['boot'][:8]" in s
assert "origin_apply_plan_sha256" in s
assert "VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED" in s
r={'status':'PASS_OFFLINE_NAMING_ONLY','source_sha256':sha(s.encode()),'old_apply_plan_sha256':sha((base/'video-r9-apply/plan.json').read_bytes()),'retry_boot':boot,'old_backup_paths':prior,'retry_backup_paths':new,'checks':['different boot prefixes isolate all three backups','changing tag alone does not change backups','different output paths isolate stage','apply and rollback stage modes differ','host out refuses reuse','all three existing backups refuse overwrite','rollback selects its bound original apply boot','fresh reboot marker retained'],'device_calls':0,'runtime_execution':False,'limitations':['No assertion of current remote backup absence; original apply tests it before swap.','No attempt counter or global 20/30-minute timer in executor; outer must enforce.']}
(out/'checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
