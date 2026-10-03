"""Preserve the zero-record rejected61b window; never replace it with retry evidence."""
from pathlib import Path
import json,hashlib,shutil,re
H=Path(__file__).resolve().parent;W=H.parents[3];d=H.parent/'window4-61b'
p=json.loads((d/'plan-61b.json').read_text());root=Path(p['out'].replace('$WORKSPACES',str(W))).parent
dest=H/'evidence/61b-original-rejected';rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src):
 rel=src.relative_to(root);out=dest/rel;out.parent.mkdir(parents=True,exist_ok=True)
 if src.suffix in {'.jpeg','.png'}:shutil.copyfile(src,out)
 else:
  s=src.read_text(errors='replace').replace(str(W),'$WORKSPACES').replace(str(Path.home()),'$MAC_HOME');s=re.sub(r'/home/[^/\s\"\']+', '$VM_HOME',s);out.write_text(s)
 rows.append({'file':str(out.relative_to(H)),'raw_sha256':sha(src),'public_sha256':sha(out)})
for pat in ['baseline/*.json','post-apply/*.json','final-*/*.json','restored-*/*.json','finish.json','runner/board-run-result.json','runner/smoke/smoke-result.json','runner/0-*.log','recovery-smoke-*/smoke-result.json','runner/smoke/*/*/*/*/record.json','runner/smoke/*/*/*/*/t20.jpeg','recovery-smoke-*/*/*/*/*/record.json','recovery-smoke-*/*/*/*/*/t20.jpeg']:
 for src in root.glob(pat):
  if src.is_file() and src.stat().st_size<1000000:copy(src)
(H/'rejected-window-index.json').write_text(json.dumps({'regular_app_records':len(list((root/'runner').glob('0-*/*/*/*/record.json'))),'cause':'unknown or duplicate requested key: outer comment token see; zero app attempts','raw_archive':'$WORKSPACES/westlake-inputs/generations/u13-stageA-window4-20261003/window4-61b','files':rows},indent=2)+'\n')
print('Rejected61b preserved',len(rows),'files; regular app records=0')
