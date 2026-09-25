import json,pathlib,subprocess,sys
r=pathlib.Path.home()/"a2hlab/board/5cd1e3dd00000000000000000923012c/images30cx"/sys.argv[1]
d=json.loads((r/"device-report.json").read_text())
h="/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh";S="5cd1e3dd00000000000000000923012c"
def dev(c):return subprocess.check_output([h,"-t",S,"shell",c],timeout=40).decode()
pid=d["child"]
raw=dev(f"cat /proc/{pid}/stat; cat /proc/uptime")
(r/"final-proc.txt").write_text(raw)
subprocess.run(["python3",str(pathlib.Path(__file__).with_name("collect.py")),sys.argv[1]],check=True)
faults=dev(f'find /data/log/faultlog -type f -name "*-{pid}-*"')
(r/"fault-paths.txt").write_text(faults)
for f in faults.splitlines():
 if f.startswith("/"): subprocess.run([h,"-t",S,"file","recv",f,pathlib.Path(f).name],cwd=r,check=True)
for key in ("child","parent"):
 p=d[key];stat=dev(f"cat /proc/{p}/stat 2>/dev/null")
 if ") " in stat and (key=="child" or "appspawn-x" in dev(f"readlink /proc/{p}/exe")):
  start=stat.rsplit(") ",1)[1].split()[19]
  now=dev(f"cat /proc/{p}/stat 2>/dev/null")
  if ") " in now and now.rsplit(") ",1)[1].split()[19]==start:dev(f"kill -9 {p}")
