"""Copy only captured screenshots from the 128 authoritative per-key records."""
import hashlib,json,os,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;REPO=H.parents[1];WSP=Path(os.environ.get('WORKSPACES',REPO.parent));O=H/'delivery'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def resolve(s):return Path(s.replace('$WORKSPACES',str(WSP)).replace('$HOME',str(Path.home())))
def portable(p):return str(p).replace(str(WSP),'$WORKSPACES').replace(str(Path.home()),'$HOME')
rows=json.loads((O/'manifest.json').read_text())['rows'];index=[]
for row in rows:
 if row['scope']!='baseline128':continue
 rp=resolve(row['source_record']);assert sha(rp)==row['source_record_sha256'],row['key'];record=json.loads(rp.read_text());assert record['key']==row['key']
 for shot in record['screenshots']:
  if shot.get('captured') is not True:continue
  # Filename resolves relative to the bound record, independent of historical user path strings.
  src=rp.parent/Path(shot['path']).name;assert src.exists(),src
  assert sha(src)==shot['sha256'],src
  dest=O/'raw-baseline-screenshots'/row['key']/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
  index.append(dict(key=row['key'],image=str(dest.relative_to(O)),sha256=sha(src),bytes=src.stat().st_size,source_image=portable(src),source_relative_to_round=str(src).split('/identity128/round/')[1],source_record=row['source_record'],source_record_sha256=sha(rp),captured=True,scheduled_seconds=shot.get('scheduled_seconds'),elapsed_seconds=shot.get('elapsed_seconds'),raw_status=record.get('status')))
assert len(index)==256 and len({r['key'] for r in index})==128 and len({r['image'] for r in index})==256
(O/'raw-baseline-index.json').write_text(json.dumps(dict(baseline_keys=128,captured_screenshots=256,facts_total_verbatim=(H/'evidence/facts.txt').read_text().strip().splitlines()[-1],not_new_captures=True,selection='Only captured=true screenshots from the 128 bound authoritative record.json files; no montage, smoke or logs.',screenshots=index),ensure_ascii=False,indent=2))
print('Copied 256 captured original screenshots from 128 authoritative records; all recorded SHAs match')
