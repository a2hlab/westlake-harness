import pathlib,json,subprocess,time,argparse
from stages import has_p2_marker
p=argparse.ArgumentParser();p.add_argument("run");p.add_argument("app");p.add_argument("--p2-wait",type=float,default=120);a=p.parse_args()
o=pathlib.Path(__file__).parent;r=pathlib.Path.home()/"a2hlab/board/5cd1e3dd00000000000000000923012c/verify32"/a.run
h=["/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh","-t","5cd1e3dd00000000000000000923012c"]
def dev(c):return subprocess.check_output(h+["shell",c],timeout=40).replace(b"\r",b"")
net=dev("ping -c 5 -W 2 1.1.1.1")
subprocess.run(["python3",str(o/"launch.py"),a.run,a.app],check=True)
(r/"network-before.txt").write_bytes(net);d=json.loads((r/"device-report.json").read_text());pid=d["child"];log=d["runtime"]+"/private-tmp/adapter_child_"+str(pid)+".stderr"
dev("aa start -b org.westlake.imehost -a EntryAbility")
start=time.monotonic();status="timeout"
while True:
 raw=dev("cat "+log+" 2>/dev/null");(r/"child.stderr").write_bytes(raw)
 if has_p2_marker(raw.decode(errors="replace")):status="bound";break
 stat=dev(f"cat /proc/{pid}/stat 2>/dev/null")
 if b") " not in stat or stat.rsplit(b") ",1)[1].startswith(b"Z"):status="exited-before-bind";break
 if time.monotonic()-start>=a.p2_wait:break
 time.sleep(2)
(r/"p2-wait.json").write_text(json.dumps({"requested_s":a.p2_wait,"elapsed_s":time.monotonic()-start,"status":status},indent=2));print(status,pid,flush=True)
