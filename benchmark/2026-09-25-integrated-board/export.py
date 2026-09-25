from pathlib import Path
import json,gzip,shutil,hashlib
src=Path("/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/board/5cd1e3dd00000000000000000923012c/verify32")
o=Path(__file__).parent;e=o/"evidence";e.mkdir(exist_ok=True)
for name in ["toutiao-1","toutiao-2","noice","wikipedia","framework","cleanup"]:
 dst=e/name;dst.mkdir(exist_ok=True)
 for f in (src/name).iterdir():
  if not f.is_file():continue
  if name=="cleanup" and f.suffix not in [".json",".txt"]:continue
  if f.name=="child.stderr":
   with gzip.GzipFile(filename=str(dst/"child.stderr.gz"),mode="wb",mtime=0) as g:g.write(f.read_bytes())
  elif f.suffix in [".txt",".json",".jsonl",".sh",".jpeg",".log"] or f.name.startswith("cppcrash"):shutil.copyfile(f,dst/f.name)
for f in src.iterdir():
 if f.is_file() and f.suffix in [".json",".log"]:shutil.copyfile(f,e/f.name)
scripts=o/"scripts";scripts.mkdir(exist_ok=True)
for f in Path("/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/ws/out-verify32").iterdir():
 if f.suffix in [".py",".sh"]:shutil.copyfile(f,scripts/f.name)
# Include the prior same-shim/no-metasec baseline as immutable recorded evidence.
prior=Path("/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/ws/westlake-applib23/evidence/property-bounds-23")
dst=e/"prior-bounds";dst.mkdir(exist_ok=True)
shutil.copyfile(prior/"summary.json",dst/"summary.json")
for name in ["bounds-online-1","bounds-online-2","bounds-online-3"]:
 t=dst/name;t.mkdir(exist_ok=True)
 for f in (prior/name).iterdir():
  if f.name in ["child.stderr.gz","run.sh","device-report.json"] or f.name.startswith("cppcrash"):shutil.copyfile(f,t/f.name)
manifest=[]
for f in sorted(e.rglob("*")):
 if f.is_file():manifest.append({"path":str(f.relative_to(o)),"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size})
(o/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("exported",len(manifest),"files")
