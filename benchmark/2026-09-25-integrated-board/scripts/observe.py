import json,pathlib,subprocess,time,sys
R=pathlib.Path.home()/"a2hlab/board/5cd1e3dd00000000000000000923012c/verify32"
r=R/sys.argv[1];duration=float(sys.argv[2]);d=json.loads((r/"device-report.json").read_text());pid=d["child"]
h="/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh";serial="5cd1e3dd00000000000000000923012c"
def dev(c):return subprocess.check_output([h,"-t",serial,"shell",c],timeout=35).decode(errors="replace")
ui=(r/"ui-tid.txt").read_text().strip() if (r/"ui-tid.txt").exists() else str(pid)
start=time.monotonic();rows=[];ident=None
while True:
 raw=dev(f"cat /proc/{pid}/stat; cat /proc/{pid}/task/{ui}/stat; cat /proc/uptime")
 row={"elapsed":time.monotonic()-start,"proc":raw}
 rows.append(row);(r/"observation.json").write_text(json.dumps(rows,indent=2))
 if raw.count(") ")<2:print("PROCESS_OR_UI_GONE",flush=True);break
 current=raw.splitlines()[0].rsplit(") ",1)[1].split()[19]
 if ident is None:ident=current
 if current!=ident:print("PID_REUSED",flush=True);break
 if row["elapsed"]>=duration:print("OBSERVED",row["elapsed"],flush=True);break
 time.sleep(min(10,duration-row["elapsed"]))
subprocess.run(["python3",str(pathlib.Path(__file__).with_name("collect.py")),sys.argv[1]],check=True)
