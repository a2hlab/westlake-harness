"""One fresh-data AOT trial, physical input, bounded observation, owned-process cleanup."""
from board42 import *
name,arm=sys.argv[1:3]
if arm not in ('baseline','verify','speed') or not re.fullmatch(r'[a-z0-9-]+',name):raise ValueError('Bad arm/name')
r=R/name
if r.exists():raise ValueError('New trial required')
before=exclusive()
reference=R.parents[1]/'5ea34a4500000000000000001123012c/ability38/idle-a1/launch-config.json'
config=json.loads(reference.read_text());cmd=config['argv']
for flag,value in [('--serial',S),('--out',str(r)),('--framework-report',str(R/('framework-'+arm)/'device-report.json'))]:cmd[cmd.index(flag)+1]=value
origin=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--origin=')),None)
if origin:
 old=R/origin
 d=json.loads((old/'device-report.json').read_text());runtime=d['runtime']
 if not runtime.startswith('/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-'):raise ValueError('Not an owned runtime')
 if json.loads((old/'arm.json').read_text())['arm']!=arm:raise ValueError('Cross-arm restart forbidden')
 r.mkdir()
 if dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name).strip():raise RuntimeError('Runtime still mounted by live process')
 uid=d['uid'];pkg='com.ss.android.article.news'
 # Reset only our HAP between trials, preventing a stale host IME/focus state.
 dev('aa force-stop org.westlake.imehost');dev('aa start -b org.westlake.imehost -a EntryAbility')
 for _ in range(60):
  try:
   host_pid=int(dev('pidof org.westlake.imehost').strip())
   window_state=json.loads(dev(f'cat /proc/{host_pid}/root/data/storage/el2/base/haps/entry/files/window-state.json'))
   detail=window_state['details'];window=int(detail.get('window',detail)['id'])
   if window>0:break
  except (ValueError,KeyError,RuntimeError):pass
  time.sleep(.25)
 else:raise RuntimeError('Fresh host window unavailable')
 d['window']=window;d['host_pid']=host_pid
 dev(f"sed -i 's/^export WL_PARENT_ID=.*/export WL_PARENT_ID={window}/' {runtime}/run.sh")

 dev(f'cd {runtime} && rm -rf app-data data webview-t-data && mkdir -p data/dalvik-cache/arm64 app-data/{pkg}/code_cache/art-volatile app-data/{pkg}/app_webview app-data/org.westlake.imehost webview-t-data && chown -R {uid}:{uid} data app-data webview-t-data && chcon -R u:object_r:data_app_el2_file:s0 app-data/{pkg}',120)
 rows=[json.loads(line) for line in (old/'commands.jsonl').read_text().splitlines()]
 dev('rm -f '+d['socket']);exclusive()
 launch=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
 d['parent']=int(dev(launch).strip())
 for _ in range(120):
  if 'READY' in dev('if [ -S '+d['socket']+' ]; then echo READY; fi'):break
  time.sleep(.25)
 else:raise RuntimeError('Parent not ready')
 spawn=next(x['command'] for x in rows if '/host_spawn /dev/unix' in x['command'])
 d['child']=int(re.search(r'result=0 pid=(\d+)',dev(spawn))[1]);d['touch']={}
 box=f'/proc/{d["child"]}/root/data/local/tmp/noice_tap.{d["child"]}'
 dev(f': > {box}; chown {uid}:{uid} {box}; chmod 666 {box}; ln -sf {box} /data/local/tmp/noice_tap')
 (r/'device-report.json').write_text(json.dumps(d,indent=2));(r/'commands.jsonl').write_bytes((old/'commands.jsonl').read_bytes())
 (r/'data-provenance.json').write_text(json.dumps(dict(origin=origin,fresh=True,cleared=['app-data','data','webview-t-data']),indent=2))
else:
 with (R/(name+'.driver.log')).open('w') as f:
  p=subprocess.run(cmd,cwd=pathlib.Path.home()/'a2hlab/manifest',stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError('Probe failed; inspect own report before retry')
 d=json.loads((r/'device-report.json').read_text())
pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
(r/'preflight-processes.txt').write_text(before);(r/'launch-config.json').write_text(json.dumps(config,indent=2))
(r/'arm.json').write_text(json.dumps(dict(arm=arm,fresh_data=True,reference=str(reference)),indent=2))
tracked={}
def action(c,kind='observe',timeout=60):
 out=dev(c,timeout)
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps(dict(epoch=time.time(),kind=kind,command=c,output=out))+'\n')
 return out
def uptime():return float(action('cat /proc/uptime').split()[0])
def track(p):
 st=dev(f'cat /proc/{p}/stat 2>/dev/null')
 if ') ' in st:tracked[p]=st.rsplit(') ',1)[1].split()[19]
def shot(label):
 remote=d['stage']+'/aot42-'+label+'.jpeg'
 stamps=action('cat /proc/uptime; snapshot_display -f '+remote+' >/dev/null; cat /proc/uptime','SCREENSHOT_'+label)
 recv(remote,r/(label+'.jpeg'));return stamps
def vt(label):
 n=int(action('wc -l < '+log).strip())
 action('echo v > /data/local/tmp/noice_tap','VIEW_TREE');time.sleep(.5)
 raw=action(f'tail -n +{n+1} '+log+" | grep -E '^(VT|\\[INITCHILD-FAIL)' ")
 (r/(label+'.txt')).write_text(raw)
 return raw
for p in [d['child'],d['parent']]:track(p)
for p in d.get('touch',{}).get('forwarder_pid','').split():
 p=int(p)
 if dev(f'readlink /proc/{p}/exe').strip()==d['stage']+'/touchfwd':track(p);action(f'kill {p}','STOP_OWN_FORWARDER')
result=dict(protocol='consent+60s, fresh app data, physical article click',arm=arm,child=pid,consent=None,consent_inputs=[],touch=None,detail_observations=[],outcome='not_measured')
try:
 action('power-shell wakeup','WAKE')
 action('cat /proc/uptime; ifconfig wlan0; ping -c 2 -W 2 1.1.1.1','NETWORK',20)
 (r/'maps-before.txt').write_text(action(f'cat /proc/{pid}/maps'))
 start=time.monotonic();ready=False;first_feed=None
 for step in range(90):
  raw=vt(f'poll-{step:02}')
  if '[INITCHILD-FAIL]' in raw or not dev(f'cat /proc/{pid}/stat 2>/dev/null').strip():result['outcome']='ui_exit_before_touch';break
  if re.search(r'"同意[^"]*"',raw) and (not result['consent_inputs'] or time.monotonic()-consent_time>15):
   found=list(re.finditer(r'rect=\[(\d+),(\d+) (\d+)x(\d+)\].*\"同意[^\"]*\"',raw))
   if found:
    index=len(result['consent_inputs']);shot('consent-'+str(index));print('CHECK_CONSENT_SCREENSHOT',name,index,flush=True)
    control=r/('consent-'+str(index)+'-xy')
    deadline=time.monotonic()+300
    while not control.exists():
     if time.monotonic()>deadline:raise RuntimeError('Consent screenshot not confirmed')
     time.sleep(.25)
    xy=control.read_text().strip()
    if not re.fullmatch(r'[0-9]+ [0-9]+',xy):raise ValueError('Bad consent coordinates')
    consent_input=action('cat /proc/uptime; uinput -T -d '+xy+' -u '+xy+'; cat /proc/uptime','CONSENT_UINPUT')
    result['consent_inputs'].append(consent_input)
    if result['consent'] is None:result['consent']=consent_input
    consent_time=time.monotonic();print('CONSENT',name,index,consent_input,flush=True)
  feed=not re.search(r'"同意[^"]*"',raw) and 'FeedCommonRecyclerView' in raw and ('FeedLightTextView' in raw or 'FeedTitleTextView' in raw)
  if feed and first_feed is None:
   first_feed=shot('first-feed');result['first_feed_screenshot_uptimes']=first_feed;print('FIRST_FEED',name,flush=True)
  if feed and result['consent'] is not None and time.monotonic()-consent_time>=30:
   ready=True;break
  if time.monotonic()-(consent_time if result['consent'] is not None else start)>150:break
  time.sleep(1)
 if ready:
  result['before_screenshot_uptimes']=shot('before');vt('before')
  print('CHECK_ARTICLE_SCREENSHOT',name,flush=True)
  deadline=consent_time+58
  while not (r/'article-xy').exists():
   if time.monotonic()>deadline:raise RuntimeError('Article screenshot not confirmed')
   time.sleep(.25)
  xy=(r/'article-xy').read_text().strip()
  if not re.fullmatch(r'[0-9]+ [0-9]+',xy):raise ValueError('Bad article coordinates')
  (r/'maps-before-touch.txt').write_text(action(f'cat /proc/{pid}/maps'))
  if time.monotonic()>consent_time+60:raise RuntimeError('Missed fixed 60-second click; exclude from latency comparison')
  time.sleep(max(0,consent_time+60-time.monotonic()))
  n=int(action('wc -l < '+log).strip())
  result['touch']=action('echo INPUT_BEFORE; cat /proc/uptime; uinput -T -d '+xy+' -u '+xy+'; echo INPUT_AFTER; cat /proc/uptime','ARTICLE_UINPUT')
  (r/'physical-result.txt').write_text(result['touch']);print('TOUCH',name,result['touch'],flush=True)
  begin=time.monotonic();shots=set();detail=False;last=0
  while time.monotonic()-begin<46:
   elapsed=time.monotonic()-begin
   fresh=action(f'cat /proc/uptime; tail -n +{n+1} '+log+" | grep -E '^\\[B47-SLA\\]|^\\[ABILITY38-(DISPATCH|FINISH)'",'LIFECYCLE_POLL')
   if re.search(r'^\[B47-SLA\] ENTRY .*NewDetailActivity',fresh,re.M) and not detail:
    detail=True;result['detail_observations'].append(dict(previous_poll=last,observed=fresh.splitlines()[0]));print('DETAIL',name,fresh[:250],flush=True)
   last=fresh.splitlines()[0] if fresh.splitlines() else None
   for target in [2,5,15,45]:
    if elapsed>=target and target not in shots:shot('after-'+str(target)+'s');shots.add(target)
   if not dev(f'cat /proc/{pid}/stat 2>/dev/null').strip():break
   time.sleep(.4)
  result['outcome']='detail_lifecycle_seen' if detail else 'no_detail_lifecycle'
  vt('after');(r/'maps-after.txt').write_text(action(f'cat /proc/{pid}/maps'))
 else:
  shot('not-ready')
  if result['outcome']=='not_measured':result['outcome']='no_eligible_feed'
except Exception as error:
 result['error']=str(error)
 result['outcome']='measurement_error'
 raise
finally:
 for key,path in [('child.stderr',log),('parent.log',d['stage']+'/parent.log'),('run.sh',d['runtime']+'/run.sh')]:
  try:recv(path,r/key)
  except Exception as error:(r/(key+'.error')).write_text(str(error))
 try:
  paths=action(f'find /data/log/faultlog -type f -name "*-{pid}-*"');(r/'fault-paths.txt').write_text(paths)
  for path in paths.splitlines():
   if path.startswith('/'):recv(path,r/pathlib.Path(path).name)
 finally:
  for p,start in tracked.items():
   st=dev(f'cat /proc/{p}/stat 2>/dev/null')
   if ') ' in st and st.rsplit(') ',1)[1].split()[19]==start:action(f'kill -9 {p}','STOP_OWN_PROCESS')
  (r/'after-processes.txt').write_text(dev('ps -A -o PID,PPID,NAME'))
  (r/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  print('COLLECTED_STOPPED',name,result['outcome'],flush=True)
