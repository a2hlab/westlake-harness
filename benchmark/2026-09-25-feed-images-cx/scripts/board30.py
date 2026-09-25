import subprocess,pathlib,json,sys,shlex,re,time
S='5cd1e3dd00000000000000000923012c'
H='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh'
R=pathlib.Path.home()/'a2hlab/board'/S/'images30cx'
R.mkdir(exist_ok=True)
def dev(c,timeout=60):
 p=subprocess.run([H,'-t',S,'shell',c],capture_output=True,timeout=timeout)
 out=(p.stdout+p.stderr).decode(errors='replace').replace('\r','')
 with (R/'operations.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'command':c,'output':out,'rc':p.returncode})+'\n')
 if p.returncode or '[Fail]' in out:raise RuntimeError(out)
 return out
def recv(remote,local):
 subprocess.run([H,'-t',S,'file','recv',remote,local.name],cwd=local.parent,check=True,timeout=240)
