"""61b-only normal UI wrapper over unchanged BMS. No guardian/deployment control."""
import argparse,datetime,hashlib,importlib.util,json,re,shlex,sys,time
from pathlib import Path
SERIAL='61b0657200000000000000000324012c'
ROOT='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2'
CFG_SHA='91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e'
BMS_REL='benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
BMS_SHA='f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c'
EXE_SHA='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
RUNTIME='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def save(path,value):
 path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def power(text):
 rows=re.findall(r'ScreenOffTime:\s*Timeout=(\d+)ms\s+OverrideTimeout=(-?\d+)ms',text)
 need(len(rows)==1,'ambiguous power dump');a,b=map(int,rows[0]);need(a>0 and b>=0,'power values');return {'timeout':a,'override':b}
def validate(p):
 need(p['serial']==SERIAL and p['control_root']==ROOT and p['cfg_sha256']==CFG_SHA,'61b R2 authority')
 need(isinstance(p['state_dir'],str) and (p['state_dir'].startswith('~/') or Path(p['state_dir']).is_absolute()),'fixed evidence state directory')
 need(re.fullmatch('[0-9a-f-]{36}',p['boot']) and p['owner_uid']==20011206,'boot/UID')
 for role in ('parent','guardian'):
  need(all(type(p[role][k])==int and p[role][k]>1 for k in ('pid','birth')),'exact '+role)
 parts=p['holder'].split();need(len(parts)==3 and parts[0]=='outer(codex)' and parts[1].isdigit(),'exact holder')
 need(abs(datetime.datetime.fromisoformat(parts[2]).timestamp()-p['window_start'])<1,'lock start timestamp')
def active_guard(p):
 pp=p['parent']['pid'];pb=p['parent']['birth'];gp=p['guardian']['pid'];gb=p['guardian']['birth'];boot=p['boot'];f=ROOT+'/boots/'+boot
 return f'''test "$(cat /proc/sys/kernel/random/boot_id)" = {shlex.quote(boot)};
test "$(sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg | cut -d' ' -f1)" = {CFG_SHA};
test ! -e {ROOT}/stop; test ! -L {ROOT}/stop; test ! -e {f}/stop; test ! -L {f}/stop;
test "$(cat {f}/lock/owner)" = '{gp} {gb} {boot}';
r=$(cat /proc/{pp}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {pb}; test "$1" != Z; test "$1" != X;
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{pp}/status); set -- $u; test "$#" = 4; test "$1" = "$2"; test "$1" = "$3"; test "$1" = "$4"; case "$1" in 0|20011206) :;; *) exit 2;; esac;
test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/{pp}/status)" = 0;
test "$(sha256sum /proc/{pp}/exe | cut -d' ' -f1)" = {EXE_SHA};
test "$(readlink /proc/{pp}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)";
own=$(stat -L -c '%d:%i' {RUNTIME}/run.sh); view=$(stat -L -c '%d:%i' /proc/{pp}/root/data/local/tmp/asx/run.sh); test -n "$own"; test "$own" = "$view";
test "$(stat -c %u /data/app/el2/100/base/org.westlake.imehost)" = 20011206;
r=$(cat /proc/{gp}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {gb}; test "$1" != Z; test "$1" != X;
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{gp}/status); set -- $u; test "$#" = 4; test "$1:$2:$3:$4" = 0:0:0:0;
test "$(readlink /proc/{gp}/exe)" = /system/bin/sh;
test "$(timeout 2 strings /proc/{gp}/cmdline)" = "$(printf '/system/bin/sh\\n%s' '{f}/watchdog.sh')";
r=$(cat /proc/{pp}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {pb};
r=$(cat /proc/{gp}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {gb};
'''
def load_bms(repo):
 path=repo/BMS_REL;need(sha(path)==BMS_SHA,'BMS source changed')
 spec=importlib.util.spec_from_file_location('bms_reentry_ui',path);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);return b

def board_class(b):
 class UI(b.Board):
  def command(self,argv,timeout=60):
   left=min(self.deadline-time.monotonic(),self.wall_deadline-time.time())
   if left<=0:raise b.BatchStop('UI/recovery budget elapsed')
   try:return super().command(argv,min(timeout,left))
   except b.BatchStop as error:
    # Original BMS preserves .error.txt; retain timeout partial streams too (T14 pattern).
    cause=error.__cause__
    if cause is not None and hasattr(cause,'stdout'):
     prefix=self.out/f'command-{self.index:05d}'
     for suffix,value in (('.stdout.txt',cause.stdout),('.stderr.txt',getattr(cause,'stderr',None))):
      prefix.with_suffix(suffix).write_bytes(value.encode() if isinstance(value,str) else value or b'')
    raise
  def ready(self):
   super().ready()
   rc,holder=self.command(self.lock+['held',SERIAL],10)
   if rc or holder.strip()!=self.profile['holder']:raise b.BatchStop('exact holder changed')
  def refresh_awake(self):
   super().shell('power-shell timeout -o 86400000',True,10)
   rc,text=super().shell('power-shell dump -s',True,10)
   actual=power(text)
   need(actual=={'timeout':self.original_power['timeout'],'override':86400000},'temporary awake readback')
   self.record.setdefault('awake_readbacks',[]).append(actual);save(self.record_path,self.record)
  def shell(self,cmd,required=True,timeout=60):
   ui='uitest ' in cmd
   need(not (self.recovery and ui),'restore cannot input UI')
   if ui:
    selected=self.record.get('selected_icon')
    is_icon=self.action=='launch' and selected and cmd=='uitest uiInput click %d %d'%tuple(selected['center'])
    if is_icon:
     # Persistent intent is before the only icon dispatch, including lost replies.
     with (self.state/'icon-dispatch.intent.json').open('x') as f:json.dump({'command':cmd,'started':time.time(),'profile_sha256':self.profile_sha},f)
    entry={'command':cmd,'attempted':True,'result':'unknown'}
    self.record.setdefault('ui_calls',[]).append(entry);save(self.record_path,self.record)
   dispatch=cmd if self.recovery else '(set -eu; '+active_guard(self.profile)+cmd+')'
   result=super().shell(dispatch,required,timeout)
   if ui:
    entry.update(result='completed' if result[0]==0 else 'failed',remote_rc=result[0])
    if result[0]==0 and is_icon:self.record.update(clicked=True,clicked_at=time.time(),click_monotonic=time.monotonic())
    save(self.record_path,self.record)
    if result[0]==0:self.refresh_awake()
   return result
 return UI

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['preflight','prepare','launch','capture','restore'])
 ap.add_argument('--profile',type=Path,required=True);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--state',type=Path,required=True);ap.add_argument('--hdc',required=True);ap.add_argument('--tag');ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 p=json.loads(a.profile.read_text());validate(p);profile_sha=sha(a.profile);tag=a.tag or a.action
 need(re.fullmatch('[a-z0-9-]+',tag),'output tag')
 if not a.execute:print(json.dumps({'execute':False,'device_calls':0,'serial':SERIAL,'action':a.action,'profile_sha256':profile_sha}));return 0
 state=a.state.resolve();need(state==Path(p['state_dir']).expanduser().resolve(),'profile state directory');need(not str(state).startswith(('/tmp/','/private/tmp/')),'persistent state required')
 recovery=a.action=='restore';now=time.time();age=now-p['window_start'];need(age>=0,'future window')
 if a.action=='preflight':
  need(age<540,'active window exhausted');state.mkdir(parents=True,exist_ok=False)
  auth={'profile_sha256':profile_sha,'profile':p,'state_dir':str(state),'monotonic_deadline':time.monotonic()+600-age,'status':'PREFLIGHT_INCOMPLETE'}
  save(state/'authority.json',auth)
 else:
  auth=json.loads((state/'authority.json').read_text())
  need(auth['profile_sha256']==profile_sha and auth['profile']==p and auth['state_dir']==str(state),'same authority required')
  need(auth['status']=='PREFLIGHT_READONLY' and 'power_original' in auth,'power preimage receipt required')
  if not recovery:need(age<540,'active window exhausted')
 out=state/tag;out.mkdir(exist_ok=False)
 b=load_bms(a.repo.resolve());UI=board_class(b)
 board=UI(SERIAL,a.hdc,'bash '+shlex.quote(str(a.repo.resolve()/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands')
 board.profile=p;board.profile_sha=profile_sha;board.state=state;board.boot=p['boot'];board.action=a.action;board.recovery=recovery
 # Normal actions end at 540s; restore has the final minute, or a bounded emergency minute.
 board.deadline=min(auth['monotonic_deadline'],time.monotonic()+60) if recovery and age<600 else time.monotonic()+60 if recovery else auth['monotonic_deadline']-60
 board.wall_deadline=min(p['window_start']+600,now+60) if recovery and age<600 else now+60 if recovery else p['window_start']+540
 board.original_power=auth.get('power_original');board.record_path=out/'record.json'
 record={'serial':SERIAL,'boot_id':p['boot'],'key':'toutiao','package':'org.westlake.imehost','action':a.action,'profile_sha256':profile_sha,'screenshots':[],'status':'STARTED','recovery_only':recovery,'playback':'unknown'};board.record=record
 remote='/data/local/tmp/61b-r2-ui-'+str(int(p['window_start']))+'-'+tag
 try:
  board.ready()
  if a.action=='preflight':
   rc,text=board.shell('power-shell dump -s');(out/'power-before.txt').write_text(text+'\n');original=power(text)
   auth.update(power_original=original,status='PREFLIGHT_READONLY');save(state/'authority.json',auth);record['status']='PREFLIGHT_READONLY';return 0
  if recovery:
   # No child, parent, guardian, cfg, STOP or runtime dependency for power recovery.
   board.shell('power-shell timeout -o '+str(board.original_power['override']))
   rc,text=board.shell('power-shell dump -s');(out/'power-after.txt').write_text(text+'\n')
   need(power(text)==board.original_power,'original power readback');record['status']='POWER_RESTORED';return 0
  board.refresh_awake();board.shell('mkdir -p '+shlex.quote(remote))
  if a.action=='prepare':
   board.shell('power-shell wakeup');tree=b.layout(board,remote,out,'unlock-layout')
   ids=[str(x.get('id') or x.get('key') or '') for x in b.attributes(tree)]
   if any('ScreenLockRootComponent' in x for x in ids):
    panel=b.panel(tree,None);need(panel is not None,'screen geometry');x1,y1,x2,y2=panel
    board.shell(f'uitest uiInput swipe {(x1+x2)//2} {y2-(y2-y1)//10} {(x1+x2)//2} {y1+(y2-y1)//5}')
   board.shell('uitest uiInput keyEvent Home');record['launcher_focus_gate']=b.launcher_focused(board)
  elif a.action=='launch':
   with (state/'launch.intent.json').open('x') as f:json.dump({'started':time.time(),'profile_sha256':profile_sha,'maximum_icon_dispatches':1},f)
   b.desktop_launch(board,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},remote,out,record)
  shot=b.capture(board,remote+'/screen.jpeg',out/'screen.jpeg');shot['captured']=True;record['screenshots'].append(shot)
  for name,cmd in [('processes','ps -A -o PID,PPID,UID,NAME'),('windows',"hidumper -s WindowManagerService -a '-a'"),('guardian','cat '+ROOT+'/boots/'+p['boot']+'/instance.txt; tail -n 15 '+ROOT+'/boots/'+p['boot']+'/events.log')]:
   rc,text=board.shell(cmd);(out/(name+'.txt')).write_text(text+'\n')
  record['status']='OBSERVATION_REQUIRES_VISUAL_REVIEW';return 0
 except Exception as ex:
  record.update(status='RESTORE_REQUIRED' if not recovery else 'RECOVERY_REQUIRED',error=str(ex));return 2
 finally:save(board.record_path,record);print(json.dumps(record))
if __name__=='__main__':raise SystemExit(main())
