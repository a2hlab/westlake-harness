#!/usr/bin/env python3
"""Fetch and verify the original SHA-pinned J1/J7b binary compile inputs."""
import argparse,hashlib,json,os,shlex,subprocess,tarfile,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--archive-file',type=Path);a=ap.parse_args()
 lock=json.loads((HERE/'dependencies.lock.json').read_text());out=a.out.resolve();assert not out.exists(),'refuse existing output';out.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='frozen-jar-dependencies-',dir=out.parent) as tmp:
  tmp=Path(tmp);archive=a.archive_file or tmp/'inputs.tar.gz'
  if not a.archive_file:
   suffix=lock['remote_directory']+'/'+lock['filename'];remote=(shlex.quote(os.environ['HW248_HOME']+'/'+suffix) if 'HW248_HOME' in os.environ else '"$HOME"/'+shlex.quote(suffix))
   with archive.open('wb') as f:subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',os.environ.get('HW248_HOST','hw248'),'cat -- '+remote],stdout=f,check=True)
  assert archive.stat().st_size==lock['bytes'] and sha(archive)==lock['sha256'],'archive SHA/bytes mismatch'
  staging=tmp/'inputs';staging.mkdir();seen=set();expected={'inputs/'+x['name']:x for x in lock['files']}
  with tarfile.open(archive,'r:gz') as tar:
   for m in tar:
    if m.name not in expected:continue
    assert m.isfile() and m.name not in seen,'invalid duplicate/member'
    row=expected[m.name];data=tar.extractfile(m).read();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],m.name
    (staging/row['name']).write_bytes(data);seen.add(m.name)
  assert seen==set(expected),'missing members';staging.rename(out)
 print(json.dumps({'status':'PASS','dependency_files':len(seen),'archive_sha256':lock['sha256']}))
if __name__=='__main__':main()
