import sys,os,json,shlex,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/"benchmark/2026-09-28-bms-route-deploy/batch"))
import bms_batch as b
out=Path.home()/".local/share/westlake/toutiao-resume-20261019"/os.environ["TT_RUN_GROUP"]/sys.argv[1]
out.mkdir(parents=True,exist_ok=False)
board=b.Board("61b0657200000000000000000324012c","/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc","bash "+shlex.quote(str(repo/"scripts/lab/board_note.sh")),"outer(codex)",out/"commands")
board.boot=os.environ["TT_EXPECTED_BOOT"];board.ready()
for i,c in enumerate(sys.argv[2:]):
 rc,t=board.shell(c);(out/f"step-{i}.txt").write_text(t)
remote="/data/local/tmp/outer-1919-"+sys.argv[1]+".jpeg"
shot=b.capture(board,remote,out/"screen.jpeg");shot["captured"]=True
b.save(out/"record.json",{"serial":board.serial,"boot_id":board.boot,"key":"toutiao","screenshots":[shot],"commands":sys.argv[2:]})
print(json.dumps({"out":str(out),"shot":shot}))
