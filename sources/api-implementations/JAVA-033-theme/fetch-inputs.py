#!/usr/bin/env python3
"""Fetch the locked build inputs, or verify and unpack a supplied offline archive."""
import argparse, hashlib, json, os, shlex, subprocess, tarfile, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--archive-file',type=Path);a=p.parse_args()
 lock=json.loads((HERE/'dependencies.lock.json').read_text());out=a.out.resolve();assert not out.exists(),'fresh output required';out.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='verified-source-inputs-',dir=out.parent) as tmp:
  tmp=Path(tmp);archive=a.archive_file or tmp/lock['filename']
  if not a.archive_file:
   suffix=lock['remote_directory']+'/'+lock['filename'];remote=shlex.quote(os.environ['HW248_HOME']+'/'+suffix) if 'HW248_HOME' in os.environ else '"$HOME"/'+shlex.quote(suffix)
   with archive.open('wb') as stream:subprocess.run(['ssh','-o','BatchMode=yes',os.environ.get('HW248_HOST','hw248'),'cat -- '+remote],stdout=stream,check=True)
  assert archive.stat().st_size==lock['bytes'] and sha(archive)==lock['sha256'],'archive identity mismatch'
  dest=tmp/'inputs';dest.mkdir();expected={e['path']:e for e in lock['files']};seen=set()
  with tarfile.open(archive,'r:gz') as tar:
   for member in tar:
    assert member.isfile() and member.name in expected and member.name not in seen,'unexpected archive member'
    entry=expected[member.name];name=Path(member.name);assert not name.is_absolute() and '..' not in name.parts,'unsafe path'
    raw=tar.extractfile(member).read();assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256'],'member hash mismatch'
    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);seen.add(member.name)
  assert seen==set(expected),'missing archive member';dest.rename(out)
 print(json.dumps({'status':'PASS','files':len(seen),'archive_sha256':lock['sha256']}))
if __name__=='__main__':main()
