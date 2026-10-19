"""Bounded real-video tap observation; preserves raw evidence, never claims playback."""
import argparse,hashlib,json,re,shlex,sys,time
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('boot','parent','parent-birth','child','child-birth','run-sha','tag'):p.add_argument('--'+n,required=True)
p.add_argument('--x',type=int,required=True);p.add_argument('--y',type=int,required=True);a=p.parse_args()
assert re.fullmatch('[0-9a-f-]{36}',a.boot) and re.fullmatch('[0-9a-f]{64}',a.run_sha)
assert re.fullmatch('[a-z0-9-]+',a.tag)
assert all(v.isdigit() for v in (a.parent,a.parent_birth,a.child,a.child_birth))
assert 0<=a.x<1200 and 0<=a.y<1920
repo=Path.cwd();sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
out=Path.home()/'.local/share/westlake/toutiao-resume-20261019'/a.tag;out.mkdir(exist_ok=False)
board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=a.boot;board.ready()
def read(n,c,required=True):
 rc,t=board.shell(c,required=required);(out/n).write_text(t);return rc,t
_,t=read('parent-before.stat','cat /proc/'+a.parent+'/stat');assert t.rsplit(') ',1)[1].split()[19]==a.parent_birth
_,t=read('child-before.stat','cat /proc/'+a.child+'/stat');cols=t.rsplit(') ',1)[1].split();assert cols[19]==a.child_birth and cols[1]==a.parent
_,t=read('child-uid.txt','cat /proc/'+a.child+'/status');assert re.search(r'^Uid:\s+20011206\s+20011206\s',t,re.M)
_,t=read('run-sha.txt','sha256sum /proc/'+a.parent+'/root/data/local/tmp/asx/run.sh');assert t.split()[0]==a.run_sha
log='/proc/'+a.parent+'/root/data/service/el1/public/appspawnx/adapter_child_'+a.child+'.stderr'
_,t=read('stderr-before-wc.txt','wc -l '+log);start_line=int(t.split()[0])
read('maps-before.txt','cat /proc/'+a.child+'/maps')
remote='/data/local/tmp/ttvideo-probe-'+a.tag;board.shell('mkdir '+remote)
r={'key':'toutiao','serial':board.serial,'boot_id':a.boot,'parent':a.parent,'parent_birth':a.parent_birth,'child':a.child,'child_birth':a.child_birth,'run_sha256':a.run_sha,'tap':{'x':a.x,'y':a.y},'stderr_baseline_lines':start_line,'screenshots':[],'playback_verdict':'pending_visual_review','audio_verdict':'unknown'}
b.save(out/'record.json',r)
board.shell(f'uitest uiInput click {a.x} {a.y}');r['tap_completed_at']=time.time();start=time.monotonic();board.shell('power-shell timeout -o 86400000')
for seconds in (5,20,25):
 time.sleep(max(0,seconds-(time.monotonic()-start)))
 shot=b.capture(board,remote+f'/t{seconds}.jpeg',out/f't{seconds}.jpeg');shot['captured']=True;shot['target_seconds']=seconds;r['screenshots'].append(shot);b.save(out/'record.json',r)
read('child-after.stat','cat /proc/'+a.child+'/stat',False)
rc,maps=read('maps-after.txt','cat /proc/'+a.child+'/maps',False)
read('parent-maps-after.txt','cat /proc/'+a.parent+'/maps',False)
board.receive(log,out/'child-full.stderr')
raw=(out/'child-full.stderr').read_text(errors='replace').splitlines()
(out/'stderr-delta.txt').write_text('\n'.join(raw[start_line:])+'\n')
need=('SOURCE-NATIVE-LOAD-FAIL','UnsatisfiedLinkError','SOURCE-NATIVE-INITARRAY','WESTLAKE-ANW','MediaCodec','AudioRenderer','TTPlayer','libmffmpeg')
lines=[f'{i+1}:{line}' for i,line in enumerate(raw) if any(n in line for n in need)]
(out/'media-selected.txt').write_text('\n'.join(lines)+'\n')
if rc==0:
 def bases(name):
  return sorted({int(c[0].split('-')[0],16) for line in maps.splitlines() if len(c:=line.split())>=6 and int(c[2],16)==0 and c[5].endswith('/'+name)})
 player=bases('libttmplayer.so');compat=bases('libopensles_android_compat.so')
 got={'player_bases':player,'compat_bases':compat,'status':'unknown','note':'Read-only relocation evidence, not playback proof'}
 if len(player)==len(compat)==1:
  got['reads']=[]
  for off,expected,targetbase in [(0x4730b0,0x3b98,compat[0]),(0x4730e8,0x3b90,compat[0]),(0x473e58,0x47b380,player[0])]:
   addr=player[0]+off
   dst=remote+f'/got-{off:x}.bin'
   cmd=f'( set -eu; row=$(cat /proc/{a.child}/stat); rest=${{row##*) }}; set -- $rest; test \"${{20}}\" = {a.child_birth}; test \"$2\" = {a.parent}; dd if=/proc/{a.child}/mem of={dst} bs=8 skip={addr//8} count=1 2>/dev/null; test \"$(stat -c %s {dst})\" = 8; od -An -tx8 {dst} )'
   rc,text=read(f'got-{off:x}.txt',cmd,False)
   actual=text.strip();got['reads'].append({'slot':hex(addr),'expected':hex(targetbase+expected),'observed':actual,'command_rc':rc,'matches':rc==0 and bool(re.fullmatch('[0-9a-fA-F]{16}',actual)) and int(actual,16)==targetbase+expected})
  got['status']='matched' if all(x['matches'] for x in got['reads']) else 'unproved'
 b.save(out/'got.json',got)
b.save(out/'record.json',r);print(out);print('\n'.join(x for x in lines if 'SOURCE-NATIVE-LOAD-FAIL' in x)[-3000:])
