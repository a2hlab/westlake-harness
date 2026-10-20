"""Root-only HAP replacement window; no uninstall/data/runtime writes."""
from pathlib import Path
import argparse,subprocess,json,time,sys,shlex,hashlib
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--window',type=Path,required=True);p.add_argument('action');p.add_argument('extra',nargs='*');a=p.parse_args()
repo=a.repo.resolve();w=a.window.resolve();w.mkdir(parents=True,exist_ok=True)
serial='5cd1e3dd00000000000000000923012c';lane='outer(codex)';hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc';board=repo/'.octos/boards/app-lighting.md';lock=['bash',str(repo/'scripts/lab/board_note.sh')]
HAP='/data/app/el1/bundle/public/org.westlake.imehost/entry.hap';RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
old='df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a';new='b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0'
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(tag,argv,timeout=30,check=True):
 d=w/(tag+'-'+str(time.time_ns()));d.mkdir();save(d/'argv.json',argv)
 try:r=subprocess.run(argv,capture_output=True,timeout=timeout)
 except subprocess.TimeoutExpired as e:
  (d/'stdout').write_bytes(e.stdout or b'');(d/'stderr').write_bytes(e.stderr or b'');(d/'rc').write_text('timeout');raise
 (d/'stdout').write_bytes(r.stdout);(d/'stderr').write_bytes(r.stderr);(d/'rc').write_text(str(r.returncode))
 if check:assert r.returncode==0,(tag,r.returncode,r.stderr.decode())
 return r.stdout.decode('utf-8','replace')
if a.action=='lock':
 assert not (w/'context.json').exists()
 run('lock',lock+['lock',str(board),serial,lane,'T32 same-signature host page only; no uninstall/data/runtime writes; experiment 1200s recovery 600s'])
 held=run('holder',lock+['held',serial]).strip();c={'start':time.time(),'holder':held,'remote':'/data/local/tmp/t32-host-page-'+str(int(time.time()))};save(w/'context.json',c);print(c);sys.exit()
c=json.loads((w/'context.json').read_text());elapsed=time.time()-c['start'];assert elapsed<1800 or a.action=='unlock','window exceeded; explicit recovery required'
assert run('held',lock+['held',serial]).strip()==c['holder']
if a.action not in ['rollback','unlock','read','power','capture','reboot','wait']:assert elapsed<1200,'experiment deadline'
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
out=w/(a.action+'-'+str(time.time_ns()));out.mkdir()
class Board(b.Board):
 def command(self,argv,timeout=60):
  left=1800-(time.time()-c['start']);assert left>0
  return super().command(argv,min(timeout,left))
 def shell(self,cmd,required=True,timeout=60):
  assert run('exact-held',lock+['held',serial]).strip()==c['holder']
  r=super().shell(cmd,required,timeout)
  if cmd.startswith('uitest '):super().shell('power-shell timeout -o 86400000',True,10)
  return r
bd=Board(serial,hdc,shlex.join(lock),lane,out/'commands')
if a.action not in ['wait','unlock']:bd.ready()
params=json.loads((repo/'benchmark/2026-10-20-t30-request-recovery/deployment/final-01/parameters.json').read_text())
def read(label='state'):
 global out
 prior=out;out=prior/label;out.mkdir()
 _,raw=bd.shell('bm dump -n org.westlake.imehost');(out/'bundle.raw').write_text(raw);j=json.loads(raw[raw.index('{'):]);save(out/'bundle.json',j)
 _,raw=bd.shell('sha256sum '+HAP+' '+params['cfg_path']+' '+' '.join(RT+'/'+f['path'] for f in params['artifacts']));(out/'fingerprint.txt').write_text(raw)
 got={line.split()[1]:line.split()[0] for line in raw.splitlines() if len(line.split())==2}
 assert got[params['cfg_path']]==params['cfg_sha256']
 for f in params['artifacts']:assert got[RT+'/'+f['path']]==f['after_sha256'],f['path']
 assert j['uid']==20011300 and j['gid']==20011300
 assert j['versionCode']==2
 reference=json.loads((w.parent/'intake-01/bundle.json').read_text())
 for key in ['appId','appIdentifier','reqPermissions','reqPermissionStates']:
  assert j[key]==reference[key],key
 assert j['applicationInfo']['accessTokenId']==reference['applicationInfo']['accessTokenId']
 assert got[HAP] in [old,new]
 data_dirs=[RT+'/app-data',RT+'/app-data/com.ss.android.article.news',RT+'/app-data/com.ss.android.article.news/app_webview','/data/app/el2/100/base/org.westlake.imehost','/data/app/el2/100/base/org.westlake.imehost/files']
 _,metadata=bd.shell("stat -c '%n %d:%i:%a:%u:%g' "+' '.join(data_dirs));(out/'data-metadata.txt').write_text(metadata)
 for n,cmd in [('identity','cat /proc/sys/kernel/random/boot_id; ps -A -o PID,PPID,UID,NAME; hidumper -s WindowManagerService -a "-a"'),('data','ls -ldZ '+RT+' '+RT+'/data '+RT+'/data /data/app/el2/100/base/org.westlake.imehost /data/app/el2/100/base/org.westlake.imehost/files'),('power','power-shell dump -s')]:
  rc,raw=bd.shell(cmd,required=False);(out/(n+'.txt')).write_text(raw);(out/(n+'.rc')).write_text(str(rc))
  assert rc==0,n
 print('read',out,'hap',got[HAP],'boot',bd.boot)
 out=prior
 return got[HAP],j
if a.action=='read':read()
elif a.action in ['install','rollback']:
 local=Path(a.extra[0]);expected=new if a.action=='install' else old;assert sha(local)==expected
 current,before=read('before')
 assert current==(old if a.action=='install' else new),'unexpected current HAP'
 bd.shell('mkdir -p '+c['remote']);target=c['remote']+'/'+expected[:12]+'.hap';bd.send(local,target)
 _,raw=bd.shell('sha256sum '+target);assert raw.split()[0]==expected
 _,raw=bd.shell('bm install -r -p '+target,timeout=180);(out/'install.txt').write_text(raw);assert 'success' in raw.lower(),raw
 current,after=read('after')
 assert (out/'before/data-metadata.txt').read_bytes()==(out/'after/data-metadata.txt').read_bytes(),'data directory identity changed'
 assert before['uid']==after['uid'] and before['gid']==after['gid']
 assert before['appId']==after['appId']
 assert before['applicationInfo']['accessTokenId']==after['applicationInfo']['accessTokenId']
 _,raw=bd.shell('sha256sum '+HAP);assert raw.split()[0]==expected
elif a.action=='reboot':
 save(out/'before.json',{'boot':bd.boot,'at':time.time()});print(run('reboot',[hdc,'-t',serial,'target','boot'],20))
elif a.action=='wait':
 previous=a.extra[0]
 for _ in range(20):
  remaining=1800-(time.time()-c['start']);assert remaining>7,'recovery deadline'
  assert run('held-poll',lock+['held',serial],min(5,remaining)).strip()==c['holder']
  raw=run('boot-poll',[hdc,'-t',serial,'shell','cat /proc/sys/kernel/random/boot_id; param get sys.westlake.demo.u13.ready'],5,False);lines=raw.splitlines()
  if len(lines)==2 and len(lines[0])==36 and lines[0]!=previous and lines[1].strip()=='true':save(w/'new-boot.json',{'boot':lines[0]});print(raw);break
  time.sleep(2)
 else:raise RuntimeError('boot not ready')
elif a.action=='launch':
 bd.shell('mkdir -p '+c['remote']);record={'key':'toutiao','serial':serial,'boot':bd.boot,'action':'single-normal-icon','screenshots':[]}
 try:
  b.desktop_launch(bd,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},c['remote'],out,record)
  for i in range(3):
   if i:time.sleep(4)
   shot=b.capture(bd,c['remote']+'/launch-'+str(i)+'.jpeg',out/('launch-'+str(i)+'.jpeg'));shot['captured']=True;record['screenshots'].append(shot)
 finally:b.save(out/'record.json',record)
 print(out)
elif a.action=='tap':
 assert len(a.extra)==2 and all(x.isdigit() for x in a.extra);x,y=map(int,a.extra);assert 0<=x<1200 and 0<=y<1920;bd.shell(f'uitest uiInput click {x} {y}')
elif a.action=='back':bd.shell('uitest uiInput keyEvent Back')
elif a.action=='capture':
 shot=b.capture(bd,c['remote']+'/capture-'+str(time.time_ns())+'.jpeg',out/'screen.jpeg');b.save(out/'record.json',{'screenshots':[dict(shot,captured=True)]});print(out)
elif a.action=='power':
 bd.shell('power-shell timeout -o 10000');raw=bd.shell('power-shell dump -s')[1];assert 'Timeout=10000ms' in raw and 'OverrideTimeout=10000ms' in raw;print(raw)
elif a.action=='unlock':
 print(run('unlock',lock+['unlock',str(board),serial,lane]));save(w/'closed.json',{'at':time.time(),'elapsed':time.time()-c['start']})
else:raise ValueError(a.action)
