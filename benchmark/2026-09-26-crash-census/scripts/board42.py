"""VM driver using the Mac HDC wrapper; target fixed to the assigned board."""
import hashlib,json,pathlib,re,shlex,subprocess,sys,time
S='5cd1e3dd00000000000000000923012c'
H='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh'
A=pathlib.Path.home()/'a2hlab/ws'
R=pathlib.Path.home()/'a2hlab/board'/S/'crash42'
R.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dev(c,timeout=60):
 p=subprocess.run([H,'-t',S,'shell',c],capture_output=True,timeout=timeout)
 out=(p.stdout+p.stderr).decode(errors='replace').replace('\r','')
 with (R/'operations.jsonl').open('a') as f:f.write(json.dumps(dict(epoch=time.time(),command=c,output=out,rc=p.returncode))+'\n')
 if p.returncode or '[Fail]' in out:raise RuntimeError(out)
 return out
def exclusive():
 out=dev('ps -A -o PID,PPID,NAME')
 pids=dev('pidof dalvikvm dalvikvm64 linker64 com.ss.android.article.news appspawn-x; exit 0').strip()
 if pids:raise RuntimeError('Board busy (pidof): '+pids)
 bad=[s for s in out.splitlines() if re.search(r'\b(dalvikvm\w*|linker64|com\.ss\.android\.article\.news|appspawn-x)\s*$',s)]
 if bad:raise RuntimeError('Board busy; never kill other experiment: '+str(bad))
 return out
def send(local,remote):
 subprocess.run([H,'-t',S,'file','send',str(local),remote],check=True,timeout=240,stdout=subprocess.DEVNULL)
def recv(remote,local):
 local.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run([H,'-t',S,'file','recv',remote,local.name],cwd=local.parent,check=True,timeout=240,stdout=subprocess.DEVNULL)
def hashes(paths):
 out={}
 for start in range(0,len(paths),8):
  for line in dev('sha256sum '+' '.join(map(shlex.quote,paths[start:start+8]))).splitlines():
   v,n=line.split(None,1);out[n.strip()]=v
 return out
