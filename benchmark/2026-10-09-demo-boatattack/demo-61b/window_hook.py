#!/usr/bin/env python3
"""Approved BoatAttack 61b five-bind transaction; never uninstall regression apps.
Uses accepted route2d inputs/touches and master B1 sandbox/cold-stop. Rollback is
limited to journalled mounts whose top mount root and effective SHA still match.
Retention requires explicit screenshot review; missing review fails closed.
"""
import argparse,hashlib,importlib.util,json,os,re,shlex,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',HERE.parents[3]))
MASTER=WS/'westlake-harness';T3=WS/'westlake-harness-tools-inventory/benchmark/2026-10-09-demo-baseline/t3'
CFG=json.loads((HERE/'inputs.json').read_text().replace('$WORKSPACES',str(WS)));SERIAL=CFG['serial'];PKG=CFG['package'];OUT=HERE/'window1'
REMOTE='/data/local/tmp/cx-t0-boat-demo-8ab85446'
EMPTY=hashlib.sha256(b'').hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def checked_inputs():
 for x in CFG['members']+[dict(source=CFG['apk'],sha256=CFG['apk_sha256'])]:
  if sha(x['source'])!=x['sha256']:raise RuntimeError('input SHA mismatch: '+x['source'])
def removable(member,top,current):
 return member['attempted'] and top and top.split()[3]==member['push_root'] and current==member['sha256']
def load_batch():
 s=importlib.util.spec_from_file_location('boat_batch',MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
B=load_batch()
def board(out):
 out.mkdir(parents=True,exist_ok=False)
 return B.Board(SERIAL,'bash '+str(WS/'westlake-inputs/tools/hdc_mac.sh'),'mac '+str(WS/'westlake-inputs/tools/board_note.sh'),'cx-t0',out)
def command(b,c,**kw):return b.shell(c,**kw)[1]
def dsha(b,p):
 text=command(b,'sha256sum '+shlex.quote(p),required=False)
 return text.split()[0] if text.split() and re.fullmatch('[0-9a-f]{64}',text.split()[0]) else None
def mounts(b,p):
 return [l for l in command(b,'cat /proc/self/mountinfo').splitlines() if l.split()[4]==p]
def push_root(b,p):
 rows=[l.split() for l in command(b,'cat /proc/self/mountinfo').splitlines() if p==l.split()[4] or p.startswith(l.split()[4].rstrip('/')+'/')]
 row=max(rows,key=lambda x:len(x[4]));return row[3].rstrip('/')+'/'+p[len(row[4]):].lstrip('/')
def identity(b,out,overlay):
 expect=json.loads((MASTER/'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json').read_text())['expected']
 if overlay:expect.update({m['target']:m['sha256'] for m in CFG['members']})
 actual={};paths=list(expect)
 for i in range(0,len(paths),24):
  text=command(b,'sha256sum '+' '.join(paths[i:i+24]),required=False);actual.update({p:h for h,p in re.findall(r'^([0-9a-f]{64})\s+(/\S+)$',text,re.M)})
 diff={p:dict(expected=h,actual=actual.get(p)) for p,h in expect.items() if actual.get(p)!=h}
 runtime=B.runtime_fingerprint(b,out);boot=B.boot_image_fingerprint(b,out);ps=command(b,'ps -A -o PID,PPID,UID,NAME');parents=[x['pid'] for x in B.processes(ps) if x['name']=='appspawn-x' and x['uid']==0 and x['ppid']==1]
 bootid=command(b,'cat /proc/sys/kernel/random/boot_id');good=not diff and runtime==(CFG['runtime_fp'] if overlay else '452447a4a0ba') and boot=='ee927db88a67' and parents==[11752] and bootid=='131b8ff9-2ead-4ee0-afe4-8700433d8bec'
 result=dict(passed=good,unique_paths=len(expect),diff=diff,runtime=runtime,boot=boot,parent_pids=parents,boot_id=bootid);save(out/'identity.json',result);print(json.dumps(result),flush=True)
 if not good:raise RuntimeError('identity gate refused')
 return result
def await_review(name,seconds=240):
 print('REVIEW_READY '+name,flush=True);end=time.time()+seconds
 while time.time()<end:
  p=OUT/(name+'-review.json')
  if p.exists():
   doc=json.loads(p.read_text());return doc.get('accepted') is True
  time.sleep(2)
 return False
def apply():
 checked_inputs();b=board(OUT/'apply');b.ready();identity(b,b.out,False)
 rc,dump=b.shell('bm dump -n '+PKG,required=False);(b.out/'bundle-before.txt').write_text(dump)
 if '"bundleName"' in dump:raise RuntimeError('BoatAttack already installed; refuse replacement')
 j=dict(serial=SERIAL,created=time.time(),members=[],installed=False,install_attempted=False,placeholder=False);save(OUT/'journal.json',j)
 command(b,'mkdir '+REMOTE)
 for i,m in enumerate(CFG['members'][:2]):
  if dsha(b,m['target'])!=m['baseline']:raise RuntimeError('shared base gate')
  x=dict(m,push=REMOTE+'/'+str(i)+'-'+Path(m['source']).name,attempted=False,before_mounts=mounts(b,m['target']));j['members'].append(x);save(OUT/'journal.json',j)
  b.send(x['source'],x['push']);x['push_root']=push_root(b,x['push']);save(OUT/'journal.json',j);ctx=command(b,'ls -Z '+x['target']);label=re.search(r'u:object_r:[A-Za-z0-9_]+:s0',ctx)
  if not label:raise RuntimeError('SELinux target label missing')
  command(b,'chcon '+label.group()+' '+x['push']);x['attempted']=True;save(OUT/'journal.json',j);command(b,'mount --bind '+x['push']+' '+x['target']);assert dsha(b,x['target'])==x['sha256']
 b.send(CFG['apk'],REMOTE+'/boat.apk');j['install_attempted']=True;save(OUT/'journal.json',j)
 rc,text=b.shell('bm install -p '+REMOTE+'/boat.apk',required=False,timeout=180);(b.out/'install.txt').write_text(text)
 if not B.bm_success(rc,text,'install'):raise RuntimeError('BMS install refused: '+text)
 j['installed']=True;dump=command(b,'bm dump -n '+PKG);(b.out/'bundle.json.txt').write_text(dump);bundle=B.parse_bundle(dump,PKG);j['uid']=bundle['uid'];save(OUT/'journal.json',j);B.prepare_sandbox(b,PKG,j['uid'],b.out)
 for i,m in enumerate(CFG['members'][2:],2):
  x=dict(m,push=REMOTE+'/'+Path(m['source']).name,attempted=False,before_mounts=mounts(b,m['target']));j['members'].append(x);save(OUT/'journal.json',j);b.send(x['source'],x['push']);x['push_root']=push_root(b,x['push']);save(OUT/'journal.json',j)
  if dsha(b,x['target']) is None:
   if not x['target'].endswith('/libwestlake_bionic_signal_box.so'):raise RuntimeError('missing original native')
   j['placeholder']=True;save(OUT/'journal.json',j);command(b,'test ! -e '+x['target']+' && touch '+x['target']+' && chmod 0644 '+x['target']+' && chcon u:object_r:data_app_el1_file:s0 '+x['target'])
  command(b,'chown 0:0 '+x['push']+' && chmod 0755 '+x['push']+' && chcon u:object_r:data_app_el1_file:s0 '+x['push']);x['attempted']=True;save(OUT/'journal.json',j);command(b,'mount --bind '+x['push']+' '+x['target']);assert dsha(b,x['target'])==x['sha256']
 assert B.cold_stop(b,PKG,j['uid'],b.out,'before-boat')
 text=command(b,'aa start -a '+CFG['ability']+' -b '+PKG+' -W');(b.out/'aa-start.txt').write_text(text);time.sleep(28)
 def child():
  ps=command(b,'ps -A -o PID,PPID,UID,NAME');kids=[x['pid'] for x in B.processes(ps) if x['uid']==j['uid'] and x['ppid']==11752]
  if len(kids)!=1:raise RuntimeError('Boat child count changed: '+str(kids))
  return kids[0]
 pid=child();images={};images['before']=B.capture(b,REMOTE+'/boat-before.jpeg',OUT/'boat-before.jpeg')
 touches=[('accel','-d 1740 1100 -i 9000 -u 1740 1100'),('left','-m 220 1000 70 1000 -k 5000 700'),('accel2','-d 1740 1100 -i 9000 -u 1740 1100'),('right','-m 220 1000 370 1000 -k 5000 700'),('reset','-c 1440 1100 200')]
 for name,args in touches:
  text=command(b,'uinput -T '+args);(b.out/(name+'-input.txt')).write_text(text);time.sleep(1);assert child()==pid;images[name]=B.capture(b,REMOTE+'/boat-'+name+'.jpeg',OUT/('boat-'+name+'.jpeg'))
 (b.out/'boat-child-maps.txt').write_text(command(b,f'cat /proc/{pid}/maps'))
 (b.out/'hilog.txt').write_text(command(b,'hilog -x',timeout=90));save(OUT/'boat-evidence.json',dict(pid=pid,images=images));identity(b,b.out,True)
 if not await_review('boat'):raise RuntimeError('Boat screenshot/touch review not accepted')
 assert B.cold_stop(b,PKG,j['uid'],b.out,'boat-after')
 j['applied']=True;save(OUT/'journal.json',j)
def smoke_restore(out):
 bindir=OUT/'vm-tools';bindir.mkdir(exist_ok=True);hdc=bindir/'hdc'
 if not hdc.exists():hdc.symlink_to(WS/'westlake-inputs/tools/hdc_mac.sh')
 env=dict(os.environ,PATH=str(bindir)+os.pathsep+os.environ.get('PATH',''))
 return subprocess.run(['python3',str(MASTER/'scripts/lab/activation_smoke.py'),'--spec',str(MASTER/'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json'),'--serial',SERIAL,'--lane','cx-t0','--out',str(out),'--hdc','bash '+str(WS/'westlake-inputs/tools/hdc_mac.sh'),'--lock-cmd','mac '+str(WS/'westlake-inputs/tools/board_note.sh')],env=env).returncode

def rollback(b,j):
 if j.get('install_attempted'):
  rc,dump=b.shell('bm dump -n '+PKG,required=False)
  if '"bundleName"' in dump:
   uid=B.parse_bundle(dump,PKG)['uid'];assert B.cold_stop(b,PKG,uid,b.out,'rollback-boat')
 for m in reversed(j['members']):
  current=mounts(b,m['target'])
  if current==m['before_mounts']:continue
  if len(current)!=len(m['before_mounts'])+1 or not removable(m,current[-1] if current else None,dsha(b,m['target'])):raise RuntimeError('foreign/drifted mount: '+m['target'])
  command(b,'umount '+m['target']);assert mounts(b,m['target'])==m['before_mounts']
 if j.get('placeholder'):
  p=CFG['members'][-1]['target']
  if dsha(b,p) is not None:
   if mounts(b,p) or dsha(b,p)!=EMPTY:raise RuntimeError('placeholder guard refused')
   command(b,'rm '+p)
 if j.get('install_attempted'):
  rc,dump=b.shell('bm dump -n '+PKG,required=False)
  if '"bundleName"' in dump:
   rc,text=b.shell('bm uninstall -n '+PKG,required=False,timeout=120)
   if not B.bm_success(rc,text,'uninstall'):raise RuntimeError('Boat uninstall refused')
 identity(b,b.out,False)
 if smoke_restore(b.out/'restored-smoke')!=0:raise RuntimeError('restored smoke failed; lock retained')
 save(OUT/'rollback-result.json',dict(passed=True,baseline='U13',identity=json.loads((b.out/'identity.json').read_text())))

def finish(force=False):
 b=board(OUT/('rollback-'+str(int(time.time()))));p=OUT/'journal.json'
 if not p.exists():identity(b,b.out,False);return
 j=json.loads(p.read_text());smoke=OUT/'runner/smoke/smoke-result.json';records=list((OUT/'runner').glob('*/*/*/*/record.json'));keys={x.parent.name for x in records};expected={x['key'] for x in json.loads((HERE/'regression-apps.json').read_text())['apps']}
 ready=not force and j.get('applied') and smoke.exists() and json.loads(smoke.read_text()).get('passed') and keys>=expected
 if ready and await_review('regression'):
  identity(b,b.out,True);save(OUT/'retained.json',dict(passed=True,identity=json.loads((b.out/'identity.json').read_text()),review=json.loads((OUT/'regression-review.json').read_text())));print('RETAINED approved BoatAttack overlay',flush=True)
 else:rollback(b,j)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['preflight','apply','finish','rollback']);a=ap.parse_args()
 if a.mode=='preflight':checked_inputs();print('INPUTS_PASS six pinned SHA256');return 0
 if sys.platform=='darwin':return subprocess.run(['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3',str(Path(__file__).resolve()),a.mode]).returncode
 OUT.mkdir(parents=True,exist_ok=True)
 if a.mode=='apply':apply()
 else:finish(a.mode=='rollback')
 return 0
if __name__=='__main__':raise SystemExit(main())
