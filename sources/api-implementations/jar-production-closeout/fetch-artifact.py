#!/usr/bin/env python3
"""Fetch one durable archive and reject size/SHA drift before publishing a local file."""
import argparse,hashlib,json,os,shlex,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--kind',choices=['toolchain','evidence'],required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--archive-file',type=Path);a=ap.parse_args()
 receipt=json.loads((REPO/'benchmark/2026-10-14-verified-source-closeout/jar/archive.json').read_text());name='java-image.tar.gz' if a.kind=='toolchain' else 'jar-evidence.tar.gz';r=next(x for x in receipt['files'] if x['filename']==name)
 out=a.out.resolve();assert not out.exists(),'refuse existing output';out.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='locked-jar-archive-',dir=out.parent) as d:
  tmp=Path(d)/name
  if a.archive_file:tmp.write_bytes(a.archive_file.read_bytes())
  else:
   remote='"$HOME"/'+shlex.quote(receipt['remote_directory']+'/'+name)
   with tmp.open('wb') as f:subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',os.environ.get('HW248_HOST','hw248'),'cat -- '+remote],stdout=f,check=True)
  assert tmp.stat().st_size==r['bytes'] and digest(tmp)==r['sha256'],'archive SHA/bytes mismatch'
  tmp.rename(out)
 print(json.dumps({'filename':name,'sha256':r['sha256'],'bytes':r['bytes'],'verified':True}))
if __name__=='__main__':main()
