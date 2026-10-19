"""Narrow diagnostic control. Exact serial, held lock, expected boot, one log key."""
import sys,json,shlex
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
mode,boot,tag=sys.argv[1:];assert mode in ('reboot','setlog','metadata')
out=Path.home()/'.local/share/westlake/toutiao-resume-20261019'/tag;out.mkdir(exist_ok=False)
board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=boot;board.ready()
rc,old=board.shell('param get debug.ttplayer.log.enable',required=False);(out/'param-before.txt').write_text(old)
rc,ps=board.shell('ps -A -o PID,PPID,UID,NAME');(out/'processes-before.txt').write_text(ps)
if mode=='setlog':
 assert 'errNum is:106' in old,old
 assert not any('id.article.news' in x or 'com.ss.android.article.news' in x for x in ps.splitlines()),'existing Toutiao child: logging must precede library initialization'
 board.shell('param set debug.ttplayer.log.enable true')
 rc,new=board.shell('param get debug.ttplayer.log.enable');(out/'param-after.txt').write_text(new);assert new.strip()=='true',new
elif mode=='reboot':
 board.command(board.hdc+['-t',board.serial,'target','boot'])
(out/'result.json').write_text(json.dumps({'mode':mode,'boot':boot,'completed':True},indent=2)+'\n')
