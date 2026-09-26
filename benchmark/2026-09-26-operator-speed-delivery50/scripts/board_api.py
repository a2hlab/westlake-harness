"""One original app, no restarting guardian. Mac-side HDC deadline plus one-shot board kill timer."""
import pathlib,subprocess,json,sys,os,signal,time,re,base64,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
S='61b0657200000000000000000324012c';PKG='com.ss.android.article.news';D='/data/local/tmp/operator45'
R=pathlib.Path.home()/'a2hlab/board'/S/'speed-delivery50';R.mkdir(exist_ok=True)
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
