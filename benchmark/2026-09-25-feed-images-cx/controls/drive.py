import json,subprocess,sys,time,pathlib
S="5cd1e3dd00000000000000000923012c"
H="/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh"
r=pathlib.Path.home()/"a2hlab/board"/S/"images30cx"/sys.argv[1]
d=json.loads((r/"device-report.json").read_text())
log=d["runtime"]+"/private-tmp/adapter_child_"+str(d["child"])+".stderr"
def dev(s):
    return subprocess.check_output([H,"-t",S,"shell",s],timeout=40).replace(b"\r",b"")
op=sys.argv[2]
if op=="vt":
    n=int(dev("wc -l < "+log).strip())
    dev("echo v > /data/local/tmp/noice_tap");time.sleep(3)
    raw=dev("tail -n +"+str(n+1)+" "+log)
    name="vt-"+str(int(time.time()))+".txt"
    (r/name).write_bytes(raw)
    print(raw.decode(errors="replace"))
elif op=="shot":
    name=sys.argv[3]+".jpeg"
    dev("snapshot_display -f /data/local/tmp/integrate14.jpeg >/dev/null")
    subprocess.run([H,"-t",S,"file","recv","/data/local/tmp/integrate14.jpeg",name],cwd=r,check=True)
    print(r/name)
elif op=="shell":
    event={"time_epoch":time.time(),"command":sys.argv[3]}
    with (r/"actions.jsonl").open("a") as f:f.write(json.dumps(event)+"\n")
    print(dev(sys.argv[3]).decode(errors="replace"))
elif op=="log":
    print(dev("tail -n "+(sys.argv[3] if len(sys.argv)>3 else "50")+" "+log).decode(errors="replace"))
