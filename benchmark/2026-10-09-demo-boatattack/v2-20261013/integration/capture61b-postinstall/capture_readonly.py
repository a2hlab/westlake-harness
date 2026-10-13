import argparse, json, hashlib, os, re, shlex, subprocess, time, uuid
from pathlib import Path
WS=Path(os.environ['WORKSPACES']).resolve();ROOT=WS/'westlake-harness'
ap=argparse.ArgumentParser(description='Original61b postinstall readonly capture; default preview, zero device writes')
ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expected-boot',required=True);ap.add_argument('--execute',action='store_true');args=ap.parse_args()
OUT=args.out.resolve();SERIAL='61b0657200000000000000000324012c'
HDC='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
template=Path(__file__).with_name('capture.request.json')
cap=json.loads(template.read_text());assert cap['serial']==SERIAL and cap['schema']=='boat-61b-capture/v1'
if not args.execute:
 print(json.dumps({'status':'DISABLED_READONLY_PREVIEW','serial':SERIAL,'expected_boot':args.expected_boot,'file_targets':len(cap['files']),'baseline_targets':319,'directory_targets':len(cap['route_b_directories']),'device_calls':0,'device_writes':0}));raise SystemExit(0)
assert not OUT.exists(),'fresh capture output required'
OUT.mkdir(parents=True);cap['raw']=[];raw=OUT/'raw';raw.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':'$WORKSPACES/'+str(p.resolve().relative_to(WS)), 'sha256':sha(p)}
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def read(name,cmd):
 files=[raw/(name+s) for s in ['.json','.stdout.txt','.stderr.txt']]
 if all(p.exists() for p in files):
  receipt=json.loads(files[0].read_text());assert receipt['argv'][:4]==[HDC,'-t',SERIAL,'shell'];assert receipt['argv'][4].startswith('/system/bin/sh -c '+shlex.quote(cmd)+'; capture_rc=')
  stdout=files[1].read_bytes();stderr=files[2].read_bytes();rc=receipt['rc']
 else:
  marker='__CAPTURE_RC_'+uuid.uuid4().hex+'__';wrapped='/system/bin/sh -c '+shlex.quote(cmd)+'; capture_rc=$?; printf "\\n'+marker+'%s\\n" "$capture_rc"'
  argv=[HDC,'-t',SERIAL,'shell',wrapped];start=time.time();r=subprocess.run(argv,capture_output=True,timeout=180);stdout,stderr,rc=r.stdout,r.stderr,r.returncode
  files[1].write_bytes(stdout);files[2].write_bytes(stderr);save(files[0],{'argv':argv,'rc':rc,'started':start,'finished':time.time()})
 cap['raw'] += [pin(p) for p in files]
 text=stdout.decode();match=re.search(r'\n__CAPTURE_RC_[a-f0-9]+__([0-9]+)\s*$',text)
 if rc or stderr.strip() or not match or match[1]!='0':raise ValueError('capture read failed '+name)
 body=text[:match.start()]
 return body if name=='cfg-source' else body.strip()

def metadata(text,path):
 lines=text.splitlines();assert len(lines)==2
 m=re.fullmatch(r'([0-7]{3,4}):(\d+):(\d+)',lines[0]);assert m
 label=re.fullmatch(r'(u:object_r:[A-Za-z0-9_]+:s0)\s+'+re.escape(path),lines[1]);assert label
 return {'mode':m[1],'uid':int(m[2]),'gid':int(m[3]),'label':label[1]}
cap['boot_before']=read('boot-before','cat /proc/sys/kernel/random/boot_id');assert cap['boot_before']==args.expected_boot,'fresh expected boot mismatch'
names=read('bundle-list','bm dump -a');assert names.splitlines()[0]=='ID: 100:';registered={n.strip() for n in names.splitlines()[1:]};assert all('.' in n for n in registered);cap['boat_uid']=None;cap['boat_registered']=cap['boat_package'] in registered
assert cap['boat_registered'], 'Boat BMS registration missing; no complete capture'
import importlib.util
identity_path=ROOT/'benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-candidate-r2/boat_identity.py'
assert sha(identity_path)=='b0b34102d65ef0ccbeb4cac1516ec1ee723e59dc4023e2f948b753963c4f7c11'
spec=importlib.util.spec_from_file_location('exact_bms_identity',identity_path);identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity)
cap['boat_uid']=identity.parse(read('boat-bundle','bm dump -n '+cap['boat_package']))
paths=sorted(cap['files'])
for i in range(0,len(paths),16):
 selected=paths[i:i+16];cmd='set -e; for p in '+' '.join(shlex.quote(p) for p in selected)+'; do test ! -L "$p"; printf "TARGET=%s\\n" "$p"; if test -f "$p"; then sha256sum "$p"; stat -c "%a:%u:%g" "$p"; ls -Zd "$p"; else test ! -e "$p"; printf "ABSENT\\n"; fi; done'
 body=read('files-%03d'%i,cmd);chunks=body.split('TARGET=')[1:];assert len(chunks)==len(selected)
 for target,chunk in zip(selected,chunks):
  lines=chunk.strip().splitlines();assert lines[0]==target
  if lines[1:]==['ABSENT']:
   cap['files'][target]={'exists':False};continue
  assert len(lines)==4
  h=re.fullmatch(r'([a-f0-9]{64})\s+'+re.escape(target),lines[1]);assert h
  cap['files'][target]=dict(exists=True,sha256=h[1],**metadata('\n'.join(lines[2:]),target))
 print('files',min(i+16,len(paths)),flush=True)
cfg='/system/etc/init/00_westlake_u13_recover-v3.cfg';text=read('cfg-source','cat '+cfg);(OUT/'current-recover.cfg').write_text(text);assert sha(OUT/'current-recover.cfg')==cap['files'][cfg]['sha256'];cap['cfg_source']=pin(OUT/'current-recover.cfg')
for i,p in enumerate(cap['route_b_directories']):cap['route_b_directories'][p]=metadata(read('route-dir-'+str(i),'test -d '+shlex.quote(p)+' && test ! -L '+shlex.quote(p)+' && stat -c "%a:%u:%g" '+shlex.quote(p)+' && ls -Zd '+shlex.quote(p)),p)
p=cap['root_absent']['target'];root_state=read('root-absent','if test -e '+shlex.quote(p)+' || test -L '+shlex.quote(p)+'; then printf PRESENT; else printf ABSENT; fi');assert root_state in ('PRESENT','ABSENT');cap['root_absent']['exists']=root_state=='PRESENT'
# Declared new directory metadata reuses the exact reviewed r4 recipe, not a claim that they exist on61b.
for p in cap['directory_after']:cap['directory_after'][p]={'mode':'755','uid':0,'gid':0,'label':'u:object_r:data_file:s0'}
source=ROOT/'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json';baseline=json.loads(source.read_text());expected=baseline['expected'];actual={}
for i in range(0,len(expected),16):
 selected=sorted(expected)[i:i+16];body=read('baseline-%03d'%i,'sha256sum '+' '.join(shlex.quote(p) for p in selected));lines=body.splitlines();assert len(lines)==len(selected)
 for line in lines:
  h,p=line.split(None,1);assert re.fullmatch('[a-f0-9]{64}',h) and p in expected and p not in actual;actual[p]=h
cap['boot_after']=read('boot-after','cat /proc/sys/kernel/random/boot_id');assert cap['boot_before']==cap['boot_after']
baseline={'serial':SERIAL,'boot_before':cap['boot_before'],'boot_after':cap['boot_after'],'complete':True,'expected':expected,'actual':actual,'source':pin(source),'raw':cap['raw']}
assert actual==expected and all(v['exists'] for v in cap['files'].values())
assert cap['files']['/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk']['sha256']=='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
def triplet(name):return {'receipt':pin(raw/(name+'.json')),'stdout':pin(raw/(name+'.stdout.txt')),'stderr':pin(raw/(name+'.stderr.txt'))}
cap['boat_identity']={'boot_before':triplet('boot-before'),'bundle':triplet('boat-bundle'),'boot_after':triplet('boot-after')}
def pinned(ref):
 p=Path(ref['path'].replace('$WORKSPACES',str(WS)));assert sha(p)==ref['sha256'];return p
identity.validate(cap['boat_identity'],SERIAL,cap['boot_after'],cap['boat_uid'],pinned,lambda p:json.loads(p.read_text()))
save(OUT/'baseline319.json',baseline);cap['baseline319']=pin(OUT/'baseline319.json');cap['complete']=not cap['root_absent']['exists'];cap['pending']=[] if cap['complete'] else ['existing Boat root requires exact owned audit archive under separate root authority; no deletion'];save(OUT/'capture.json',cap)
print(json.dumps({'readonly_collection_complete':True,'deployment_capture_complete':cap['complete'],'files':len(paths),'baseline319_equal':actual==expected,'boot':cap['boot_after'],'boat_uid':cap['boat_uid'],'device_writes':0}))

if not cap['complete']:raise SystemExit(2)
