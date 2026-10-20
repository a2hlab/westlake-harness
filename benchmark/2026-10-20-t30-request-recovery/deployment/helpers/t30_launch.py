from pathlib import Path
import sys,json,time,shlex
from window_paths import WINDOW,context,budget,phase_limit,tag as safe_tag
repo=Path.cwd();base=WINDOW;c=context();phase,boot,tag=sys.argv[1:];safe_tag(tag);recovery=phase_limit(phase);deadline=time.monotonic()+budget(c,recovery);out=base/tag;out.mkdir(exist_ok=False)
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
class UI(b.Board):
 def command(self,argv,timeout=60):
  left=deadline-time.monotonic();assert left>0;return super().command(argv,min(timeout,left))
 def ready(self):
  super().ready();rc,h=self.command(self.lock+['held',self.serial],10);assert rc==0 and h.strip()==c['holder']
 def shell(self,cmd,required=True,timeout=60):
  assert time.monotonic()<deadline
  result=super().shell(cmd,required,min(timeout,20))
  if cmd.startswith('uitest '):
   super().shell('power-shell timeout -o 86400000',True,10)
   _,power=super().shell('power-shell dump -s',True,10);assert 'OverrideTimeout=86400000ms' in power
  return result
bd=UI(c['serial'],c['hdc'],'bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'inner(cx-seal)',out/'commands');bd.boot=boot;bd.ready();remote='/data/local/tmp/t30-'+tag+'-'+str(int(c['start']));bd.shell('mkdir '+remote);record=dict(key='toutiao',serial=c['serial'],boot=boot,action='single-normal-icon',screenshots=[])
try:
 b.desktop_launch(bd,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},remote,out,record)
 sys.path.insert(0,str(Path(__file__).parent)); import t30_quick_read
 if not recovery: t30_quick_read.collect(bd,out/'quick',boot,c)
 shot=b.capture(bd,remote+'/after-icon.jpeg',out/'after-icon.jpeg');shot['captured']=True;record['screenshots'].append(shot)
 for name,cmd in [('ps','ps -A -o PID,PPID,UID,NAME'),('windows',"hidumper -s WindowManagerService -a '-a'")]:
  _,raw=bd.shell(cmd);(out/(name+'.txt')).write_text(raw)
finally:b.save(out/'record.json',record)
print(json.dumps(record))
