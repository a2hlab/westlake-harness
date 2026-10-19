import sys,os,json,shlex,re,hashlib
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
out=Path.home()/'.local/share/westlake/toutiao-resume-20261019/video-p1-live-r2'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=os.environ['TT_EXPECTED_BOOT'];board.ready()
f='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/boots/'+board.boot
_,inst=board.shell('cat '+f+'/instance.txt');(out/'instance.txt').write_text(inst);d=dict(l.split('=',1) for l in inst.splitlines() if '=' in l);assert d['boot_id']==board.boot
for name in ['parent','child']:
 pid=d[name];assert pid.isdigit(),d
 for what in ['stat','environ','maps']:
  rc,t=board.shell('cat /proc/'+pid+'/'+what,required=False);(out/(name+'-'+what+'.txt')).write_text(t)
 _,state=board.shell('cat '+f+'/state; tail -n 8 '+f+'/events.log');(out/'guardian.txt').write_text(state)
rt='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
_,meta=board.shell('sha256sum '+rt+'/run.sh '+rt+'/libopensles_android_compat.so; stat -L -c %d:%i '+rt+'/run.sh /proc/'+d['parent']+'/root/data/local/tmp/asx/run.sh');(out/'runtime.txt').write_text(meta)
print(inst);print(meta);print('parent compat:',sum('libopensles_android_compat.so' in l for l in (out/'parent-maps.txt').read_text().splitlines()))
