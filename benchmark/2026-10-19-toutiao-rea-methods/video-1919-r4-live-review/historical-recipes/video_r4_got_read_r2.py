import sys,json,shlex,re,hashlib
from pathlib import Path
repo=Path.cwd();sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
base=Path.home()/'.local/share/westlake/toutiao-resume-20261019';out=base/'video-r4-got-read-r2';out.mkdir(exist_ok=False)
board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot='fade993a-5649-44c5-9677-79f6ee82a8ad';board.ready()
guard='row=$(cat /proc/9360/stat); rest=${row##*) }; set -- $rest; test "${20}" = 18882; test "$2" = 6696; test "$(stat -c %u /proc/9360)" = 20011206; '
_,maps=board.shell('( set -eu; '+guard+'cat /proc/9360/maps )');(out/'maps.txt').write_text(maps)
old=(base/'video-r4-play1/maps-after.txt').read_text()
for name in ('libttmplayer.so','libopensles_android_compat.so'):
 rows=lambda s:[l for l in s.splitlines() if l.endswith('/'+name)]
 assert rows(maps)==rows(old),(name,'mapping changed')
# Four compat PT_LOAD offsets/vaddr pages have independently been reconciled.
proof=json.loads((base/'video-r4-compat-load-bias.json').read_text());assert all(x['load_bias']=='0x7f83e40000' for x in proof)
player=0x7e16a00000;compat=0x7f83e40000
r={'boot':board.boot,'child':9360,'child_birth':18882,'parent':6696,'player_base':hex(player),'compat_base':hex(compat),'reads':[],'note':'Exact mapping continuity and 4 PT_LOAD page-derived compat bias; read-only, not playback.'}
for off,target in [(0x4730b0,compat+0x3b98),(0x4730e8,compat+0x3b90),(0x473e58,player+0x47b380)]:
 addr=player+off
 cmd='( set -eu; '+guard+f'dd if=/proc/9360/mem of=/data/local/tmp/r4-got-{off:x}.bin bs=8 skip={addr//8} count=1 2>/dev/null; test \"$(stat -c %s /data/local/tmp/r4-got-{off:x}.bin)\" = 8; od -An -tx8 /data/local/tmp/r4-got-{off:x}.bin )'
 rc,t=board.shell(cmd,required=False);(out/f'got-{off:x}.txt').write_text(t)
 match=rc==0 and bool(re.fullmatch('[0-9a-fA-F]{16}',t.strip())) and int(t.strip(),16)==target
 r['reads'].append({'offset':hex(off),'slot':hex(addr),'expected':hex(target),'observed':t.strip(),'remote_rc':rc,'matched':match})
r['status']='matched' if all(x['matched'] for x in r['reads']) else 'unproved';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
