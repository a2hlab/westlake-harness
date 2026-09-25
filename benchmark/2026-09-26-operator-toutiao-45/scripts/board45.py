import subprocess,pathlib,json,sys,shlex,re,time,hashlib
S='61b0657200000000000000000324012c'
SOURCE='5ea34a4500000000000000001123012c'
H='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh'
R=pathlib.Path.home()/'a2hlab/board'/S/'operator45'
R.mkdir(parents=True,exist_ok=True)
A=pathlib.Path('/home/dspfac/a2hlab/source-closure/verify')
def dev(c,timeout=120,serial=S):
 p=subprocess.run([H,'-t',serial,'shell',c],capture_output=True,timeout=timeout)
 out=(p.stdout+p.stderr).decode(errors='replace').replace('\r','')
 with (R/'operations.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'serial':serial,'command':c,'output':out,'rc':p.returncode})+'\n')
 if p.returncode or '[Fail]' in out:raise RuntimeError(out)
 return out

def recv(remote,local,serial=S):
 local.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run([H,'-t',serial,'file','recv',remote,local.name],cwd=local.parent,check=True,timeout=300)

def send(local,remote):subprocess.run([H,'-t',S,'file','send',str(local),remote],check=True,timeout=300)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def c40_done():
 p=pathlib.Path('/proc/1460613/cmdline')
 return not p.exists() or b'boardloop.runner' not in p.read_bytes()
