import sys,json,shlex,re
from pathlib import Path
repo=Path.cwd(); base=Path.home()/'.local/share/westlake/toutiao-resume-20261019'; out=base/'video-r7-logger-chain'; out.mkdir(exist_ok=False)
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot='904a55b5-1821-4f23-aa50-b08b731c0234';board.ready()
guard='set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = 904a55b5-1821-4f23-aa50-b08b731c0234; r=$(cat /proc/4979/stat); z=${r##*) }; set -- $z; test "${20}" = 6990; r=$(cat /proc/6951/stat); z=${r##*) }; set -- $z; test "${20}" = 8704; test "$2" = 4979; '
def shell(c): return board.shell('( '+guard+c+' )')[1]
maps=shell('cat /proc/6951/maps');(out/'maps.txt').write_text(maps)
reads=[]
def read(label,addr):
 row=[s for s in maps.splitlines() if int(s.split()[0].split('-')[0],16)<=addr and addr+8<=int(s.split()[0].split('-')[1],16)];assert len(row)==1
 value=shell(f'dd if=/proc/6951/mem bs=8 skip={addr//8} count=1 2>/dev/null | od -An -tx8').strip();assert re.fullmatch('[0-9a-fA-F]{16}',value)
 v=int(value,16); vr=[s for s in maps.splitlines() if int(s.split()[0].split('-')[0],16)<=v<int(s.split()[0].split('-')[1],16)]
 reads.append(dict(label=label,address=hex(addr),value=hex(v),address_map=row,value_maps=vr));(out/'reads.json').write_text(json.dumps(reads,indent=2));return v
read('liblog_is_loggable_GOT',0x7fab480000+0xd4f8)
logger=read('liblog_logger',0x7fab480000+0xe6f8);assert logger==0x7face5eff0
basebias=logger-0x1eff0
obj=read('libbase_logger_object',basebias+0x3ec38)
fn=read('libbase_function_object',obj+0x20)
vt=read('libbase_function_vtable',fn)
read('libbase_function_call',vt+0x30)
read('libbase_function_payload',fn+8)
assert read('libbase_logger_object_after',basebias+0x3ec38)==obj
assert read('libbase_function_object_after',obj+0x20)==fn
assert read('liblog_logger_after',0x7fab480000+0xe6f8)==logger
(out/'maps-after.txt').write_text(shell('cat /proc/6951/maps'))
print(json.dumps(reads,indent=2))
