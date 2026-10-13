import json, hashlib, os, re, shlex, subprocess, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];WS=ROOT.parent
OUT=Path(__file__).resolve().parent;SERIAL='61b0657200000000000000000324012c'
HDC='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
cap=json.loads((OUT/'capture.request.json').read_text());raw=OUT/'raw';raw.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':'$WORKSPACES/'+str(p.resolve().relative_to(WS)), 'sha256':sha(p)}
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def read(name,cmd):
 marker='__CAPTURE_RC_'+uuid.uuid4().hex+'__';wrapped='/system/bin/sh -c '+shlex.quote(cmd)+'; capture_rc=$?; printf "\\n'+marker+'%s\\n" "$capture_rc"'
 argv=[HDC,'-t',SERIAL,'shell',wrapped];start=time.time();r=subprocess.run(argv,capture_output=True,timeout=180)
 (raw/(name+'.stdout.txt')).write_bytes(r.stdout);(raw/(name+'.stderr.txt')).write_bytes(r.stderr);save(raw/(name+'.json'),{'argv':argv,'rc':r.returncode,'started':start,'finished':time.time()})
 cap['raw'] += [pin(raw/(name+s)) for s in ['.json','.stdout.txt','.stderr.txt']]
 text=r.stdout.decode();match=re.search('\n'+marker+'([0-9]+)\s*$',text)
 if r.returncode or r.stderr.strip() or not match or match[1]!='0':raise ValueError('capture read failed '+name)
 return text[:match.start()].strip()
def metadata(text,path):
 lines=text.splitlines();assert len(lines)==2
 m=re.fullmatch(r'([0-7]{3,4}):(\d+):(\d+)',lines[0]);assert m
 label=re.fullmatch(r'(u:object_r:[A-Za-z0-9_]+:s0)\s+'+re.escape(path),lines[1]);assert label
 return {'mode':m[1],'uid':int(m[2]),'gid':int(m[3]),'label':label[1]}
cap['boot_before']=read('boot-before','cat /proc/sys/kernel/random/boot_id')
names=read('bundle-list','bm dump -a');assert names.splitlines()[0]=='ID: 100:';registered={n.strip() for n in names.splitlines()[1:]};assert all('.' in n for n in registered);cap['boat_uid']=None;cap['boat_registered']=cap['boat_package'] in registered
paths=sorted(cap['files'])
for i in range(0,len(paths),16):
 selected=paths[i:i+16];cmd='set -e; for p in '+' '.join(shlex.quote(p) for p in selected)+'; do test ! -L "$p"; printf "TARGET=%s\\n" "$p"; if test -f "$p"; then sha256sum "$p"; stat -c "%a:%u:%g" "$p"; ls -Zd "$p"; else test ! -e "$p"; printf "ABSENT\\n"; fi; done'
 body=read('files-%03d'%i,cmd);chunks=body.split('TARGET=')[1:];assert len(chunks)==len(selected)
 for target,chunk in zip(selected,chunks):
  lines=chunk.strip().splitlines();assert lines[0]==target
  if lines[1:]==['ABSENT']:
   cap['files'][target]={'exists':False};continue
  assert len(lines)==4
  h=re.fullmatch('([a-f0-9]{64})\s+'+re.escape(target),lines[1]);assert h
  cap['files'][target]=dict(exists=True,sha256=h[1],**metadata('\n'.join(lines[2:]),target))
 print('files',min(i+16,len(paths)),flush=True)
cfg='/system/etc/init/00_westlake_u13_recover-v3.cfg';text=read('cfg-source','cat '+cfg);(OUT/'current-recover.cfg').write_text(text+'\n');assert sha(OUT/'current-recover.cfg')==cap['files'][cfg]['sha256'];cap['cfg_source']=pin(OUT/'current-recover.cfg')
for i,p in enumerate(cap['route_b_directories']):cap['route_b_directories'][p]=metadata(read('route-dir-'+str(i),'test -d '+shlex.quote(p)+' && test ! -L '+shlex.quote(p)+' && stat -c "%a:%u:%g" '+shlex.quote(p)+' && ls -Zd '+shlex.quote(p)),p)
p=cap['root_absent']['target'];assert read('root-absent','if test -e '+shlex.quote(p)+' || test -L '+shlex.quote(p)+'; then printf PRESENT; else printf ABSENT; fi')=='ABSENT';cap['root_absent']['exists']=False
# Declared new directory metadata reuses the exact reviewed r4 recipe, not a claim that they exist on61b.
for p in cap['directory_after']:cap['directory_after'][p]={'mode':'755','uid':0,'gid':0,'label':'u:object_r:data_file:s0'}
source=ROOT/'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json';baseline=json.loads(source.read_text());expected=baseline['expected'];actual={}
for i in range(0,len(expected),16):
 selected=sorted(expected)[i:i+16];body=read('baseline-%03d'%i,'sha256sum '+' '.join(shlex.quote(p) for p in selected));lines=body.splitlines();assert len(lines)==len(selected)
 for line in lines:
  h,p=line.split(None,1);assert re.fullmatch('[a-f0-9]{64}',h) and p in expected and p not in actual;actual[p]=h
cap['boot_after']=read('boot-after','cat /proc/sys/kernel/random/boot_id');assert cap['boot_before']==cap['boot_after']
baseline={'serial':SERIAL,'boot_before':cap['boot_before'],'boot_after':cap['boot_after'],'complete':True,'expected':expected,'actual':actual,'source':pin(source),'raw':cap['raw']}
save(OUT/'baseline319.json',baseline);cap['baseline319']=pin(OUT/'baseline319.json');cap['complete']=False;cap['pending']=['fixed Boat APK installation and actual UID/private target preimages'];save(OUT/'capture.json',cap)
print(json.dumps({'readonly_collection_complete':True,'deployment_capture_complete':False,'files':len(paths),'baseline319_equal':actual==expected,'boot':cap['boot_after'],'boat_uid':cap['boat_uid'],'device_writes':0}))
