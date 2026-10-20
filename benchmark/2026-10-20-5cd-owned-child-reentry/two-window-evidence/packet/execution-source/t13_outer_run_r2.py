import json,subprocess,sys,time
from pathlib import Path
b=Path(__file__).parent/"t13-5cd-window-02"
c=json.loads((b/"context.json").read_text())
action=sys.argv[1]; repo=Path(c["repo"]); tool=repo/"benchmark/2026-10-20-5cd-owned-child-reentry"
if action in ("prepare","launch","capture"):
 tag=sys.argv[2]; out=b/"ui"/tag
 argv=[sys.executable,str(tool/"ui.py"),action,"--execute","--repo",str(repo),"--hdc",c["hdc"],"--holder",c["holder"],"--start",str(c["start"]),"--root",str(b/"ui"),"--tag",tag,"--receipt",str(b/"apply/result.json")]+sys.argv[3:]
else:
 out=b/action
 argv=[sys.executable,str(tool/"tool.py"),action,"--execute","--repo",str(repo),"--hdc",c["hdc"],"--holder",c["holder"],"--window-start",str(c["start"]),"--root",c["remote_root"],"--exit-mode","term-once","--out",str(out)]
 if action!="preflight":argv += ["--receipt",str(b/("preflight/result.json" if action=="apply" else "apply/result.json"))]
log=b/("outer-"+action+("-"+sys.argv[2] if action in ("prepare","launch","capture") else "")); log.with_suffix(".argv.json").write_text(json.dumps(argv))
try:
 r=subprocess.run(argv,capture_output=True,timeout=150); rc=r.returncode; stdout=r.stdout; stderr=r.stderr
except subprocess.TimeoutExpired as e:
 rc=124;stdout=e.stdout or b"";stderr=e.stderr or b""
log.with_suffix(".stdout").write_bytes(stdout);log.with_suffix(".stderr").write_bytes(stderr);log.with_suffix(".rc").write_text(str(rc));print(stdout.decode(errors="replace"));print(stderr.decode(errors="replace"));print("outer_rc",rc,"elapsed",time.time()-c["start"]);sys.exit(rc)
