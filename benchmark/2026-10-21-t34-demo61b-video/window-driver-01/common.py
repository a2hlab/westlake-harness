"""T34-only receipt and identity helpers. No import-time device action."""
import argparse,datetime,hashlib,importlib.util,json,os,re,shlex,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
REL='benchmark/2026-10-21-t34-demo61b-video/'
SERIAL='61b0657200000000000000000324012c'
RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
q=shlex.quote

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def load_module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def bytes_output(x):return x if isinstance(x,bytes) else (x or '').encode()
def run_record(path,argv,timeout,env=None):
 path.mkdir(parents=True,exist_ok=False);dump(path/'argv.json',argv)
 begin=time.time()
 try:
  p=subprocess.run(argv,capture_output=True,timeout=timeout,env=env);rc,out,err=p.returncode,p.stdout,p.stderr;status='EXITED'
 except subprocess.TimeoutExpired as e:rc,out,err,status=124,bytes_output(e.stdout),bytes_output(e.stderr),'HOST_TIMEOUT_PARTIAL'
 (path/'stdout').write_bytes(out);(path/'stderr').write_bytes(err);(path/'rc').write_text(str(rc)+'\n');dump(path/'result.json',{'rc':rc,'status':status,'started':begin,'finished':time.time(),'timeout_seconds':timeout})
 return rc,out,err

def select_child(rows,parent):
 xs=[r for r in rows if r['ppid']==parent and r['uid']==20011206]
 return xs[0]['pid'] if len(xs)==1 else None

class Driver:
 def __init__(self,a,recovery):
  self.a=a;self.repo=a.repo.resolve();self.w=a.window.resolve();self.recovery=recovery;self.limit=1800 if recovery else 1100;self.i=0
  self.origin=json.loads((self.w/'admission.json').read_text());assert digest(self.w/'admission.json')==a.admission_sha
  assert self.origin['approved_by']=='outer(codex)' and self.origin['serial']==SERIAL
  self.holder=self.origin['holder'];self.start=float(self.origin['window_start']);assert len(self.holder.split())==3
  assert datetime.datetime.strptime(self.holder.split()[-1],'%Y-%m-%dT%H:%M:%S%z').timestamp()==self.start
  assert time.time()>=self.start;self.deadline=time.monotonic()+self.limit-(time.time()-self.start)
  self.out=self.w/('recover-reviewed' if recovery else 'exec-reviewed');assert not self.out.exists(),'Never overwrite or retry this driver evidence'
  for rel,h in json.loads((HERE/'helper-pins.json').read_text()).items():assert digest(self.repo/rel)==h,rel
  self.cv=load_module('candidate_prepare',self.repo/REL/'candidate-view-01/prepare.py')
  self.readout=load_module('candidate_report',self.repo/REL/'candidate-view-01/report.py')
  self.op=json.loads((self.w/('rollback.argv.json' if recovery else 'apply.argv.json')).read_text())
  assert digest(self.w/('rollback.argv.json' if recovery else 'apply.argv.json'))==a.operation_argv_sha
  def opt(n):assert self.op.count(n)==1;return self.op[self.op.index(n)+1]
  assert Path(self.op[1]).resolve()==self.repo/REL/'transport-01/file_transport.py'
  assert Path(opt('--executor')).resolve()==self.repo/REL/'deployment/executor61b.py'
  assert opt('--holder')==self.holder and float(opt('--start'))==self.start
  assert Path(opt('--repo')).resolve()==self.repo and Path(opt('--data')).resolve()==self.w/'data'
  assert opt('--hdc')==str(a.hdc) and '--execute' in self.op
  assert self.op[self.op.index('--')+1]==('rollback' if recovery else 'apply')
  adpath=Path(opt('--admission')).resolve();assert adpath==self.w/('rollback-admission.json' if recovery else 'admission.json')
  ad=json.loads(adpath.read_text());assert ad['approved_by']=='outer(codex)' and ad['holder']==self.holder and float(ad['window_start'])==self.start
  if recovery:
   assert Path(opt('--origin-admission')).resolve()==self.w/'admission.json'
   assert Path(opt('--apply-plan')).resolve()==self.w/'apply/plan.json'
  self.out.mkdir();dump(self.out/'intent.json',{'origin_admission_sha256':a.admission_sha,'operation_argv_sha256':a.operation_argv_sha,'holder':self.holder,'start':self.start,'status':'STARTED_UNKNOWN'})
 def remaining(self):
  r=self.deadline-time.monotonic();assert r>0,'Original window deadline reached; no extension';return r
 def raw(self,tag,argv,to=30,allow_failure=False):
  self.i+=1;p=self.out/f'{self.i:03d}-{tag}';r=run_record(p,argv,min(to,self.remaining()),dict(os.environ,HDC=str(self.a.hdc)))
  if not allow_failure:assert r[0]==0,f'{tag} failed; stop without retry; receipt={p}'
  return r
 def held(self):
  rc,out,_=self.raw('held',['bash',str(self.repo/'scripts/lab/board_note.sh'),'held',SERIAL],15)
  assert out.decode().strip()==self.holder,'Different lock: refuse'
 def shell(self,tag,body,to=35,allow_failure=False):
  self.held();marker='__T34_DRIVER_REMOTE_RC__'
  script='( set -eu\n'+body+'\n); r=$?; printf "\\n'+marker+'%s\\n" "$r"; exit "$r"'
  rc,out,err=self.raw(tag,[str(self.a.hdc),'-t',SERIAL,'shell',script],to,True)
  matches=re.findall(rb'^'+marker.encode()+rb'([0-9]+)$',out,re.M)
  good=rc==0 and matches==[b'0']
  if not allow_failure:assert good,f'{tag} missing/failed remote result; no retry'
  return good,out.decode(errors='replace')
 def boot(self,allow_failure=False):
  good,t=self.shell('boot','cat /proc/sys/kernel/random/boot_id',15,allow_failure)
  rows=[s for s in t.splitlines() if re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',s)]
  return rows[0] if good and len(rows)==1 else None
 def reboot(self,pre):
  self.held();self.raw('reboot',[str(self.a.hdc),'-t',SERIAL,'target','boot'],60)
  until=min(time.monotonic()+200,self.deadline)
  while time.monotonic()<until:
   time.sleep(min(3,max(0,until-time.monotonic())))
   b=self.boot(True)
   if b and b!=pre:
    ready,t=self.shell('ready','param get sys.westlake.demo.u13.ready',15,True)
    if ready and 'true' in [x.strip() for x in t.splitlines()]:return b
  raise AssertionError('Fresh boot/ready not established; keep lock')
 def ui(self,boot,tag,action,seconds):
  self.held();area=self.out/'ui';area.mkdir(exist_ok=True);session=area/'session.json'
  value={'serial':SERIAL,'boot':boot,'holder':self.holder,'start':self.start}
  if session.exists():assert json.loads(session.read_text())==value
  else:dump(session,value)
  argv=['python3',str(self.repo/REL/'ui-01/ui.py'),'--repo',str(self.repo),'--window',str(area),'--session',str(session),'--tag',tag,'--observe-seconds',str(seconds)]
  if self.recovery:argv+=['--recovery']
  if action=='power':argv+=['--power','original']
  self.raw('ui-'+tag,argv+[action],150)
  record=json.loads((area/('ui-'+tag)/'record.json').read_text());assert record['status']=='completed'
  if action!='power':
   shots=[s for s in record.get('screenshots',[]) if s.get('captured')];assert shots
   for s in shots:assert digest(s['path'])==s['sha256']
  return record
 def identity(self,pid,uid,exe,boot):
  good,t=self.shell('identity-'+str(pid),f'''test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}
echo STAT0; cat /proc/{pid}/stat
echo STATUS; cat /proc/{pid}/status
echo EXE; sha256sum /proc/{pid}/exe
echo MNT; readlink /proc/{pid}/ns/mnt
echo CMDLINE; strings /proc/{pid}/cmdline
echo STAT1; cat /proc/{pid}/stat
test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}''')
  stats=re.findall(r'^'+str(pid)+r' \(.*\) (.+)$',t,re.M);assert len(stats)==2
  v=[s.split() for s in stats];assert v[0][19]==v[1][19] and v[0][1]==v[1][1] and all(s[0] not in ('Z','X') for s in v)
  u=re.search(r'^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$',t,re.M);assert u and set(u.groups())=={str(uid)}
  assert re.search(r'^TracerPid:\s+0$',t,re.M)
  assert re.search(r'^'+exe+r'\s+/proc/'+str(pid)+r'/exe$',t,re.M)
  ns=re.findall(r'^mnt:\[\d+\]$',t,re.M);assert len(ns)==1
  if exe==self.cv.HOST:assert '\norg.westlake.imehost\n' in t
  return {'pid':pid,'birth':int(v[0][19]),'ppid':int(v[0][1]),'uid':uid,'exe_sha256':exe,'mnt':ns[0]}
 def discover(self,boot,include_child=True):
  _,t=self.shell('ps',f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}; ps -A -o PID,PPID,UID,NAME')
  rows=[]
  for l in t.splitlines():
   a=l.split()
   if len(a)>=4 and all(x.isdigit() for x in a[:3]):rows.append(dict(zip(['pid','ppid','uid'],map(int,a[:3])),name=a[3]))
  roots=[r['pid'] for r in rows if r['ppid']==1 and r['uid']==0 and r['name'].endswith('appspawn-x')];assert len(roots)==1,'No unique live parent; stop'
  parent=self.identity(roots[0],0,self.cv.EXE,boot)
  _,wm=self.shell('wms','hidumper -s WindowManagerService -a -a');wr=[l.split() for l in wm.splitlines() if l.split() and l.split()[0]=='imehost0'];assert len(wr)==1
  host=self.identity(int(wr[0][2]),20011206,self.cv.HOST,boot);wid=int(wr[0][3])
  _,ns=self.shell('init-mnt','readlink /proc/1/ns/mnt');init=ns.splitlines()[0];assert re.fullmatch(r'mnt:\[\d+\]',init) and parent['mnt']!=init
  child=None;child_pid=select_child(rows,parent['pid']) if include_child else None
  if child_pid is not None:child=self.identity(child_pid,20011206,self.cv.EXE,boot)
  dump(self.out/'discovery.json',{'parent':parent,'host':host,'child':child,'child_scope':'unique PPID/UID row plus exe; null means unknown/ambiguous','wid':wid,'init_mnt':init,'boot':boot})
  return parent,host,child,wid,init

def arguments():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--window',type=Path,required=True);p.add_argument('--hdc',type=Path,required=True);p.add_argument('--admission-sha',required=True);p.add_argument('--operation-argv-sha',required=True);p.add_argument('--execute',action='store_true');return p.parse_args()
def entry(fn,recovery):
 a=arguments()
 if not a.execute:print('PREVIEW_ONLY_NO_DEVICE_CALL');return
 d=Driver(a,recovery)
 try:fn(d)
 except BaseException as e:
  dump(d.out/'failure.json',{'status':'STOPPED_KEEP_LOCK_NO_RETRY','error':str(e),'at':time.time()});raise
