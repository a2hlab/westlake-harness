#!/usr/bin/env python3
"""Publish small sanitized archive sidecars; original pending and failure stay immutable."""
import argparse,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates fresh archive sidecars.');return
 src=HERE/'.private/archive-01';attempt=HERE/'.private/upload-01';out=HERE/'archive';out.mkdir(exist_ok=False)
 def clean(s):
  s=s.replace(str(HERE),'$LANE/benchmark/2026-10-20-t21-window-evidence').replace(str(Path.home()),'$HOME')
  s=re.sub(r'/home/[^/ \n\"\']+', 'HW248_ARTIFACT_ROOT', s)
  return re.sub(r'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])','HW248_HOST',s)
 refs=[]
 for source,name in [(src/'receipt.json','pending.json'),(attempt/'receipt.json','lane-attempt.json')]+[(p,'lane-'+p.name+('.txt' if p.suffix=='.stderr' else '')) for p in sorted(attempt.glob('0.*'))]:
  data=source.read_bytes();q=out/name;q.write_text(clean(data.decode()));refs.append({'private_alias':str(source.relative_to(HERE)), 'sha256':sha(source),'bytes':len(data),'public_path':name,'public_sha256':sha(q)})
 m=src/'members.json';r=json.loads((src/'receipt.json').read_text());assert r['local_member_sha_verified'] and not r['remote_verified']
 (out/'source-index.json').write_text(json.dumps(refs,indent=2)+'\n')
 (out/'local-verification.json').write_text(json.dumps({'archive_sha256':r['archive_sha256'],'bytes':r['bytes'],'members':r['member_count'],'all_member_sha_size_verified':True,'members_index_sha256':sha(m),'private_archive':'.private/archive-01/window.tar.gz','exact_remote_argv':'.private/archive-01/remote-commands.private.json','remote_status':'PENDING_OUTER_EXECUTION','lane_first_ssh_rc':255},indent=2)+'\n')
if __name__=='__main__':main()
