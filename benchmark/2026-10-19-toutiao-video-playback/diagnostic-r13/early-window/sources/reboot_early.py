from pathlib import Path
import sys,json,shlex
repo=Path.cwd();sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
boot,tag=sys.argv[1:];out=Path.home()/'.local/share/westlake/toutiao-resume-20261019'/tag;out.mkdir(exist_ok=False)
bd=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');bd.boot=boot;bd.ready()
r=bd.command(bd.hdc+['-t',bd.serial,'target','boot']);(out/'result.json').write_text(json.dumps({'boot':boot,'reboot_transport_rc':r[0],'output':r[1]}));print(r)
