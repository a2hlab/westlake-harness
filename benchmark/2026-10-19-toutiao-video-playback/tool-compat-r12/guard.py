"""Only read-only serial-qualified queries. No deployment, kill or forwarding."""
import json,shlex,subprocess,time
from pathlib import Path
from policy import *
class Guard:
 def __init__(self,a,out,deadline):self.a=a;self.out=Path(out);self.deadline=deadline;self.n=0;self.marker=None
 def capture(self,phase,after=False):
  a=self.a;self.n+=1;out=self.out/f'identity-{self.n:02d}-{phase}';out.mkdir()
  held=subprocess.run(['bash',str(path(a['lock_script']['path'])),'held',SERIAL],capture_output=True,timeout=5)
  (out/'held.stdout.txt').write_bytes(held.stdout);(out/'held.stderr.txt').write_bytes(held.stderr)
  need(held.returncode==0 and held.stdout.decode().strip()==a['holder'],'lock changed')
  cmds=['set -eu']
  def sec(k,c):cmds.extend(["printf '%s\\n' "+shlex.quote('R12_'+k),c])
  sec('BOOT','cat /proc/sys/kernel/random/boot_id');sec('KERNEL','uname -srvm');sec('SELINUX','getenforce')
  roles=['probe'] if after else ['probe','server']
  for role in roles:
   r=a[role];pid=r['pid'];sec(role+'_STAT',f'cat /proc/{pid}/stat');sec(role+'_STATUS',f'cat /proc/{pid}/status')
   sec(role+'_CMD',f'od -An -v -tx1 /proc/{pid}/cmdline');sec(role+'_EXE',f'readlink /proc/{pid}/exe');sec(role+'_SHA',f'sha256sum /proc/{pid}/exe');sec(role+'_INODE',f"stat -L -c '%d:%i' /proc/{pid}/exe")
  sec('MAPS',f'cat /proc/{a["probe"]["pid"]}/maps')
  if phase=='pre-connect':
   sec('TCP',f'cat /proc/{a["server"]["pid"]}/net/tcp');sec('TCP6',f'cat /proc/{a["server"]["pid"]}/net/tcp6')
   sec('FDS',f'for f in /proc/{a["server"]["pid"]}/fd/*; do readlink "$f"; done')
  sec('COUNTS','cat '+shlex.quote(a['remote_root']+'/probe.stdout'))
  for role in roles:sec(role+'_END',f'cat /proc/{a[role]["pid"]}/stat')
  sec('BOOT_END','cat /proc/sys/kernel/random/boot_id');cmds.append("printf '%s\\n' R12_RC=0")
  argv=[str(path(a['hdc']['path'])),'-t',SERIAL,'shell','; '.join(cmds)]
  (out/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
  try:r=subprocess.run(argv,capture_output=True,timeout=8 if after else min(8,max(.1,self.deadline-time.monotonic())))
  except subprocess.TimeoutExpired as ex:
   (out/'stdout.txt').write_bytes(ex.stdout or b'');(out/'stderr.txt').write_bytes(ex.stderr or b'');(out/'rc.json').write_text('{"timeout":true}\n');raise
  (out/'stdout.txt').write_bytes(r.stdout);(out/'stderr.txt').write_bytes(r.stderr);(out/'rc.json').write_text(json.dumps({'rc':r.returncode})+'\n');need(r.returncode==0,'transport rc')
  d=sections(r.stdout.decode());need(d['BOOT']==a['boot']==d['BOOT_END'],'boot drift');need(d['KERNEL']==a['kernel'] and d['SELINUX']==a['selinux'],'kernel/selinux drift')
  st={}
  for role in roles:
   expected=a[role];begin=stat(d[role+'_STAT']);end=stat(d[role+'_END'])
   need((begin['pid'],begin['birth'])==(expected['pid'],expected['birth'])==(end['pid'],end['birth']),'PID/birth '+role)
   need(begin['state'] not in ('Z','X') and end['state'] not in ('Z','X'),'dead '+role)
   status={l.split(':',1)[0]:l.split(':',1)[1].strip() for l in d[role+'_STATUS'].splitlines() if ':' in l}
   need([int(v) for v in status['Uid'].split()]==[expected['uid']]*4,'UID '+role)
   argv0=[expected['remote_path']] if role=='probe' else [expected['remote_path'],'gdbserver','127.0.0.1:5039','--attach',str(a['probe']['pid'])]
   need(cmdhex(d[role+'_CMD'])==b'\0'.join(v.encode() for v in argv0)+b'\0','exact cmdline '+role)
   need(d[role+'_EXE']==expected['remote_path'] and d[role+'_SHA'].split()[0]==expected['sha256'],'executable path/SHA '+role)
   need(tuple(int(v) for v in d[role+'_INODE'].split(':'))==(expected['device'],expected['inode']),'executable inode '+role)
   st[role]=(end,status)
  tracer=int(st['probe'][1]['TracerPid']);need(tracer==(0 if after else a['server']['pid']),'tracer phase')
  if after:need(st['probe'][0]['state'] not in ('T','t'),'probe still stopped')
  if phase=='pre-connect':
   ls=listeners(d['TCP'])+listeners(d['TCP6']);need(len(ls)==1 and ls[0]['address']=='0100007F:13AF','exact loopback listening socket')
   need('socket:['+str(ls[0]['inode'])+']' in d['FDS'].splitlines(),'server socket ownership')
  addr=mapped_marker(d['MAPS'],a)
  if self.marker is None:self.marker=addr
  need(addr==self.marker,'marker mapping drift')
  counts=[]
  for line in d['COUNTS'].splitlines():
   m=re.fullmatch('R12_COUNT ([1-9][0-9]*)',line);need(m is not None,'probe stdout format');counts.append(int(m[1]))
  need(bool(counts) and all(y>x for x,y in zip(counts,counts[1:])),'stdout counter progression')
  proof={'phase':phase,'marker':addr,'last_count':counts[-1],'tracer':tracer,'state':st['probe'][0]['state'],'pid':a['probe']['pid'],'birth':a['probe']['birth'],'boot':a['boot']}
  (out/'verified.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
