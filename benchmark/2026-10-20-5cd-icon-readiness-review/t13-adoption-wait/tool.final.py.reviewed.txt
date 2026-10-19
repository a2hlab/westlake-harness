#!/usr/bin/env python3
"""T13 outer-only bounded control placement. Preview is the default."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from datetime import datetime
from pathlib import Path
from derive import *

def power(text):
 rows=re.findall(r'ScreenOffTime:\s*Timeout=(\d+)ms\s+OverrideTimeout=(-?\d+)ms',text)
 need(len(rows)==1,'power dump ambiguous');a,b=map(int,rows[0]);need(a>0 and b>=0,'power value');return {'timeout':a,'override':b}
def process_stat(text,pid):
 a,b=text.strip().rsplit(') ',1);f=b.split();need(int(a.split()[0])==pid and len(f)>=20 and f[0] not in ('Z','X'),'process stat')
 return {'pid':pid,'birth':int(f[19]),'ppid':int(f[1])}
def shell_guard():
 return f'''test "$(cat /proc/sys/kernel/random/boot_id)" = '{BOOT}';
r=$(cat /proc/{PARENT}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {BIRTH}; test "$1" != Z; test "$1" != X;
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{PARENT}/status); set -- $u; test "$#" = 4; test "$1" = "$2"; test "$1" = "$3"; test "$1" = "$4"; case "$1" in 0|{UID}) :;; *) exit 45;; esac;
test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/{PARENT}/status)" = 0;
e=$(sha256sum /proc/{PARENT}/exe); set -- $e; test "$1" = '{EXE_SHA}';
test "$(readlink /proc/{PARENT}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)";
test "$(stat -L -c '%d:%i' '{RUNTIME}/run.sh')" = "$(stat -L -c '%d:%i' /proc/{PARENT}/root/data/local/tmp/asx/run.sh)";
test "$(stat -c %u /data/app/el2/100/base/org.westlake.imehost)" = {UID};
'''
def implementation_pins():
 return {n:sha((HERE/n).read_bytes()) for n in ['derive.py','t12_derive.py','tool.py','ui.py','source-pins.json']}
def adoption_wait_budget(deadline,now):
 # Leave the existing 60-second recovery reserve plus 5 seconds for transport.
 budget=min(30,int(deadline-now-60-5))
 need(budget>=1,'no adoption observation budget before recovery reserve')
 return budget

def adoption_wait(root,guardian,budget):
 need(type(budget)==int and 1<=budget<=30,'bounded adoption wait')
 pid=guardian['pid'];birth=guardian['birth']
 need(type(pid)==int and pid>1 and type(birth)==int and birth>0,'guardian wait identity')
 return 'HERE='+shlex.quote(root)+'; . "$HERE/config-common.sh"; . "$HERE/launch-common.sh"; . "$HERE/adoption-guard.sh";\n'+f'''
read taw_up taw_rest < "$PROC/uptime"
taw_until=$((${{taw_up%%.*}}+{budget}))
while :; do
 t12_launch_guard
 [ "$(rb_birth {pid})" = {birth} ]
 [ "$(rb_uid {pid})" = 0:0:0:0 ]
 [ "$(readlink "$PROC/{pid}/exe")" = /system/bin/sh ]
 taw_cmd=$(timeout 2 strings "$PROC/{pid}/cmdline")
 [ "$taw_cmd" = "$(printf '/system/bin/sh\\n%s' "$HERE/entry.sh")" ] || [ "$taw_cmd" = "$(printf '/system/bin/sh\\n%s' "$HERE/watchdog.sh")" ]
 [ "$(rb_birth {pid})" = {birth} ]
 read taw_up taw_rest < "$PROC/uptime"
 [ "${{taw_up%%.*}}" -lt "$taw_until" ] || {{ echo ADOPTION_WAIT_EXPIRED >&2; exit 2; }}
 [ ! -L "$HERE/adopted" ]
 if [ -f "$HERE/adopted" ]; then
  t13_adoption_guard
  [ "$t13_gp:$t13_gb" = '{pid}:{birth}' ]
  cat "$HERE/adopted"
  break
 fi
 sleep 1
done
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['preflight','apply','stop','restore','refresh-awake','term-once'])
 ap.add_argument('--execute',action='store_true');ap.add_argument('--serial',default=SERIAL)
 ap.add_argument('--hdc',type=Path);ap.add_argument('--repo',type=Path,default=Path.cwd());ap.add_argument('--holder')
 ap.add_argument('--out',type=Path);ap.add_argument('--receipt',type=Path);ap.add_argument('--window-start',type=float)
 ap.add_argument('--exit-mode',choices=['natural','term-once'],default='natural')
 ap.add_argument('--root',default='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t13-window1')
 a=ap.parse_args();need(a.serial==SERIAL,'serial');sources()
 need(re.fullmatch('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t13-[a-z0-9-]+',a.root),'root')
 if not a.execute:
  print(json.dumps({'execute':False,'device_calls':0,'action':a.action,'serial':SERIAL,'root':a.root,'got':'disabled','needs_outer_review':True}));return 0
 need(a.hdc and a.hdc.is_file() and a.holder and a.out and a.window_start,'explicit execution context required')
 h=a.holder.split();need(len(h)==3 and h[1].isdigit(),'holder format')
 locked=datetime.fromisoformat(h[2]).timestamp();need(abs(a.window_start-locked)<1,'window-start must match holder ISO')
 age=time.time()-locked;recovery=a.action in ('stop','restore')
 need(age>=0 and (recovery or age<600),'600 second window')
 deadline=time.monotonic()+(60 if recovery else 600-age)
 out=a.out.resolve();need(not str(out).startswith('/tmp/'),'persistent evidence');out.mkdir(parents=True,exist_ok=False)
 receipt=json.loads(a.receipt.read_text()) if a.receipt else None
 if receipt:
  if not recovery:deadline=min(deadline,receipt['monotonic_deadline'])
  need(receipt['serial']==SERIAL and receipt['boot']==BOOT and receipt['root']==a.root and receipt['window_start']==a.window_start and receipt['holder']==a.holder,'receipt identity')
  if not recovery:need(receipt['exit_mode']==a.exit_mode and receipt['implementation_pins']==implementation_pins(),'mode/source receipt drift')
 result={'action':a.action,'serial':SERIAL,'boot':BOOT,'root':a.root,'window_start':a.window_start,'monotonic_deadline':deadline,'recovery_only':recovery,'holder':a.holder,'status':'UNKNOWN','device_commands':0,'exit_mode':a.exit_mode,'implementation_pins':implementation_pins(),'visual':'pending_review','playback':'unknown','audio':'unknown'}
 seq=0
 def run(argv,label,command_timeout=15,reserve=0):
  nonlocal seq
  seq+=1;p=out/f'{seq:03d}-{label}';p.with_suffix('.argv.json').write_text(json.dumps(argv)+'\n')
  left=deadline-time.monotonic()-reserve;need(left>0,'deadline/reserve; outer recovery required')
  try:r=subprocess.run(argv,capture_output=True,timeout=min(left,command_timeout))
  except subprocess.TimeoutExpired as ex:
   p.with_suffix('.stdout').write_bytes(ex.stdout or b'');p.with_suffix('.stderr').write_bytes(ex.stderr or b'');p.with_suffix('.rc.json').write_text('{"timeout":true}\n');raise
  p.with_suffix('.stdout').write_bytes(r.stdout);p.with_suffix('.stderr').write_bytes(r.stderr);p.with_suffix('.rc.json').write_text(json.dumps({'rc':r.returncode})+'\n');need(r.returncode==0,'transport '+label)
  return r.stdout.decode('utf8','replace')
 def remote(body,label,parent=True,command_timeout=15,reserve=0):
  held=run(['bash',str(a.repo.resolve()/'scripts/lab/board_note.sh'),'held',SERIAL],'lock',reserve=reserve);need(held.strip()==a.holder,'lock changed')
  guard=shell_guard() if parent else f'test "$(cat /proc/sys/kernel/random/boot_id)" = {BOOT};\n'
  marker='T13_RC_'+uuid.uuid4().hex
  s='( set -eu;\n'+guard+body+'\n'+guard+'printf "\\n'+marker+'=0\\n" )'
  text=run([str(a.hdc.resolve()),'-t',SERIAL,'shell',s],label,command_timeout=command_timeout,reserve=reserve);result['device_commands']+=1
  need(text.rstrip().endswith(marker+'=0'),'remote failure '+label);return text.rsplit(marker+'=0',1)[0].rstrip()
 def hashes():
  paths={CFG:CFG_SHA,RUNTIME+'/run.sh':RUN_SHA,RUNTIME+'/prepare_jit50.sh':JIT_SHA,STAGE+'/host_spawn':HOST_SHA,STAGE+'/request.bin':REQUEST_SHA,OLD+'/screen-gate':DECODER_SHA}
  for path,h in paths.items():need(remote('sha256sum '+shlex.quote(path),'pin').split()[0]==h,'deployed pin '+path)
 def processes():
  ps=remote('ps -A -o PID,PPID,UID,NAME','ps')
  for line in ps.splitlines():
   if 'com.ss.android.article.news' in line:need(line.split()[0]==str(CHILD),'unexpected child')
  remote(ownership_probe(),'exact-owned-child')
  args=remote('ps -A -o PID,PPID,UID,ARGS','args')
  for line in args.splitlines():
   t=line.split()
   if len(t)>=5 and t[0].isdigit() and len(t[3:])==2 and t[4].endswith(('/watchdog.sh','/watchdog-reentry.sh','/entry.sh')):raise ValueError('existing guardian or entry')
  return ps
 def read_power():return power(remote('power-shell dump -s','power',parent=False))
 try:
  if a.action=='preflight':
   hashes();processes()
   need(remote('cat '+shlex.quote(OLD+'/state'),'old-state')=='START_FAILED','old state changed')
   spawn=remote('cat '+shlex.quote(OLD+'/spawn.txt'),'old-spawn');need(spawn=='[TT-EXECUTOR] REFUSE FOREGROUND_HOST_NOT_READY','old failure changed')
   remote('test -S '+shlex.quote(SOCKET)+'; test ! -e '+shlex.quote(a.root)+'; test ! -L '+shlex.quote(a.root),'paths')
   env=remote(f'timeout 2 strings /proc/{PARENT}/environ','parent-env');wid=re.findall(r'^WL_PARENT_ID=(\d+)$',env,re.M);owners=re.findall(r'^ASX_RUNTIME_OWNER_UID=(\d+)$',env,re.M)
   need(len(wid)==1 and owners==[str(UID)],'parent environment')
   wm=remote("hidumper -s WindowManagerService -a '-a'",'windows');desktop=[];host=[]
   for line in wm.splitlines():
    t=line.split()
    if t and re.fullmatch(r'SCBDesktop\d+',t[0]):need(len(t)>=15,'desktop row');desktop.append(t)
    if t and t[0]=='imehost0':need(len(t)>=15,'host row');host.append(t)
   need(len(desktop)==1 and len(host)==1 and host[0][3]==wid[0],'host/desktop current windows')
   identities={}
   for role,row,cmd in [('desktop',desktop[0],'com.ohos.sceneboard'),('host',host[0],'org.westlake.imehost')]:
    pid=int(row[2]);st=process_stat(remote(f'cat /proc/{pid}/stat',role+'-stat'),pid)
    status=remote(f'cat /proc/{pid}/status',role+'-status');u=re.findall(r'^Uid:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',status,re.M);need(len(u)==1 and len(set(u[0]))==1,'window UID');uid=int(u[0][0]);need(uid==(UID if role=='host' else DESKTOP_UID),'window UID profile')
    need(remote(f'readlink /proc/{pid}/exe',role+'-exe')=='/system/bin/appspawn','window exe')
    exe_sha=remote(f'sha256sum /proc/{pid}/exe',role+'-exe-sha').split()[0];need(re.fullmatch('[0-9a-f]{64}',exe_sha),'window exe SHA')
    need(remote(f'timeout 2 strings /proc/{pid}/cmdline',role+'-cmdline')==cmd,'window cmdline')
    need(process_stat(remote(f'cat /proc/{pid}/stat',role+'-stat-end'),pid)==st,'window process drift');identities[role]={**st,'uid':uid,'wid':int(row[3]),'exe_sha256':exe_sha}
   old_sha={}
   for n in ('state','events.log','instance.txt','sequence','spawn.txt','parent-identity','parent-start.txt'):
    old_sha[n]=remote('sha256sum '+shlex.quote(OLD+'/'+n),'old-sha-'+n).split()[0]
   original=read_power();up=float(remote('cat /proc/uptime','uptime').split()[0]);left=deadline-time.monotonic();need(left>120,'recovery reserve')
   result.update({'status':'PREFLIGHT_ONLY_PENDING_REVIEW','old_controls_sha256':old_sha,'power_original':original,'windows':identities,'parent':{'pid':PARENT,'birth':BIRTH},'child':{'pid':CHILD,'birth':CHILD_BIRTH},'guardian_deadline_uptime':int(up+left-60),'pins':{'cfg':CFG_SHA,'run':RUN_SHA},'source_pins_sha':sha((HERE/'source-pins.json').read_bytes())})
  elif a.action=='apply':
   need(receipt and receipt['status']=='PREFLIGHT_ONLY_PENDING_REVIEW','preflight receipt required')
   need(receipt['source_pins_sha']==sha((HERE/'source-pins.json').read_bytes()),'source receipt drift');hashes();processes()
   need(read_power()==receipt['power_original'],'power preimage changed')
   up=float(remote('cat /proc/uptime','uptime').split()[0]);need(up+60<receipt['guardian_deadline_uptime']<=up+deadline-time.monotonic(),'deadline reserve or extension')
   payload=derive(a.root,receipt['windows']['desktop']['uid'],receipt['guardian_deadline_uptime'])
   (out/'payload').mkdir()
   for n,s in payload.items():(out/'payload'/n).write_text(s)
   result.update({'power_original':receipt['power_original'],'old_controls_sha256':receipt['old_controls_sha256'],'guardian_deadline_uptime':receipt['guardian_deadline_uptime'],'preflight_sha':sha(a.receipt.read_bytes()),'status':'APPLY_INTENT_RECOVERY_REQUIRED'})
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
   remote('power-shell timeout -o 86400000','awake',parent=False)
   actual=read_power();need(actual['override']==86400000 and actual['timeout']>0,'awake readback')
   remote('test ! -e '+shlex.quote(a.root)+'; test ! -L '+shlex.quote(a.root)+'; umask 077; mkdir '+shlex.quote(a.root),'mkdir')
   result['root_identity']=remote("stat -c '%d:%i:%u:%g:%a' "+shlex.quote(a.root),'root-identity');need(result['root_identity'].endswith(':0:0:700'),'root metadata')
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
   for n,s in payload.items():
    remote('test ! -e '+shlex.quote(a.root+'/'+n)+'; (set -C; printf %s '+shlex.quote(s)+' > '+shlex.quote(a.root+'/'+n)+'); chmod 500 '+shlex.quote(a.root+'/'+n),'place-'+n)
   remote('test "$(sha256sum '+shlex.quote(OLD+'/screen-gate')+' | cut -d\' \' -f1)" = '+DECODER_SHA+'; cp '+shlex.quote(OLD+'/screen-gate')+' '+shlex.quote(a.root+'/screen-gate')+'; chmod 500 '+shlex.quote(a.root+'/screen-gate'),'decoder-copy')
   for n,s in payload.items():need(remote('sha256sum '+shlex.quote(a.root+'/'+n),'verify-'+n).split()[0]==sha(s.encode()),'payload readback '+n)
   processes()
   text=remote('nohup /system/bin/sh '+shlex.quote(a.root+'/entry.sh')+' > '+shlex.quote(a.root+'/guardian.log')+' 2>&1 < /dev/null &\ngp=$!; printf "T13_GPID=%s\\n" "$gp"; cat /proc/$gp/stat','guardian-start')
   pid=int(re.search(r'T13_GPID=(\d+)',text).group(1));st=process_stat(text.split('\n',1)[1],pid)
   result['guardian']=st
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
   # Nohup is not ARMED: require the actual R2 instance and a live guardian.
   wait_budget=adoption_wait_budget(deadline,time.monotonic())
   result['adoption_wait_seconds']=wait_budget
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
   adopted=remote(adoption_wait(a.root,st,wait_budget),'adopted',command_timeout=wait_budget+5,reserve=60)
   need(adopted==f"{st['pid']} {st['birth']} {BOOT} {PARENT} {BIRTH} {CHILD} {CHILD_BIRTH} 1",'adoption guardian mismatch')
   remote(ownership_probe(),'armed-child-alive',reserve=60)
   result.update({'status':'ARMED_ADOPTED_CHILD','adopted':adopted,'child':{'pid':CHILD,'birth':CHILD_BIRTH},'payload_sha256':{n:sha(v.encode()) for n,v in payload.items()}})
  elif a.action=='term-once':
   need(receipt and receipt['status']=='ARMED_ADOPTED_CHILD' and receipt['exit_mode']=='term-once','armed term-once receipt required')
   need(receipt.get('root_identity') and receipt.get('adopted') and receipt.get('guardian'),'armed identity required')
   remote('test ! -L '+shlex.quote(a.root)+'; test "$(stat -c '+shlex.quote('%d:%i:%u:%g:%a')+' '+shlex.quote(a.root)+')" = '+shlex.quote(receipt['root_identity']),'root-guard')
   for n,h in receipt['payload_sha256'].items():
    need(remote('test ! -L '+shlex.quote(a.root+'/'+n)+'; sha256sum '+shlex.quote(a.root+'/'+n),'term-pin').split()[0]==h,'term payload drift '+n)
   need(remote('cat '+shlex.quote(a.root+'/adopted'),'term-adopted')==receipt['adopted'],'adopted drift')
   result.update({'status':'TERM_INTENT_OUTCOME_UNKNOWN','armed_receipt_sha256':sha(a.receipt.read_bytes())})
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
   remote('/system/bin/sh '+shlex.quote(a.root+'/term-once.sh'),'term-once')
   result['status']='TERM_SENT_EXIT_NOT_PROVEN' 
  elif a.action=='refresh-awake':
   need(receipt and 'power_original' in receipt,'receipt');remote('power-shell timeout -o 86400000','awake',parent=False)
   actual=read_power();need(actual['override']==86400000 and actual['timeout']>0,'awake readback');result['status']='AWAKE_ONLY'
  elif a.action=='stop':
   need(receipt and 'power_original' in receipt,'apply intent required')
   # Only this exact new attempt; preserve stop and all evidence.
   need(receipt.get('root_identity'),'root identity missing: reconcile required')
   remote('test ! -L '+shlex.quote(a.root)+'; test \"$(stat -c '+shlex.quote('%d:%i:%u:%g:%a')+' '+shlex.quote(a.root)+')\" = '+shlex.quote(receipt['root_identity']),'root-guard',parent=False)
   remote('if [ -d '+shlex.quote(a.root)+' ] && [ ! -L '+shlex.quote(a.root)+' ]; then test ! -L '+shlex.quote(a.root+'/stop')+'; printf "outer_stop\\n" > '+shlex.quote(a.root+'/stop')+'; fi','stop',parent=False)
   if receipt.get('guardian'):
    g=receipt['guardian'];pid=g['pid'];birth=g['birth']
    # TERM targets only the recorded shell PID. A changed process refuses; no group signal.
    body=f'''if [ -e /proc/{pid}/stat ]; then
r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {birth};
if [ "$1" != Z ]; then
c=$(timeout 2 strings /proc/{pid}/cmdline); test "$c" = "$(printf '/system/bin/sh\\n%s' '{a.root}/watchdog.sh')";
kill -TERM {pid};
fi
fi'''
    remote(body,'guardian-term',parent=False)
    # Bounded confirmation; no child/parent control.
    remote(f'for n in 1 2 3 4 5; do if [ ! -e /proc/{pid}/stat ]; then break; fi; r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {birth}; [ "$1" != Z ] || break; sleep 1; done; if [ -e /proc/{pid}/stat ]; then r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {birth}; test "$1" = Z; fi','guardian-stopped',parent=False)
   else:raise ValueError('guardian identity missing: outer must reconcile before stop complete')
   result.update({'status':'GUARDIAN_STOPPED_RESTORE_REQUIRED','power_original':receipt['power_original']})
  elif a.action=='restore':
   need(receipt and 'power_original' in receipt,'original power receipt required');original=receipt['power_original'];need(type(original['override'])==int and original['override']>=0,'original override')
   remote('power-shell timeout -o '+str(original['override']),'restore-awake',parent=False);need(read_power()==original,'restore readback')
   for path,h in {CFG:CFG_SHA,RUNTIME+'/run.sh':RUN_SHA,**{OLD+'/'+n:h for n,h in receipt.get('old_controls_sha256',{}).items()}}.items():
    need(remote('sha256sum '+shlex.quote(path),'close-unchanged',parent=False).split()[0]==h,'close preimage drift '+path)
   result.update({'status':'POWER_RESTORED_ONLY','power_original':original,'old_controls_verified':bool(receipt.get('old_controls_sha256'))})
  return 0
 except Exception as ex:
  result['error']=str(ex);result['status']='RECOVERY_REQUIRED' if a.action!='preflight' else 'PREFLIGHT_REFUSED';return 2
 finally:
  result['finished']=time.time();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':raise SystemExit(main())
