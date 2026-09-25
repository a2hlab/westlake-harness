from pathlib import Path
import json,gzip,hashlib,subprocess,sys
root=Path(__file__).resolve().parent
repo=Path(subprocess.check_output(["git","-C",str(root),"rev-parse","--show-toplevel"],text=True).strip())
items=json.loads((root/"manifest.json").read_text())
for item in items:
 p=root/item["path"];data=p.read_bytes()
 assert len(data)==item["bytes"] and hashlib.sha256(data).hexdigest()==item["sha256"],p
 if "--git" in sys.argv:assert subprocess.check_output(["git","-C",str(repo),"show","HEAD:"+str(p.relative_to(repo))])==data,p
for row in json.loads((root/"evidence/results.json").read_text()):
 raw=gzip.decompress((root/"evidence"/row["run"]/"child.stderr.gz").read_bytes())
 assert hashlib.sha256(raw).hexdigest()==row["stderr_sha256"]
 lines=raw.decode(errors="replace").splitlines()
 for field in ["fatal","uncaught","p2_markers","asurface_errors","cronet_boot","b47","ui_returned"]:
  for hit in row[field]:assert lines[hit["line"]-1]==hit["text"]
 assert len(row["asurface_errors"])==sum("Unable to load function ASurface" in l for l in lines)
 assert len(row["cronet_boot"])==sum("bootSucceed" in l for l in lines)
 assert len(row["fatal"])==sum("Fatal signal" in l for l in lines)
print("PASS",len(items),"evidence files, 4 stderr hashes and cited line checks")
