#!/usr/bin/env python3
"""Append exact outer transfer evidence; never repack or rewrite pending receipts."""
import argparse, hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args()
 if not a.write: print('Read-only default; --write creates a new outer-success sidecar.');return
 src=Path.home()/'.local/share/westlake/t18-production/source-closure-outer-success'
 expected=json.loads((HERE/'.private/archive-02/remote-commands.private.json').read_text())
 old=json.loads((HERE/'manifest.json').read_text())
 for r in old['files']: assert sha(ROOT/r['path'])==r['sha256']
 pending=HERE/'packet-final/archive-receipt.json';r=json.loads(pending.read_text())
 for i in range(3):
  assert json.loads((src/f'{i}.argv.json').read_text())==expected[i]
  assert (src/f'{i}.rc').read_text().strip()=='0'
 lines=(src/'2.stdout').read_text().splitlines()
 assert lines[0].split()[0]==r['archive_sha256'] and int(lines[1])==r['bytes']
 out=HERE/'outer-success';out.mkdir(exist_ok=False)
 remote=expected[2][-1].split()[1].rsplit('/',2)[0]
 def clean(s): return s.replace(remote,'HW248_ARTIFACT_ROOT').replace(str(ROOT),'$WORKSPACES/westlake-harness-t4').replace(str(Path.home()),'$HOME')
 def dump(n,x): (out/n).write_text(json.dumps(x,indent=2)+'\n')
 index=[]
 for f in sorted(src.iterdir()):
  if not f.is_file():continue
  dest=out/(f.name+'.txt' if f.suffix in ('.stdout','.stderr') else f.name)
  data=f.read_bytes();dest.write_text(clean(data.decode()))
  index.append(dict(raw_path='$HOME/.local/share/westlake/t18-production/source-closure-outer-success/'+f.name,raw_sha256=sha(f),raw_bytes=len(data),public_path=str(dest.relative_to(ROOT)),public_sha256=sha(dest),byte_exact=data==dest.read_bytes()))
 (out/'prior-manifest.json').write_bytes((HERE/'manifest.json').read_bytes())
 dump('source-index.json',index)
 dump('verification.json',dict(token='t18-source-closure-remote-closed',status='OUTER_REMOTE_VERIFIED',argv_equal_prepared=True,rc=[0,0,0],archive_sha256=r['archive_sha256'],bytes=r['bytes'],member_count=r['member_count'],remote_sha_size_match=True,historical_pending_receipt_sha256=sha(pending),prior_manifest_sha256=sha(HERE/'manifest.json'),archive_repacked=False,device_calls=0,source_snapshot_commit='286c1e520',source_snapshot_commit_basis='outer delivery receipt; not a historical build claim',mc46_original_final_logs='UNKNOWN_NOT_FOUND'))
 (out/'ACK.md').write_text('ACK t18-source-closure-remote-closed\n\nAll three original outer argv match the prepared commands and returned 0. Remote SHA and size match archive-02. The original pending receipt and previous payload remain unchanged. No repack or build was performed. The original final mc46 full build logs remain unknown.\n')
 print(json.dumps(dict(status='OUTER_REMOTE_VERIFIED',prior_payload_unchanged=len(old['files']),new_sidecars=len(list(out.iterdir())))))
if __name__=='__main__':main()
