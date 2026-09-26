import subprocess,pathlib,json,sys,shlex,re,time,hashlib
S='61b0657200000000000000000324012c'
H='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh'
R=pathlib.Path.home()/'a2hlab/board'/S/'isolated48'
R.mkdir(parents=True,exist_ok=True)
ROOT=pathlib.Path(__file__).resolve().parents[1]
D='/data/local/tmp/operator45'
PKG='com.ss.android.article.news'
def dev(command,timeout=120):
 p=subprocess.run([H,'-t',S,'shell',command],capture_output=True,timeout=timeout)
 out=(p.stdout+p.stderr).decode(errors='replace').replace('\r','')
 with (R/'operations.jsonl').open('a') as f:f.write(json.dumps(dict(epoch=time.time(),command=command,output=out,rc=p.returncode))+'\n')
 if p.returncode or '[Fail]' in out:raise RuntimeError(out[-3000:])
 return out
def recv(remote,local):
 local.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run([H,'-t',S,'file','recv',remote,local.name],cwd=local.parent,check=True,timeout=300,stdout=subprocess.DEVNULL)
def send(local,remote):subprocess.run([H,'-t',S,'file','send',str(local),remote],check=True,timeout=300,stdout=subprocess.DEVNULL)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stat(pid):
 s=dev('cat /proc/'+str(pid)+'/stat 2>/dev/null').strip()
 return s if ') ' in s else None
def live(pid,birth=None):
 s=stat(pid)
 if not s:return False
 f=s.rsplit(') ',1)[1].split()
 return f[0]!='Z' and (birth is None or f[19]==birth)
def kill_checked(pid):
 a=stat(pid);b=stat(pid)
 if a and b and a.rsplit(') ',1)[1].split()[19]==b.rsplit(') ',1)[1].split()[19]:dev('kill -9 '+str(pid))
def shot(r,label):
 remote='/data/local/tmp/refined48.jpeg';dev('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/(label+'.jpeg'))
 p=ROOT/'preview'/r.name/(label+'.jpeg');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/(label+'.jpeg')).read_bytes());print('SHOT',p,flush=True)

# HDC file recv on procfs stops after its first ~4 KiB read; spool to a regular file.
def proc_maps(pid, destination):
 remote='/data/local/tmp/refined48-maps-'+str(int(pid))+'.txt'
 dev('cat /proc/'+str(int(pid))+'/maps > '+remote)
 recv(remote,destination)
 lines=destination.read_text().splitlines()
 assert len(lines)>100 and any('[stack]' in l for l in lines),'incomplete maps snapshot'
