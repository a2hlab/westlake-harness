import sys,json,time,shlex,re
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/"benchmark/2026-09-28-bms-route-deploy/batch"))
import bms_batch as b
out=Path.home()/".local/share/westlake/toutiao-resume-20261019/video-p1-live-r2/play-observe-1";out.mkdir(parents=True,exist_ok=False)
se="61b0657200000000000000000324012c";boot="db544de8-d26b-4c19-95d9-75ed10b34aae"
board=b.Board(se,"/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc","bash "+shlex.quote(str(repo/"scripts/lab/board_note.sh")),"outer(codex)",out/"commands");board.boot=boot;board.ready()
pid="7644";birth="16540";parent="5785"
f="/proc/"+parent+"/root/data/service/el1/public/appspawnx/adapter_child_"+pid+".stderr"
remote="/data/local/tmp/ttvideo-observe-20261019-p1r2";board.shell("mkdir -p "+remote)
record={"serial":se,"boot_id":boot,"package":"org.westlake.imehost","child":int(pid),"birth":birth,"parent":int(parent),"screenshots":[],"trigger":"previous video tab tap; no new tap in this observation"}
def read(name,cmd,required=True):
 rc,t=board.shell(cmd,required=required);(out/name).write_text(t);return rc,t
_,stat=read("child-before.stat","cat /proc/"+pid+"/stat");parts=stat.rsplit(") ",1)[1].split();assert parts[1]==parent and parts[19]==birth
_,r=read("run-sha.txt","sha256sum /proc/"+parent+"/root/data/local/tmp/asx/run.sh");assert r.split()[0]=="ea98494255b05699ca24b134e6ada8849b023b4ab59d3d7e291194cfa8425f73"
_,wc=read("stderr-before-wc.txt","wc -l "+f);baseline=int(wc.split()[0]);record["stderr_baseline_lines"]=baseline
read("maps-before.txt","cat /proc/"+pid+"/maps")
read("media-before.txt","grep -n -E 'SOURCE-NATIVE-LOAD|libttmplayer|libtexturerender|libvcbasekit|libmffmpeg|SL_IID|WESTLAKE-ANW|AJMediaCodec|MediaCodec|AudioTrack|TTVideoEngine|UnsatisfiedLinkError' "+f,False)
board.shell("hilog -x > "+remote+"/hilog-before.txt");board.receive(remote+"/hilog-before.txt",out/"hilog-before.txt")
b.save(out/"record.json",record)
board.shell("power-shell timeout -o 86400000");start=time.monotonic();record["tap_time"]=time.time()
for seconds in (20,25):
 time.sleep(max(0,seconds-(time.monotonic()-start)))
 shot=b.capture(board,remote+f"/t{seconds}.jpeg",out/f"t{seconds}.jpeg");shot["captured"]=True;record["screenshots"].append(shot);b.save(out/"record.json",record)
read("child-after.stat","cat /proc/"+pid+"/stat",False)
read("maps-after.txt","cat /proc/"+pid+"/maps",False)
read("stderr-delta.txt",f"tail -n +{baseline+1} "+f,False)
read("media-all-after.txt","grep -n -E 'SOURCE-NATIVE-LOAD|libttmplayer|libtexturerender|libvcbasekit|libmffmpeg|SL_IID|WESTLAKE-ANW|AJMediaCodec|MediaCodec|AudioTrack|TTVideoEngine|UnsatisfiedLinkError' "+f,False)
board.shell("hilog -x > "+remote+"/hilog-after.txt");board.receive(remote+"/hilog-after.txt",out/"hilog-after.txt")
read("processes-after.txt","ps -A -o PID,PPID,UID,NAME")
board.receive(f,out/"child-full.stderr")
b.save(out/"record.json",record);print(out)
text=(out/"stderr-delta.txt").read_text();print("delta bytes",len(text));print("\n".join(x for x in text.splitlines() if any(t in x for t in ["SOURCE-NATIVE-LOAD-FAIL","SL_IID","libttmplayer","UnsatisfiedLinkError"])))
