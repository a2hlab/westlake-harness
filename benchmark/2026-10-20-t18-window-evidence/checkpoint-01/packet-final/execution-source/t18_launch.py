from pathlib import Path
import sys,json,time,shlex
repo=Path.cwd();base=Path(__file__).parent/'t18-5cd-window-01';c=json.loads((base/'context.json').read_text());boot,tag=sys.argv[1:];out=base/tag;out.mkdir(exist_ok=False);assert time.time()-c['start']<1500
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
class UI(b.Board):
 def ready(self):
  super().ready();rc,h=self.command(self.lock+['held',self.serial],10);assert rc==0 and h.strip()==c['holder']
 def shell(self,cmd,required=True,timeout=60):
  assert time.time()-c['start']<1700
  result=super().shell(cmd,required,min(timeout,20))
  if cmd.startswith('uitest '):
   super().shell('power-shell timeout -o 86400000',True,10)
   _,power=super().shell('power-shell dump -s',True,10);assert 'OverrideTimeout=86400000ms' in power
  return result
bd=UI(c['serial'],c['hdc'],'bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');bd.boot=boot;bd.ready();remote='/data/local/tmp/t17-'+tag+'-'+str(int(c['start']));bd.shell('mkdir '+remote);record=dict(key='toutiao',serial=c['serial'],boot=boot,action='single-normal-icon',screenshots=[])
try:
 b.desktop_launch(bd,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},remote,out,record)
 shot=b.capture(bd,remote+'/after-icon.jpeg',out/'after-icon.jpeg');shot['captured']=True;record['screenshots'].append(shot)
 for name,cmd in [('ps','ps -A -o PID,PPID,UID,NAME'),('windows',"hidumper -s WindowManagerService -a '-a'")]:
  _,raw=bd.shell(cmd);(out/(name+'.txt')).write_text(raw)
finally:b.save(out/'record.json',record)
print(json.dumps(record))
