import hashlib,json,sys,tarfile
from pathlib import PurePosixPath
archive,expected,size,members_sha,count=sys.argv[1:]
def digest(stream):
 h=hashlib.sha256()
 for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
with open(archive,'rb') as f:assert digest(f)==expected
import os
assert os.stat(archive).st_size==int(size)
with tarfile.open(archive,'r:gz') as t:
 entries=t.getmembers();assert len(entries)==int(count)
 assert all(e.isfile() and not PurePosixPath(e.name).is_absolute() and '..' not in PurePosixPath(e.name).parts for e in entries)
 assert len({e.name for e in entries})==len(entries)
 data=t.extractfile('archive/members.json').read();assert hashlib.sha256(data).hexdigest()==members_sha
 manifest=json.loads(data)['files'];pins={r['path']:r for r in manifest};assert len(pins)==len(manifest)
 assert set(e.name for e in entries)==set(pins)|{'archive/members.json'}
 for e in entries:
  if e.name=='archive/members.json':continue
  row=pins[e.name];assert e.size==row['bytes'],e.name
  assert digest(t.extractfile(e))==row['sha256'],e.name
print(json.dumps({'status':'ARCHIVE_AND_ALL_MEMBERS_VERIFIED','sha256':expected,'bytes':int(size),'members':len(entries),'data_members':len(manifest),'member_manifest_sha256':members_sha}))
