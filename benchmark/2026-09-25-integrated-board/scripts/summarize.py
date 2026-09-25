import pathlib,json,re,hashlib
r=pathlib.Path.home()/"a2hlab/board/5cd1e3dd00000000000000000923012c/verify32"
rows=[]
for name in ["toutiao-1","toutiao-2","noice","wikipedia"]:
 p=r/name
 if not (p/"child.stderr").exists():continue
 d=json.loads((p/"device-report.json").read_text());raw=(p/"child.stderr").read_bytes();s=raw.decode(errors="replace");lines=s.splitlines()
 hits=lambda token:[{"line":i,"text":l} for i,l in enumerate(lines,1) if token in l]
 row={"run":name,"child":d["child"],"stderr_sha256":hashlib.sha256(raw).hexdigest(),"fatal":hits("Fatal signal"),"uncaught":hits("[UNCAUGHT] thread="),"p2_markers":hits("sBindAppDone=true"),"asurface_errors":hits("Unable to load function ASurface"),"cronet_boot":hits("bootSucceed"),"b47":hits("B47-SLA"),"ui_returned":hits("launchActivityThread RETURNED"),"faults":[]}
 for f in p.glob("cppcrash*"):
  t=f.read_text();row["faults"].append({"file":f.name,"lifetime":re.search(r"Process life time:(.*)",t)[1],"reason":re.search(r"Reason:(.*)",t)[1],"registers":next(l for l in t.splitlines() if l.startswith("lr:"))})
 if (p/"observation.json").exists():
  obs=json.loads((p/"observation.json").read_text());row["observation_elapsed_s"]=obs[-1]["elapsed"];row["observation_has_process_and_ui"]=obs[-1]["proc"].count(") ")==2
 if (p/"p2-wait.json").exists():row["p2_wait"]=json.loads((p/"p2-wait.json").read_text())
 rows.append(row)
(r/"results.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n")
print(json.dumps([{k:v for k,v in x.items() if k not in ["b47","p2_markers","uncaught"]} for x in rows],indent=2))
