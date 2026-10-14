#!/usr/bin/env python3
"""Fetch five SHA-pinned compile dependencies; implementation sources stay in Git."""
import argparse,hashlib,json,shlex,subprocess,tarfile,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--archive-file',type=Path,help='Use an already downloaded bundle; skip SSH');a=ap.parse_args()
 pin=json.loads((HERE/'dependency-bundle.lock.json').read_text());lock=json.loads((HERE/'dependencies.lock.json').read_text());out=a.out.resolve();assert not out.exists(),'refuse existing output';out.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='tagsoup-dependencies-',dir=out.parent) as temp:
  archive=a.archive_file or Path(temp)/'bundle.tar.gz'
  if not a.archive_file:
   host,path=pin['archive'].split(':',1);assert host=='hw248'
   with archive.open('wb') as f:subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'cat -- '+shlex.quote(path)],stdout=f,check=True)
  assert archive.stat().st_size==pin['bytes'] and sha(archive)==pin['sha256'],'bundle SHA/size mismatch'
  expected={pin['dependencies_archive_prefix']+d['path'].removeprefix('$A2HLAB_WS/'):d for d in lock['t7d_classpath']+[lock['r8']]};seen=set();staging=Path(temp)/'deps';staging.mkdir()
  with tarfile.open(archive,'r:gz') as t:
   for member in t:
    if member.name not in expected:continue
    assert member.isfile() and member.name not in seen
    row=expected[member.name];data=t.extractfile(member).read();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    dest=staging/row['path'].removeprefix('$A2HLAB_WS/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);seen.add(member.name)
  assert seen==set(expected),'missing dependency members';staging.rename(out)
 print(json.dumps({'status':'PASS','dependency_files':len(seen),'archive_sha256':pin['sha256']}))
if __name__=='__main__':main()
