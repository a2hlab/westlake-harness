from pathlib import Path
import gzip,json,hashlib,subprocess,sys
root=Path(__file__).resolve().parent;repo=Path(subprocess.check_output(["git","-C",str(root),"rev-parse","--show-toplevel"],text=True).strip());items=json.loads((root/"manifest.json").read_text())
for item in items:
 p=root/item["path"];data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==item["sha256"] and len(data)==item["bytes"],p
 if "--git" in sys.argv:assert subprocess.check_output(["git","-C",str(repo),"show","HEAD:"+str(p.relative_to(repo))])==data,p
for row in json.loads((root/"results.json").read_text()):
 raw=gzip.decompress((root/"evidence"/row["run"]/"child.stderr.gz").read_bytes());assert hashlib.sha256(raw).hexdigest()==row["stderr_sha256"]
 lines=raw.decode(errors="replace").splitlines();assert sum("__ndk1" in l and "symbol not found" in l for l in lines)==row["ndk1_error_lines"]
 for key in ["ndk1_errors","fatal","uncaught","ui_returned"]:
  for hit in row[key]:assert lines[hit["line"]-1]==hit["text"]
print("PASS",len(items),"evidence files and exact log metrics")
