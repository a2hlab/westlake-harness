"""Outer-only normal UI; exact 5cd lock/boot/window; temporary awake authority from T12 apply receipt."""
import argparse,datetime,json,os,re,shlex,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','launch','capture','click']);p.add_argument('--repo',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--holder',required=True);p.add_argument('--start',type=float,required=True);p.add_argument('--hdc',required=True);p.add_argument('--x',type=int);p.add_argument('--y',type=int);p.add_argument('--identity',type=Path);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
serial='5cd1e3dd00000000000000000923012c';boot='0525bb05-f714-42ad-90f0-ecdb10356c4f'
if not a.execute:print(json.dumps({'execute':False,'serial':serial,'device_calls':0}));sys.exit(0)
age=time.time()-a.start
assert 0<=age<600, 'future or expired window'
assert abs(a.start-datetime.datetime.fromisoformat(a.holder.split()[2]).timestamp())<1, 'window start must match exact lock timestamp'
authority=json.loads(a.receipt.read_text());assert authority['serial']==serial and authority['boot']==boot and authority['window_start']==a.start and authority['status']=='ARMED_WAIT_ACTUAL_ICON'
assert authority.get('power_original') and authority.get('guardian')
assert authority.get('holder')==a.holder
assert re.fullmatch('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t12-[a-z0-9-]+',authority['root'])
monotonic_deadline=min(time.monotonic()+540-age,authority['monotonic_deadline']-60)
assert a.tag.replace('-','').isalnum() and a.root.is_absolute() and not str(a.root).startswith(('/tmp/','/private/tmp/'))
sys.path.insert(0,str(a.repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
out=a.root/a.tag;out.mkdir(parents=True,exist_ok=False)
class UI(b.Board):
 def command(self,argv,timeout=60):
  remaining=monotonic_deadline-time.monotonic()
  if remaining<=0:raise b.BatchStop('600 second window elapsed')
  return super().command(argv,min(timeout,remaining))
 def ready(self):
  super().ready()
  rc,holder=self.command(self.lock+['held',serial],10)
  if rc or holder.strip()!=a.holder:raise b.BatchStop('exact lock holder changed')
 def shell(self,cmd,required=True,timeout=60):
  ui='uitest ' in cmd
  if ui:
   entry={'command':cmd,'attempted':True,'result':'unknown'}
   record.setdefault('ui_calls',[]).append(entry);b.save(out/'record.json',record)
  result=super().shell(cmd,required,timeout)
  if ui:
   entry.update(result='completed' if result[0]==0 else 'failed',remote_rc=result[0])
   selected=record.get('selected_icon')
   if result[0]==0 and a.action=='launch' and selected and cmd=='uitest uiInput click %d %d'%tuple(selected['center']):
    record.update(clicked=True,clicked_at=time.time(),click_monotonic=time.monotonic())
   if result[0]==0 and a.action=='click':record['video_ui_command_completed']=True
   b.save(out/'record.json',record)
  if ui:
   super().shell('power-shell timeout -o 86400000',True,10)
   rc,power=super().shell('power-shell dump -s',True,10)
   if 'OverrideTimeout=86400000ms' not in power:raise b.BatchStop('awake readback mismatch')
  return result

board=UI(serial,a.hdc,'bash '+shlex.quote(str(a.repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=boot;board.ready()
remote='/data/local/tmp/t12-5cd-'+str(int(a.start))+'-'+a.tag
record={'serial':serial,'boot_id':boot,'key':'toutiao','package':'org.westlake.imehost','action':a.action,'screenshots':[],'playback':'unknown'}
def check_identity():
 if not a.identity:return
 r=json.loads(a.identity.read_text());assert r['boot']==boot and r['serial']==serial
 for role in ['parent','child']:
  x=r[role];assert x and x['pid']>1
  rc,raw=board.shell('cat /proc/%d/stat'%x['pid']);tail=raw.rsplit(') ',1)[1].split()
  if int(tail[1])!=x['ppid'] or int(tail[19])!=x['birth'] or tail[0] in ('Z','X'):raise b.BatchStop('UI child identity changed')
check_identity();board.shell('mkdir -p '+shlex.quote(remote))
try:
 if a.action=='prepare':
  board.shell('power-shell wakeup')
  tree=b.layout(board,remote,out,'prepare-layout')
  ids=[str(q.get('id') or q.get('key') or '') for q in b.attributes(tree)]
  if any('ScreenLockRootComponent' in q for q in ids):
   panel=b.panel(tree,None);assert panel
   x1,y1,x2,y2=panel
   board.shell(f'uitest uiInput swipe {(x1+x2)//2} {y2-(y2-y1)//10} {(x1+x2)//2} {y1+(y2-y1)//5}')
  board.shell('uitest uiInput keyEvent Home')
  record['launcher_focus_gate']=b.launcher_focused(board)
 elif a.action=='launch':
  rc,events=board.shell('cat '+shlex.quote(authority['root']+'/events.log'))
  assert 't12_desktop_seen' in events, 'guardian has not observed desktop'
  with (a.root/'launch-once.json').open('x') as f:json.dump({'started':time.time(),'maximum_icon_clicks':1},f)
  b.desktop_launch(board,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},remote,out,record)
 elif a.action=='click':
  assert a.identity and a.x is not None and a.y is not None
  with (a.root/'video-ui-once.json').open('x') as f:json.dump({'started':time.time(),'x':a.x,'y':a.y},f)
  r=json.loads(a.identity.read_text());guards=[]
  for role in ['parent','child']:
   q=r[role];pid=int(q['pid']);birth=int(q['birth']);ppid=int(q['ppid'])
   guards.append('r=$(cat /proc/%d/stat); z=${r##*) }; set -- $z; test "${20}" = %d; test "$2" = %d; test "$1" != Z; test "$1" != X'%(pid,birth,ppid))
  guard='; '.join(guards)
  board.shell('(set -eu; '+guard+f'; uitest uiInput click {a.x} {a.y}; '+guard+')')
 board.shell('power-shell wakeup');check_identity()
 shot=b.capture(board,remote+'/screen.jpeg',out/'screen.jpeg');shot['captured']=True;record['screenshots'].append(shot)
 for name,cmd in [('ps','ps -A -o PID,PPID,UID,NAME'),('windows',"hidumper -s WindowManagerService -a '-a'")]:
  rc,text=board.shell(cmd);(out/(name+'.txt')).write_text(text+'\n')
 check_identity()
finally:
 b.save(out/'record.json',record)
print(json.dumps({'out':str(out),'screenshots':record['screenshots']}))
