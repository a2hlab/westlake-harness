import sys,os,json,time,shlex
from pathlib import Path
repo=Path(os.environ.get("WESTLAKE_REPO",Path.cwd())).resolve()
sys.path.insert(0,str(repo/"benchmark/2026-09-28-bms-route-deploy/batch"))
import bms_batch as b
serial="61b0657200000000000000000324012c"
expected=os.environ.get("TT_EXPECTED_BOOT","f59c05dd-85b1-40f9-8ad5-baec804d642f")
base=Path.home()/".local/share/westlake/toutiao-resume-20261019"
action,tag=sys.argv[1:3]
out=base/os.environ.get("TT_RUN_GROUP","icon-manual-live-r2")/tag
out.mkdir(parents=True,exist_ok=False)
board=b.Board(serial,"/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc","bash "+shlex.quote(str(repo/"scripts/lab/board_note.sh")),"outer(codex)",out/"commands")
board.boot=expected
board.ready()
f=os.environ.get("TT_CONTROL_ROOT","/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r1")+"/boots/"+board.boot
remote="/data/local/tmp/icon-accept-20261019-"+tag
board.shell("mkdir -p "+remote)
record={"serial":serial,"boot_id":board.boot,"package":"org.westlake.imehost","key":"toutiao","screenshots":[],"action":action}
for name,cmd in [("guardian-before","cat "+f+"/state "+f+"/instance.txt "+f+"/sequence; tail -n 15 "+f+"/events.log"),("processes-before","ps -A -o PID,PPID,UID,NAME")]:
 rc,t=board.shell(cmd,required=False);(out/(name+".txt")).write_text(t)
if action=="launch":
 b.desktop_launch(board,{"package":"org.westlake.imehost","launch_activity":"EntryAbility"},remote,out,record)
 time.sleep(5)
elif action=="click":
 x,y=map(int,sys.argv[3:5]);board.shell(f"uitest uiInput click {x} {y}");board.shell("power-shell timeout -o 86400000");time.sleep(5)
shot=b.capture(board,remote+"/screen.jpeg",out/"screen.jpeg")
shot["captured"]=True;record["screenshots"].append(shot)
b.save(out/"record.json",record)
for name,cmd in [("guardian-after","cat "+f+"/state "+f+"/instance.txt "+f+"/sequence; tail -n 20 "+f+"/events.log"),("processes-after","ps -A -o PID,PPID,UID,NAME"),("windows","hidumper -s WindowManagerService -a '-a'")]:
 rc,t=board.shell(cmd,required=False);(out/(name+".txt")).write_text(t)
print(json.dumps({"out":str(out),"shot":shot},ensure_ascii=False))
