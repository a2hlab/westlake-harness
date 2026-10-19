import sys,json,shlex,time
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
oldboot,tag=sys.argv[1:];out=Path.home()/'.local/share/westlake/toutiao-resume-20261019'/tag;out.mkdir(exist_ok=False)
board=b.Board('61b0657200000000000000324012c' if False else '61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands')
for i in range(30):
 try:
  board.boot=None;board.ready();rc,t=board.shell('param get sys.westlake.demo.u13.ready',required=False)
  if board.boot!=oldboot and rc==0 and t.strip()=='true':
   (out/'ready.json').write_text(json.dumps({'boot':board.boot,'ready':True},indent=2)+'\n');print('READY',board.boot);break
 except Exception as e:print(type(e).__name__,str(e)[:120],flush=True)
 time.sleep(5)
else:raise SystemExit('READY timeout')
