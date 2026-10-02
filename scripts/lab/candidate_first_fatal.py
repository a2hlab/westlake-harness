import json,glob,os,subprocess,sys
WS=os.environ.get("WORKSPACES",os.path.expanduser("~/orca/workspaces"))
REPO=WS+"/westlake-harness"
OUT=sys.argv[1]; os.makedirs(OUT,exist_ok=True)
so=json.load(open(REPO+"/benchmark/2026-10-01-u9-sweep/outer-signoff.json"))
nonlit={k for k,v in so["keys"].items() if v.get("verdict")!="lit"}
res={}; src={}
for rec in sorted(glob.glob(WS+"/westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window5/**/runner/*/*/*/*/record.json",recursive=True)):
    if "/smoke/" in rec: continue
    kd=os.path.dirname(rec); k=os.path.basename(kd)
    if k not in nonlit or k in res: continue
    r=subprocess.run(["python3",REPO+"/scripts/lab/first_fatal.py",kd],capture_output=True,text=True,timeout=300)
    try: res[k]=json.loads(r.stdout)
    except Exception: res[k]={"status":"unknown","error":(r.stderr or r.stdout)[-300:]}
    src[k]=kd.replace(WS,"$WORKSPACES")
json.dump(res,open(OUT+"/first-fatal.json","w"),indent=1,ensure_ascii=False)
json.dump(src,open(OUT+"/sources.json","w"),indent=1)
c=subprocess.run(["python3",REPO+"/scripts/lab/cluster_first_cause.py",OUT+"/first-fatal.json"],capture_output=True,text=True)
open(OUT+"/clusters.json","w").write(c.stdout)
print("non-lit keys:",len(nonlit),"with window5 runs:",len(res),"| missing:",sorted(nonlit-set(res)))
try:
    cl=json.loads(c.stdout)
    items=cl.items() if isinstance(cl,dict) else enumerate(cl)
    for name,v in list(items)[:20]:
        keys=v.get("keys") if isinstance(v,dict) else v
        print(len(keys) if isinstance(keys,list) else '?', str(name)[:110])
except Exception as e: print("cluster output:",c.stdout[:500],c.stderr[-300:])
