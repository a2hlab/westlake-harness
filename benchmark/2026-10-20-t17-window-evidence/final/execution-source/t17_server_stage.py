from pathlib import Path
import json,subprocess,sys,time,shlex,hashlib
repo=Path.cwd();base=Path(__file__).parent;w=base/'t17-5cd-window-01';c=json.loads((w/'context.json').read_text());p=json.loads((w/'candidate-retry-profile/profile.json').read_text());out=w/'observer-stage';out.mkdir(exist_ok=False)
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
sys.path.insert(0,str(repo/'benchmark/2026-10-20-t17-network-reuse'));import read_binding
class Board(b.Board):
 def ready(self):
  assert time.time()-c['start']<1080
  super().ready();rc,h=self.command(self.lock+['held',self.serial],10);assert rc==0 and h.strip()==c['holder']
board=Board(c['serial'],c['hdc'],'bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=p['boot'];board.ready()
src=Path.home()/'Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/lib64/clang/12.0.8/lib/linux/aarch64/lldb-server';digest='13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a';assert hashlib.sha256(src.read_bytes()).hexdigest()==digest
remote='/data/local/tmp/t17-lldb-5807db3d';g=read_binding.guard(p);board.shell('(set -eu; '+g+'; test ! -e '+remote+'; mkdir '+remote+'; chmod 700 '+remote+' )');board.send(src,remote+'/lldb-server');board.shell('(set -eu; '+g+'; test "$(sha256sum '+remote+'/lldb-server | cut -d\' \' -f1)" = '+digest+'; chmod 700 '+remote+'/lldb-server; echo T17_SERVER_STAGED )');print(remote)
