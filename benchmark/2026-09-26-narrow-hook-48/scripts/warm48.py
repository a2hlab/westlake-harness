"""One original app, no restarting guardian. Mac-side HDC deadline plus one-shot board kill timer."""
import pathlib,subprocess,json,sys,os,signal,time,re,base64,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
S='61b0657200000000000000000324012c';PKG='com.ss.android.article.news';D='/data/local/tmp/operator45'
R=pathlib.Path.home()/'a2hlab/board'/S/'narrow48';R.mkdir(exist_ok=True)
name,op=sys.argv[1:3];assert re.fullmatch(r'[a-z0-9-]+',name)
r=R/name
c=json.loads((R.parent/'isolated48/config.json').read_text());rt=c['runtime'];stage=c['stage']
def hdc(args,cwd=None,timeout=55):
 cwd=pathlib.Path(cwd or R).resolve();mac_cwd=str(cwd) if str(cwd).startswith('/Users/') else '/Users/zhaoyue/OrbStack/a2hlab'+str(cwd)
 j=base64.b64encode(json.dumps(dict(serial=S,args=args,cwd=mac_cwd,timeout=timeout)).encode()).decode()
 p=subprocess.Popen(['mac','bash','-c','exec /usr/bin/python3 -c "$1" "$2"','bash',(ROOT/'scripts/hdc_timeout_host.py').read_text(),j],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 try:raw=p.communicate(timeout=min(timeout,55)+4)[0]
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL)
  try:p.communicate(timeout=1)
  except subprocess.TimeoutExpired:pass
  raise TimeoutError('VM proxy timed out: '+str(args[:2]))
 out=raw.decode(errors='replace').replace('\r','')
 with (R/'operations.jsonl').open('a') as f:f.write(json.dumps(dict(epoch=time.time(),args=args,rc=p.returncode,output=out))+'\n')
 if p.returncode==124 or 'HDC_HARD_TIMEOUT' in out:raise TimeoutError('Mac HDC timed out: '+str(args[:2]))
 if p.returncode or '[Fail]' in out:raise RuntimeError(out[-2000:])
 return out
def dev(cmd,timeout=55):return hdc(['shell',cmd],timeout=timeout)
def recv(remote,path,timeout=55):path.parent.mkdir(parents=True,exist_ok=True);hdc(['file','recv',remote,path.name],path.parent,timeout)
def state(pid):
 s=dev('cat /proc/'+str(pid)+'/stat 2>/dev/null',10).strip()
 if ') ' not in s:return None
 f=s.rsplit(') ',1)[1].split();return {'birth':f[19],'alive':f[0]!='Z','raw':s}
def shot(label,timeout=12):
 q='/data/local/tmp/bounded48-'+name+'.jpeg';dev('snapshot_display -f '+q+' >/dev/null',timeout);recv(q,r/(label+'.jpeg'),timeout)
 p=ROOT/'preview'/name/(label+'.jpeg');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/(label+'.jpeg')).read_bytes());print('SHOT',p,flush=True)
def cleanup(parent=None,child=None):
 # No restart is possible: shared stop marker remains present throughout these rounds.
 cmd='touch '+D+'/stop; '
 if child:cmd+='kill -9 '+str(child)+' 2>/dev/null; '
 if parent:cmd+='kill -9 '+str(parent)+' 2>/dev/null; '
 cmd+='for p in $(pidof '+PKG+' appspawn-x); do kill -9 "$p"; done; '
 cmd+='sleep 1; echo APP_PIDS; pidof '+PKG+'; echo APPSPAWN_PIDS; pidof appspawn-x; echo MEMORY; free -m; cat /proc/meminfo'
 s=dev(cmd,12);(r/'cleanup.txt').write_text(s)
 assert not s.split('APP_PIDS\n',1)[1].split('APPSPAWN_PIDS',1)[0].strip(),s
 assert not s.split('APPSPAWN_PIDS\n',1)[1].split('MEMORY',1)[0].strip(),s
 available=int(re.search(r'MemAvailable:\s+(\d+)',s)[1]);assert available>1024*1024,'less than 1GiB available after cleanup'
 return available
def collect(child):
 recv(rt+'/private-tmp/adapter_child_'+str(child)+'.stderr',r/'child.stderr',20)
 recv(stage+'/parent.log',r/'parent.log',15)
 paths=dev('find '+rt+'/private-tmp/crash42 -type f -name "event-'+format(child,'x')+'-*"; find /data/log/faultlog -type f -name "*-'+str(child)+'-*" 2>/dev/null',10)
 (r/'fault-paths.txt').write_text(paths)
 for p in paths.splitlines():
  if p.startswith(rt+'/private-tmp/crash42/') or p.startswith('/data/log/faultlog/'):recv(p,r/'faults'/p.rsplit('/',1)[-1],15)
if op in ('run','auto','confirm','confirm-warm'):
 assert not r.exists();r.mkdir();result={'round':name,'restart_guardian':False,'max_observation_s':245,'board_kill_deadline_s':250,'failure':None};parent=None;child=None
 try:
  pre=dev('touch '+D+'/stop; echo APP_PIDS; pidof '+PKG+'; echo APPSPAWN_PIDS; pidof appspawn-x; echo MEMORY; free -m; cat /proc/meminfo',12)
  (r/'preflight.txt').write_text(pre)
  assert not pre.split('APP_PIDS\n',1)[1].split('APPSPAWN_PIDS',1)[0].strip(),'app already exists'
  assert not pre.split('APPSPAWN_PIDS\n',1)[1].split('MEMORY',1)[0].strip(),'appspawn already exists'
  result['mem_available_before_kib']=int(re.search(r'MemAvailable:\s+(\d+)',pre)[1]);assert result['mem_available_before_kib']>1024*1024
  sys.path.insert(0,str(ROOT.parent/'2026-09-26-operator-isolated-48/scripts'))
  from deploymentrefined48 import EXPECTED
  expected=dict(EXPECTED);expected['webview-t-lib/libwebview_bionic_shim.so']='dc4f5e6fd66fa8e6793d1c0d181b1436b743669534d1fd311f7724e77da61e35';expected['libart.so']='78e344455ec300f70106a7fcceafeff26f4b768f17b0c116927dc8848676f3bc'
  hashes=dev('sha256sum '+' '.join(rt+'/'+p for p in expected),20);(r/'component-hashes.txt').write_text(hashes)
  for p,v in expected.items():assert v+'  '+rt+'/'+p in hashes,p
  if op!='confirm-warm':
   profile=rt+'/profile-backups/bounded48-'+name
   dev('test ! -e '+profile+' || exit 9; mkdir -p '+profile+'; '+ '; '.join('if [ -d '+rt+'/'+p+' ]; then mv '+rt+'/'+p+' '+profile+'/'+p+'; fi' for p in ('app-data','data','webview-t-data'))+'; echo PROFILE_READY',20)
  s=dev(f'mkdir -p {rt}/data/dalvik-cache/arm64 {rt}/app-data/{PKG}/code_cache {rt}/app-data/{PKG}/app_webview {rt}/app-data/org.westlake.imehost {rt}/webview-t-data; chown -R 20010053:20010053 {rt}/data {rt}/app-data {rt}/webview-t-data; chcon -R u:object_r:data_app_el2_file:s0 {rt}/app-data/{PKG}; echo 1048576 > /proc/sys/vm/max_map_count; power-shell timeout -o 86400000; power-shell wakeup; aa start -b org.westlake.imehost -a EntryAbility; rm -f '+c['socket']+'; cat /proc/sys/vm/max_map_count',20)
  (r/'setup.txt').write_text(s);assert '1048576' in s
  parent=int(dev(c['parent_command'],10).strip());result['parent']=parent
  ready=time.monotonic()+30
  while 'READY' not in dev('if [ -S '+c['socket']+' ]; then echo READY; fi',5):
   assert time.monotonic()<ready,'parent socket timeout';time.sleep(.5)
  child=int(re.search(r'result=0 pid=(\d+)',dev(c['spawn_command'],10))[1]);started=time.monotonic();birth=state(child)['birth']
  result.update(child=child,birth=birth,started_epoch=time.time(),deadline_epoch=time.time()+245)
  (r/'instance.json').write_text(json.dumps(result,indent=2))
  # This one-shot timer only terminates this PID/birth and parent; it never restarts anything.
  parent_birth=state(parent)['birth']
  timer='sleep 248; set -- $(cat /proc/'+str(child)+'/stat 2>/dev/null); if [ "$1" = "'+str(child)+'" ]; then shift 21; if [ "$1" = "'+birth+'" ]; then echo DEADLINE_KILL; kill -9 '+str(child)+' '+str(parent)+'; fi; fi; set -- $(cat /proc/'+str(parent)+'/stat 2>/dev/null); if [ "$1" = "'+str(parent)+'" ]; then shift 21; if [ "$1" = "'+parent_birth+'" ]; then kill -9 '+str(parent)+'; fi; fi'
  q=__import__('shlex').quote
  result['deadline_timer']=dev('nohup /system/bin/sh -c '+q(timer)+' >'+D+'/bounded48-'+name+'-deadline.log 2>&1 </dev/null & echo $!',5).strip()
  fd=dev('ls -l /proc/'+str(child)+'/fd',5);(r/'recorder-fd.txt').write_text(fd);assert '/private-tmp/crash42' in fd
  print('ROUND_STARTED',name,child,parent,flush=True);last=-1;observed_alive=True;next_dialog_check=15;auto_clicked=False;consented=(op=='confirm-warm')
  while True:
   elapsed=time.monotonic()-started
   if elapsed>=240:break
   timeout=max(1,min(10,240-elapsed))
   s=dev('cat /proc/uptime; cat /proc/'+str(child)+'/stat; cat /proc/meminfo; pidof '+PKG,timeout)
   with (r/'samples.jsonl').open('a') as f:f.write(json.dumps({'elapsed':elapsed,'output':s})+'\n')
   rows=s.splitlines();st=next((x for x in rows if x.startswith(str(child)+' (')),None)
   observed_alive=bool(st and st.rsplit(') ',1)[1].split()[0]!='Z' and st.rsplit(') ',1)[1].split()[19]==birth)
   if not observed_alive:result['failure']='original exited during observation';break
   if (op=='auto' or (op=='confirm' and not consented)) and not auto_clicked and elapsed>=next_dialog_check and elapsed<130:
    from privacy_dialog import privacy_dialog, feed_ready
    label=('feed-gate-' if consented else 'consent-gate-')+str(int(elapsed));shot(label,5);next_dialog_check=elapsed+(3 if consented else 10)
    matched=feed_ready(r/(label+'.jpeg')) if consented else privacy_dialog(r/(label+'.jpeg'))
    with (r/'visual-gate.jsonl').open('a') as f:f.write(json.dumps({'elapsed':elapsed,'image':label+'.jpeg','gate':'feed' if consented else 'privacy','matched':matched})+'\n')
    if matched:
     for xy in (('380 410',) if consented else ('600 1273',)):
      cmd='cat /proc/uptime; uinput -T -d '+xy+' -u '+xy
      out=dev(cmd,5)
      with (r/'inputs.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'command':cmd,'output':out,'source':'visual-gated automatic real uinput'})+'\n')
      time.sleep(.7)
     if consented:
      auto_clicked=True;result['automatic_input_elapsed']=time.monotonic()-started;print('AUTO_ARTICLE_UINPUT',name,result['automatic_input_elapsed'],flush=True)
     else:
      consented=True;next_dialog_check=time.monotonic()-started+3;print('AUTO_CONSENT_UINPUT',name,flush=True)
   interval=10 if op in ('confirm','confirm-warm') and consented else 40
   if int(elapsed)//interval>last and elapsed<230:last=int(elapsed)//interval;shot('during-'+str(last*interval),min(5,max(1,(238-elapsed)/2)))
   if elapsed>230 and not result.get('final_shot'):shot('before-cleanup',3);result['final_shot']=True
   for second in (20,60,190):
    mark='maps'+str(second)
    if elapsed>second and mark not in result:
     remote='/data/local/tmp/narrow48-'+name+'-'+mark+'.maps'
     dev('cat /proc/'+str(child)+'/maps > '+remote,5);recv(remote,r/(mark+'.maps'),8)
     content=(r/(mark+'.maps')).read_text();result[mark]={'bytes':len(content),'lines':len(content.splitlines()),'valid':len(content.splitlines())>100 and '[stack]' in content}
   time.sleep(min(3,max(0,240-(time.monotonic()-started))))
  result.update(observed_seconds=time.monotonic()-started,alive_before_cleanup=observed_alive,cleanup_reason='scheduled bounded termination' if observed_alive else 'original already exited')
 except Exception as e:
  result['failure']=type(e).__name__+': '+str(e);print('ROUND_FAILURE',result['failure'],flush=True)
 finally:
  # Cleanup precedes collection: evidence download must never prolong a live test or spawn replacements.
  try:result['mem_available_after_kib']=cleanup(parent,child)
  except Exception as e:result['cleanup_failure']=repr(e)
  if child:
   try:collect(child)
   except Exception as e:result['collection_failure']=repr(e)
  result['end_epoch']=time.time();(r/'result.json').write_text(json.dumps(result,indent=2));print('ROUND_RESULT',json.dumps(result),flush=True)
elif op in ('input','article'):
 d=json.loads((r/'instance.json').read_text());assert time.time()<d['deadline_epoch']-10,'window ended';st=state(d['child']);assert st and st['alive'] and st['birth']==d['birth']
 xy=sys.argv[3:];assert len(xy)==2 and all(x.isdigit() for x in xy)
 cmd='cat /proc/uptime; uinput -T -d '+' '.join(xy)+' -u '+' '.join(xy);s=dev(cmd,5)
 with (r/'inputs.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'command':cmd,'output':s,'operation':op})+'\n')
 print(s,flush=True)
 if op=='article':
  clicked=time.monotonic();time.sleep(10);shot('article-after-10s',3)
  (r/'article-capture-time.json').write_text(json.dumps({'command':cmd,'click_output':s,'after_command_return_s':time.monotonic()-clicked},indent=2))
elif op=='shot':shot(sys.argv[3],5)
elif op=='timeout-test':
 r.mkdir(exist_ok=True);start=time.monotonic()
 try:
  dev('sleep 3',.3);raise AssertionError('timeout did not fire')
 except TimeoutError as e:
  elapsed=time.monotonic()-start;assert elapsed<5,elapsed
  (r/'timeout-selftest.json').write_text(json.dumps({'expected_timeout':True,'elapsed':elapsed,'message':str(e)},indent=2));print('TIMEOUT_TEST_PASS',elapsed)
else:raise SystemExit(op)
