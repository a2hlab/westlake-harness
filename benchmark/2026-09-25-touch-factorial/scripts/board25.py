import subprocess,pathlib,json,sys,shlex,re,time
S='5ea34a4500000000000000001123012c'
H='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh'
R=pathlib.Path.home()/'a2hlab/board'/S/'touch25'
R.mkdir(exist_ok=True)
def dev(c,timeout=60):
 p=subprocess.run([H,'-t',S,'shell',c],capture_output=True,timeout=timeout)
 out=(p.stdout+p.stderr).decode(errors='replace').replace('\r','')
 with (R/'operations.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'command':c,'output':out,'rc':p.returncode})+'\n')
 if p.returncode or '[Fail]' in out:raise RuntimeError(out)
 return out
def recv(remote,local):
 subprocess.run([H,'-t',S,'file','recv',remote,local.name],cwd=local.parent,check=True,timeout=240)
if __name__=='__main__':
 if sys.argv[1]=='shell':print(dev(sys.argv[2]))
 elif sys.argv[1]=='cleanup':
  roots=dev('find /data/local/tmp -maxdepth 1 -type d -name "a2hlab-*"; find /data/app/el2/100/base/org.westlake.imehost/files -maxdepth 1 -type d -name "a2hlab-source-*"').splitlines()
  roots=[p for p in roots if p.startswith('/data/')]
  (R/'cleanup-roots.json').write_text(json.dumps(roots,indent=2))
  logs=[]
  for p in roots:
   logs += [s for s in dev('find '+shlex.quote(p)+' -type f \\( -name "*.log" -o -name "*.stderr" -o -name "*.stdout" -o -name "run.sh" \\)').splitlines() if s.startswith(p+'/')]
  (R/'cleanup-logs.json').write_text(json.dumps(logs,indent=2))
  if logs:
   remote='/data/local/tmp/touch25-old-logs.tar'
   print(dev('tar -cf '+remote+' '+' '.join(map(shlex.quote,logs)),180))
   recv(remote,R/'old-logs.tar')
   assert (R/'old-logs.tar').stat().st_size>0
  # Only processes whose mount/executable references an inventoried deployment.
  raw=dev('for p in /proc/[0-9]*; do echo PROC:$p; readlink $p/exe; cat $p/mountinfo 2>/dev/null | grep a2hlab-source; done',120)
  (R/'cleanup-process-mounts.txt').write_text(raw)
  killed=[]
  for block in raw.split('PROC:')[1:]:
   p=block.splitlines()[0];pid=int(p.split('/')[-1])
   if any(pathlib.Path(root).name in block for root in roots):
    st=dev('cat '+p+'/stat 2>/dev/null')
    if ') ' not in st:continue
    start=st.rsplit(') ',1)[1].split()[19]
    now=dev('cat '+p+'/stat 2>/dev/null')
    if ') ' in now and now.rsplit(') ',1)[1].split()[19]==start:
     dev('kill -9 '+str(pid));killed.append(pid)
  time.sleep(1)
  refs=dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep a2hlab-source',120)
  removed=[];kept=[]
  for p in roots:
   if pathlib.Path(p).name in refs:kept.append(p);continue
   dev('rm -rf '+shlex.quote(p));removed.append(p)
  (R/'cleanup-result.json').write_text(json.dumps({'killed':killed,'removed':removed,'kept':kept,'archive_bytes':(R/'old-logs.tar').stat().st_size},indent=2))
  print('cleanup',len(removed),len(kept),killed)
