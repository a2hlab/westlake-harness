import pathlib,json,gzip,hashlib,shutil,re
root=pathlib.Path(__file__).resolve().parent;vm=pathlib.Path("/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab")
r=vm/"board/5cd1e3dd00000000000000000923012c/images30cx";o=vm/"ws/out-images30cx";e=root/"evidence";e.mkdir(exist_ok=True);summary=[]
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if src.suffix in [".stderr",".log",".jsonl"] or src.name.endswith("exports.txt"):
  dst=dst.with_name(dst.name+".gz")
  with gzip.GzipFile(filename=str(dst),mode="wb",mtime=0) as g:g.write(src.read_bytes())
 else:shutil.copyfile(src,dst)
for name in ["baseline-1","full-1","full-2","control-noice","control-wikipedia"]:
 p=r/name
 if not (p/"child.stderr").exists():continue
 for f in p.iterdir():
  if f.is_file() and (f.suffix in [".stderr",".txt",".json",".jsonl",".log",".sh",".jpeg"] or f.name.startswith("cppcrash")):copy(f,e/name/f.name)
 raw=(p/"child.stderr").read_bytes();s=raw.decode(errors="replace");d=json.loads((p/"device-report.json").read_text())
 hits=lambda term:[{"line":i,"text":l} for i,l in enumerate(s.splitlines(),1) if term in l]
 errors=[{"line":i,"text":l} for i,l in enumerate(s.splitlines(),1) if "__ndk1" in l and "symbol not found" in l]
 row={"run":name,"child":d["child"],"stderr_sha256":hashlib.sha256(raw).hexdigest(),"ndk1_errors":errors,"ndk1_error_lines":len(errors),"fatal":hits("Fatal signal"),"uncaught":hits("[UNCAUGHT] thread="),"ui_returned":hits("launchActivityThread RETURNED"),"faults":[]}
 for f in p.glob("cppcrash*"):
  t=f.read_text(errors="replace");row["faults"].append({"file":f.name,"lifetime":re.search(r"Process life time:(.*)",t)[1],"reason":re.search(r"Reason:(.*)",t)[1],"thread":re.search(r"Tid:.*",t)[0]})
 if (p/"observation.json").exists():row["observed_s"]=json.loads((p/"observation.json").read_text())[-1]["elapsed"]
 summary.append(row)
for f in r.iterdir():
 if f.is_file() and f.suffix in [".json",".jsonl",".txt"]:copy(f,e/f.name)
for f in o.iterdir():
 if f.is_file() and f.suffix in [".json",".log"]:copy(f,e/"inputs"/f.name)
for folder in ["scripts","controls"]:
 for f in (o/folder).glob("*.py"):copy(f,root/folder/f.name)
shutil.copyfile(o/"targets.json",root/"targets.json")
(root/"results.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
manifest=[{"path":str(f.relative_to(root)),"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size} for f in sorted(e.rglob("*")) if f.is_file()]
(root/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n");print("export",len(manifest),[(x["run"],x["ndk1_error_lines"]) for x in summary])
