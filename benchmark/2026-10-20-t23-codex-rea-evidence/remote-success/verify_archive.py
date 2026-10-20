import hashlib,json,sys,tarfile
from pathlib import Path
p=Path(sys.argv[1]); expected=sys.argv[2];size=int(sys.argv[3]);mh=sys.argv[4]
assert p.stat().st_size==size
assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
with tarfile.open(p,"r:gz") as t:
 members=t.getmembers();assert len({m.name for m in members})==len(members)
 assert all(m.isfile() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts for m in members)
 raw=t.extractfile("MANIFEST.json").read();assert hashlib.sha256(raw).hexdigest()==mh
 files=json.loads(raw)["files"];assert len(files)==66 and len(members)==67
 assert {m.name for m in members}=={x["path"] for x in files}|{"MANIFEST.json"}
 for x in files:
  b=t.extractfile(x["path"]).read();assert len(b)==x["bytes"] and hashlib.sha256(b).hexdigest()==x["sha256"],x["path"]
print(json.dumps({"status":"ALL_MEMBERS_VERIFIED","archive_sha256":expected,"archive_bytes":size,"manifest_sha256":mh,"data_members":len(files),"all_members":len(members)}))
