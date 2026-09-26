from pathlib import Path
import sys,json,time,re,shlex
name,op=sys.argv[1:3];args=sys.argv[3:];p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];recv=x['recv'];rt=x['rt'];F='/data/local/tmp/operator45/selfheal48';Q='/data/local/tmp/operator45/speed50'
def save(n,s): (r/n).write_text(s);return s
def info():return json.loads((r/'instance.json').read_text())
def alive(d):
 s=x['state'](d['child']);return s and s['alive'] and s['birth']==d['birth']
if op=='start':
 arm=args[0];assert arm in ('base','speed')
 assert 'STOPPED' in dev('test -f '+F+'/stop && test ! -d '+F+'/lock && echo STOPPED',5)
 assert not dev('pidof com.ss.android.article.news appspawn-x',5).strip()
 save('preflight.txt',dev('cat /proc/uptime; free -m; cat /proc/meminfo; cat /proc/sys/vm/max_map_count',5))
 s=(x['ROOT'].parent/'2026-09-26-operator-selfheal48/scripts/watchdog.sh.in').read_text();fun=s.split('prepare_profile(){',1)[1].split('\narchive_exit(){',1)[0]
 setup='#!/system/bin/sh\nset -eu\nRUNTIME='+shlex.quote(rt)+'\nPKG=com.ss.android.article.news\nmode=fresh\nprepare_profile(){'+fun+'\nprepare_profile\necho 1048576 > /proc/sys/vm/max_map_count\npower-shell timeout -o 86400000\npower-shell wakeup\naa start -b org.westlake.imehost -a EntryAbility\n'
 setup=setup.replace('operator-selfheal-','operator-speed50-');(r/'prepare.sh').write_text(setup)
 dev('mkdir -p '+Q,5);x['hdc'](['file','send','prepare.sh',Q+'/prepare.sh'],r,10);save('prepare.txt',dev('/system/bin/sh '+Q+'/prepare.sh',30))
 src=x['R']/'preflight/run.sh';run=src.read_text();run,n=re.subn(r'^(?:export WESTLAKE_OH_JIT_FILE_CACHE_DIR=.*|unset WESTLAKE_OH_JIT_FILE_CACHE_DIR)$',"export WESTLAKE_OH_JIT_FILE_CACHE_DIR="+('/data/data/com.ss.android.article.news/code_cache/art-volatile' if arm=='speed' else "''"),run,flags=re.M);assert n==1
 (r/'run.sh').write_text(run);x['hdc'](['file','send','run.sh',rt+'/run.sh'],r,10)
 if arm=='speed':assert 'SPEED_PRESENT' in dev('test -f '+rt+'/oat/arm64/toutiao.odex && echo SPEED_PRESENT',5)
 else:assert 'NO_APP_AOT' in dev('test ! -f '+rt+'/oat/arm64/toutiao.odex && echo NO_APP_AOT',5)
 dev('rm -f '+x['c']['socket'],5);parent=int(dev(x['c']['parent_command'],8).strip())
 for _ in range(30):
  if 'READY' in dev('test -S '+x['c']['socket']+' && echo READY',5):break
  time.sleep(.2)
 else:raise RuntimeError('parent socket timeout')
 hook=p.with_name('prepare_jit50.sh');x['hdc'](['file','send',hook.name,rt+'/prepare_jit50.sh'],hook.parent,10)
 save('jit-prepare.txt',dev('/bin/nsenter -t '+str(parent)+' -m -- /system/bin/sh /data/local/tmp/asx/prepare_jit50.sh',8))
 spawn=save('spawn.txt',dev(x['c']['spawn_command'],10));child=int(re.search(r'result=0 pid=(\d+)',spawn)[1]);st=x['state'](child);assert st and st['alive'];d=dict(child=child,parent=parent,birth=st['birth'],arm=arm,host_start=time.monotonic());save('instance.json',json.dumps(d,indent=2))
 timer='sleep 300; v=$(cat /proc/'+str(child)+'/stat 2>/dev/null); rest=${v##*) }; set -- $rest; shift 19; if [ "$1" = "'+st['birth']+'" ]; then kill -9 '+str(child)+' '+str(parent)+'; fi'
 (r/'timer.sh').write_text('#!/system/bin/sh\n'+timer+'\n');x['hdc'](['file','send','timer.sh',Q+'/timer.sh'],r,5);save('timer.pid',dev('nohup /system/bin/sh '+Q+'/timer.sh >'+Q+'/timer.log 2>&1 </dev/null & echo $!',5))
 feed=0;last=0;consented=False;start=time.monotonic()
 while time.monotonic()-start<175:
  if not alive(d):raise RuntimeError('app died during bootstrap')
  out=dev('cat /proc/uptime; timeout 4 snapshot_display -t png -f '+Q+'/current.png >/dev/null; '+F+'/screen-gate '+Q+'/current.png',8);label=out.splitlines()[-1].strip()
  with (r/'bootstrap.jsonl').open('a') as f:f.write(json.dumps({'elapsed':time.monotonic()-start,'output':out})+'\n')
  if label in ('privacy','login') and time.monotonic()-last>10:
   coords='600 1273' if label=='privacy' else '55 92';save('action-'+str(int(time.monotonic()))+'.txt',dev('cat /proc/uptime; uinput -T -d '+coords+' -u '+coords,5));last=time.monotonic();consented=consented or label=='privacy'
  feed=feed+1 if label=='feed' and consented else 0
  if feed>=2:x['shot']('feed-gate');print('READY',json.dumps(d),flush=True);break
  time.sleep(3)
 else:raise RuntimeError('feed bootstrap timeout')
elif op=='shot':
 x['shot'](args[0])
elif op=='touch':
 d=info();assert alive(d);coords=' '.join(args);assert re.fullmatch(r'\d+ \d+',coords);print(dev('cat /proc/uptime; uinput -T -d '+coords+' -u '+coords,5))
elif op=='refresh':
 d=info();assert alive(d);print(dev('cat /proc/uptime; uinput -T -m 600 500 600 1550 500',5))
elif op=='click':
 d=info();assert alive(d);coords=' '.join(args);assert re.fullmatch(r'\d+ \d+',coords)
 gate=json.loads((r/'bootstrap.jsonl').read_text().splitlines()[-1]);gate_up=float(gate['output'].split()[0]);now=float(dev('cat /proc/uptime',5).split()[0]);time.sleep(max(0,gate_up+35-now));assert alive(d)
 out=save('input.txt',dev('cat /proc/uptime; uinput -T -d '+coords+' -u '+coords+'; cat /proc/uptime',5));print(out,flush=True);start=time.monotonic();samples=[]
 for target in [2,4,6,8,10,12,14,16,18,20,25,30,40,50,60]:
  time.sleep(max(0,target-(time.monotonic()-start)))
  if not alive(d):save('died-during-click.txt',dev('cat /proc/uptime',5));break
  before=dev('cat /proc/uptime',5);label='after-'+str(target);x['shot'](label,8);after=dev('cat /proc/uptime',5);samples.append(dict(label=label,before=before,after=after));save('frames.json',json.dumps(samples,indent=2))
 save('postclick-state.txt',dev('cat /proc/uptime; cat /proc/'+str(d['child'])+'/stat; free -m',5));recv(rt+'/private-tmp/adapter_child_'+str(d['child'])+'.stderr',r/'child.stderr',20)
elif op=='collect':
 d=info()
 while alive(d) and float(dev('cat /proc/uptime',5).split()[0])-int(d['birth'])/100<240:time.sleep(8)
 x['collect'](d['child']);raw=Q+'/maps';dev('cat /proc/'+str(d['child'])+'/maps > '+raw,5);recv(raw,r/'live.maps',8);save('final-state.txt',dev('cat /proc/uptime; cat /proc/'+str(d['child'])+'/stat; cat /proc/'+str(d['child'])+'/status; free -m',8))
 save('jit-stat.txt',dev('/bin/nsenter -t '+str(d['parent'])+' -m -- /system/bin/sh -c '+shlex.quote('stat -c "%u:%g:%a:%F" /data/data/com.ss.android.article.news/code_cache/art-volatile; test ! -L /data/data/com.ss.android.article.news/code_cache/art-volatile && echo NONSYMLINK'),8))
elif op=='cleanup':
 d=info();print(x['cleanup'](d['parent'],d['child']));
 if (r/'timer.pid').exists():dev('kill '+(r/'timer.pid').read_text().strip()+' 2>/dev/null',5)
else:raise SystemExit(op)
