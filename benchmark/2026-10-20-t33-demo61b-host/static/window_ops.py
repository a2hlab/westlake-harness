"""Root-only HAP replacement window; no uninstall/data/runtime writes."""
from pathlib import Path
import argparse,subprocess,json,time,sys,shlex,hashlib,re,os
from datetime import datetime
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--window',type=Path,required=True);p.add_argument('action');p.add_argument('extra',nargs='*');a=p.parse_args()
HERE=Path(__file__).resolve().parent
reference=json.loads((HERE/'reference.json').read_text())
assert a.action in ['lock','intake','read','install','rollback','reboot','wait','launch','capture','power','unlock']
repo=a.repo.resolve();w=a.window.resolve();w.mkdir(parents=True,exist_ok=True)
serial='61b0657200000000000000000324012c';lane='outer(codex)';hdc=os.environ.get('HDC','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc');board=repo/'.octos/boards/app-lighting.md';lock=['bash',str(repo/'scripts/lab/board_note.sh')]
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
 run('lock',lock+['lock',str(board),serial,lane,'T33 61b same-signature host page only; no uninstall/data/runtime writes; experiment 1200s recovery 600s'])
 held=run('holder',lock+['held',serial]).strip();c={'start':datetime.fromisoformat(held.split()[2]).timestamp(),'holder':held,'remote':'/data/local/tmp/t33-host-page-'+str(int(time.time()))};save(w/'context.json',c);print(c);sys.exit()
c=json.loads((w/'context.json').read_text());deadline=time.monotonic()+1800-(time.time()-c['start']);elapsed=time.time()-c['start'];assert elapsed<1800 or a.action=='unlock','window exceeded; explicit recovery required'
assert run('held',lock+['held',serial]).strip()==c['holder']
if a.action not in ['rollback','unlock','read','power','capture','reboot','wait']:assert elapsed<1200,'experiment deadline'
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
out=w/(a.action+'-'+str(time.time_ns()));out.mkdir()
class Board(b.Board):
 def command(self,argv,timeout=60):
  left=deadline-time.monotonic();assert left>0
  assert run('command-held',lock+['held',serial],min(10,left)).strip()==c['holder']
  return super().command(argv,min(timeout,left))
 def shell(self,cmd,required=True,timeout=60):
  assert run('exact-held',lock+['held',serial]).strip()==c['holder']
  r=super().shell(cmd,required,timeout)
  if cmd.startswith('uitest '):
   super().shell('power-shell timeout -o 86400000',True,10)
   assert 'OverrideTimeout=86400000ms' in super().shell('power-shell dump -s',True,10)[1]
  return r
bd=Board(serial,hdc,shlex.join(lock),lane,out/'commands')
if a.action not in ['wait','unlock']:bd.ready()
def hexbytes(text):
 assert re.fullmatch(r'[0-9a-fA-F\s]*',text)
 return bytes.fromhex(text)
def wid_normalize(raw):
 pattern=rb'^export WL_PARENT_ID=([0-9]+)$'
 matches=list(re.finditer(pattern,raw,re.M));assert len(matches)==1,'run WID field count'
 return re.sub(pattern,b'export WL_PARENT_ID=<WID>',raw,flags=re.M),int(matches[0][1])
def stat_fields(raw):
 tail=raw[raw.rfind(')')+2:].split();assert len(tail)>=20 and tail[0] not in ['Z','X','x']
 return {'birth':int(tail[19]),'ppid':int(tail[1])}
def parse_hashes(raw):
 result={}
 for line in raw.splitlines():
  pair=line.split();assert len(pair)==2 and re.fullmatch('[0-9a-f]{64}',pair[0]),'malformed SHA'
  assert pair[1] not in result;result[pair[1]]=pair[0]
 return result

def read(label='state',live=True,initial=False):
 global out
 prior=out;out=prior/label;out.mkdir()
 def text(name,cmd):
  rc,raw=bd.shell(cmd);(out/(name+'.txt')).write_text(raw);(out/(name+'.rc')).write_text(str(rc));return raw
 boot=text('boot','cat /proc/sys/kernel/random/boot_id').strip()
 raw=text('bundle','bm dump -n org.westlake.imehost');j=json.loads(raw[raw.index('{'):]);save(out/'bundle.json',j)
 for key,value in reference['bundle'].items():assert j[key]==value,('bundle',key)
 assert j['applicationInfo']['accessTokenId']==reference['accessTokenId']
 before_path=w/'fresh-before.json'
 baseline=None if initial else json.loads(before_path.read_text())
 if initial:assert not before_path.exists(),'fresh-before already exists'
 else:assert c['fresh_before_sha256']==sha(before_path),'fresh-before pin'
 expected=dict(reference['runtime']);expected.update(reference['controls'])
 paths=list(expected)+[HAP]
 hashes=parse_hashes(text('fingerprint','set -eu; sha256sum '+' '.join(shlex.quote(x) for x in paths)))
 rawrun=hexbytes(text('run-hex','od -An -v -tx1 '+shlex.quote(RT+'/run.sh')))
 assert hashlib.sha256(rawrun).hexdigest()==hashes[RT+'/run.sh']
 if initial:
  assert hashes[RT+'/run.sh']==reference['runtime'][RT+'/run.sh'],'initial exact run'
  original=(HERE/'reference-run.sh').read_bytes()
 else:
  expected=baseline['hashes'];original=bytes.fromhex(baseline['run_hex'])
 for path,value in expected.items():
  if path not in [RT+'/run.sh',HAP]:assert hashes[path]==value,('content drift',path)
 assert wid_normalize(rawrun)[0]==wid_normalize(original)[0],'run changed outside WID'
 assert hashes[HAP] in [old,new]
 absent=text('compat','set -eu; test ! -e '+RT+'/libopensles_android_compat.so; test ! -L '+RT+'/libopensles_android_compat.so; echo COMPAT_ABSENT')
 assert absent.strip()=='COMPAT_ABSENT'
 dirs=[RT+'/app-data',RT+'/app-data/com.ss.android.article.news',RT+'/app-data/com.ss.android.article.news/app_webview','/data/app/el2/100/base/org.westlake.imehost','/data/app/el2/100/base/org.westlake.imehost/files']
 metadata=text('data-metadata',"stat -c '%n %d:%i:%a:%u:%g' "+' '.join(dirs))
 labels=text('data-labels',"ls -ldZ "+' '.join(dirs))
 label_map={line.split()[-1]:next(x for x in line.split() if x.startswith('u:object_r:')) for line in labels.splitlines()}
 assert set(label_map)==set(dirs)
 if baseline:
  assert metadata==baseline['data_metadata'],'directory identity drift'
  assert label_map==baseline['labels'],'directory label drift'
 power=text('power','power-shell dump -s')
 if initial:assert 'Timeout=30000ms' in power and 'OverrideTimeout=86400000ms' in power
 rc,debug=bd.shell('param get debug.ttplayer.log.enable',required=False)
 save(out/'debug.json',{'remote_rc':rc,'stdout':debug});assert re.search(r'errNum is:106(?:!|\s|$)',debug)
 identity=None
 if live:
  ps=text('ps','ps -A -o PID,PPID,UID,NAME');rows=[x.split() for x in ps.splitlines()[1:]]
  parents=[r for r in rows if len(r)==4 and r[2]=='0' and r[3]=='appspawn-x']
  hosts=[r for r in rows if len(r)==4 and r[2]=='20011206' and r[3]=='org.westlake.imehost']
  assert len(parents)==len(hosts)==1,'unique parent/host required'
  pp,hp=parents[0][0],hosts[0][0];assert pp.isdigit() and hp.isdigit()
  pstat=stat_fields(text('parent-pre','cat /proc/'+pp+'/stat'));hstat=stat_fields(text('host-pre','cat /proc/'+hp+'/stat'))
  assert pstat['ppid']==1
  exe=text('parent-exe','readlink /proc/'+pp+'/exe').strip();assert exe in ['/data/local/tmp/asx/appspawn-x','/data/local/tmp/asx/asx-spawner']
  exe_sha=parse_hashes(text('parent-exe-sha','sha256sum /proc/'+pp+'/exe'))['/proc/'+pp+'/exe']
  if baseline:assert exe_sha==baseline['identity']['parent_exe_sha256']
  wm=text('wms','hidumper -s WindowManagerService -a "-a"');wr=[l.split() for l in wm.splitlines() if l.startswith('imehost0 ')]
  assert len(wr)==1 and wr[0][2]==hp and wr[0][3].isdigit();wid=int(wr[0][3])
  envraw=hexbytes(text('parent-env-hex','od -An -v -tx1 /proc/'+pp+'/environ'));fields=envraw.split(b'\0')
  assert [x for x in fields if x.startswith(b'WL_PARENT_ID=')]==[('WL_PARENT_ID='+str(wid)).encode()]
  assert [x for x in fields if x.startswith(b'ASX_RUNTIME_OWNER_UID=')]==[b'ASX_RUNTIME_OWNER_UID=20011206']
  assert wid_normalize(rawrun)[1]==wid,'run/WMS/environment WID mismatch'
  mnt=text('parent-mnt','readlink /proc/'+pp+'/ns/mnt').strip();assert mnt!=text('init-mnt','readlink /proc/1/ns/mnt').strip()
  for path in reference['runtime']:
   if not path.startswith(RT+'/'):continue
   private='/proc/'+pp+'/root/data/local/tmp/asx/'+path[len(RT)+1:]
   actual=parse_hashes(text('private-'+str(len(list(out.iterdir()))),'sha256sum '+private))[private]
   assert actual==hashes[path],('private SHA',path)
   ids=text('inode-'+str(len(list(out.iterdir()))),"stat -L -c '%d:%i' "+path+' '+private).splitlines();assert len(ids)==2 and ids[0]==ids[1],('private inode',path)
  text('private-compat','set -eu; test ! -e /proc/'+pp+'/root/data/local/tmp/asx/libopensles_android_compat.so; test ! -L /proc/'+pp+'/root/data/local/tmp/asx/libopensles_android_compat.so')
  assert pstat==stat_fields(text('parent-post','cat /proc/'+pp+'/stat'))
  assert hstat==stat_fields(text('host-post','cat /proc/'+hp+'/stat'))
  identity={'parent':int(pp),'parent_birth':pstat['birth'],'parent_exe_sha256':exe_sha,'host':int(hp),'host_birth':hstat['birth'],'wid':wid,'parent_mnt':mnt}
 assert text('boot-post','cat /proc/sys/kernel/random/boot_id').strip()==boot
 result={'serial':serial,'boot':boot,'holder':c['holder'],'hashes':hashes,'run_hex':rawrun.hex(),'data_metadata':metadata,'labels':label_map,'identity':identity,'bundle':j,'power_original':reference['power']}
 save(out/'result.json',result)
 if initial:
  assert hashes[HAP]==old
  save(before_path,result);c['fresh_before_sha256']=sha(before_path);save(w/'context.json',c)
 print('read',out,'hap',hashes[HAP],'boot',boot)
 out=prior
 return hashes[HAP],j
if a.action=='intake':read(initial=True)
elif a.action=='read':read()
elif a.action in ['install','rollback']:
 local=Path(a.extra[0]);expected=new if a.action=='install' else old;assert sha(local)==expected
 _,hap_raw=bd.shell('sha256sum '+HAP)
 observed=parse_hashes(hap_raw)[HAP]
 save(out/'hap-before-operation.json',{'action':a.action,'current_sha256':observed,'requested_sha256':expected,'raw':hap_raw,'at':time.time()})
 current,before=read('before',live=(a.action=='install'))
 assert current==observed,'HAP changed during precheck'
 assert current in ([old] if a.action=='install' else [old,new]),'unexpected current HAP'
 if a.action=='rollback' and current==old:
  save(out/'rollback-already-original.json',{'status':'EXACT_OLD_HAP_NO_INSTALL_REQUIRED','sha256':old,'runtime_bundle_data_checked':True,'live_identity_checked':False});print(out);sys.exit()
 bd.shell('mkdir -p '+c['remote']);target=c['remote']+'/'+expected[:12]+'.hap';bd.send(local,target)
 _,raw=bd.shell('sha256sum '+target);assert raw.split()[0]==expected
 _,raw=bd.shell('bm install -r -p '+target,timeout=180);(out/'install.txt').write_text(raw);assert 'success' in raw.lower(),raw
 current,after=read('after',live=False)
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
 with (w/('launch-intent-'+bd.boot+'.json')).open('x') as f:json.dump({'boot':bd.boot,'at':time.time(),'status':'intent_unknown'},f)
 bd.shell('mkdir -p '+c['remote']);record={'key':'toutiao','serial':serial,'boot':bd.boot,'action':'single-normal-icon','screenshots':[]}
 try:
  b.desktop_launch(bd,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},c['remote'],out,record)
  for i in range(3):
   if i:time.sleep(4)
   shot=b.capture(bd,c['remote']+'/launch-'+str(i)+'.jpeg',out/('launch-'+str(i)+'.jpeg'));shot['captured']=True;record['screenshots'].append(shot)
 finally:b.save(out/'record.json',record)
 print(out)
elif a.action=='capture':
 shot=b.capture(bd,c['remote']+'/capture-'+str(time.time_ns())+'.jpeg',out/'screen.jpeg');b.save(out/'record.json',{'screenshots':[dict(shot,captured=True)]});print(out)
elif a.action=='power':
 bd.shell('power-shell timeout -o 86400000');raw=bd.shell('power-shell dump -s')[1];assert 'Timeout=30000ms' in raw and 'OverrideTimeout=86400000ms' in raw;print(raw)
elif a.action=='unlock':
 print(run('unlock',lock+['unlock',str(board),serial,lane]));save(w/'closed.json',{'at':time.time(),'elapsed':time.time()-c['start']})
else:raise ValueError(a.action)
