from pathlib import Path
import json,subprocess,sys,time
b=Path(__file__).parent/"t13-5cd-window-02"; c=json.loads((b/"context.json").read_text());repo=Path(c["repo"]);sys.path.insert(0,str(repo/"benchmark/2026-10-20-5cd-owned-child-reentry"));import tool
d=b/sys.argv[1];d.mkdir(exist_ok=False)
held=subprocess.check_output(["bash",str(repo/"scripts/lab/board_note.sh"),"held",c["serial"]]).decode().strip();assert held==c["holder"];assert time.time()-c["start"]<600
root=c["remote_root"];body=sys.argv[2] if len(sys.argv)>2 else 'for n in state events.log instance.txt adopted sequence spawn.txt; do printf "FILE=%s\\n" "$n"; if [ -f '+root+'/$n ]; then tail -18 '+root+'/$n; else echo ABSENT; fi; done; ps -A -o PID,PPID,UID,NAME; if [ -e /proc/31210/stat ]; then cat /proc/31210/stat; else echo OLD_CHILD_ABSENT; fi'
s='(set -eu; '+tool.shell_guard()+body+'; '+tool.shell_guard()+'echo T13_READ_COMPLETE)'
a=[c["hdc"],"-t",c["serial"],"shell",s];(d/"argv.json").write_text(json.dumps(a));r=subprocess.run(a,capture_output=True,timeout=15);(d/"stdout").write_bytes(r.stdout);(d/"stderr").write_bytes(r.stderr);(d/"rc").write_text(str(r.returncode));text=r.stdout.decode(errors="replace");assert r.returncode==0 and text.rstrip().endswith("T13_READ_COMPLETE");print("\n".join(l for l in text.splitlines() if not l.strip()[:1].isdigit() or any(k in l for k in ("article.news","appspawn","imehost","reason="))));print("elapsed",time.time()-c["start"])
