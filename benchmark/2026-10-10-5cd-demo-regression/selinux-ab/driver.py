#!/usr/bin/env python3
"""Authorized 5cd <=45min icon-click Enforcing/Permissive observation; always restore 1.
Mac detached coordinator, VM existing demo batch. No install/runtime/sandbox/reboot.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;D=HERE.parent;BASE=D.parent/'2026-10-09-demo-baseline';WS=Path(os.environ.get('WORKSPACES',D.parents[2]));SERIAL='5cd1e3dd00000000000000000923012c';BOOT='707ef9d2-038c-48e1-8036-f0d9e50eb5c2';NOTE=WS/'westlake-inputs/tools/board_note.sh';BOARD=WS/'westlake-harness/.octos/boards/app-lighting.md';ROOT=D/'capture-continuation-round-r2'
def read(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def portable(p):return str(Path(p).resolve()).replace(str(WS),'$WORKSPACES')
def note(text):subprocess.run([str(NOTE),'progress',str(BOARD),'91','cx-t0',text],check=True)
def shell(cmd,out):
 # board raw status-marker and lane/boot checks, including setenforce writes.
 code="import importlib.util,json;from pathlib import Path;p=Path("+repr(str(WS/'westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'))+");s=importlib.util.spec_from_file_location('b',p);b=importlib.util.module_from_spec(s);s.loader.exec_module(b);o=Path("+repr(str(out))+ ");o.mkdir(parents=True,exist_ok=False);d=b.Board("+repr(SERIAL)+","+repr(str(WS/'westlake-inputs/tools/hdc_mac.sh'))+","+repr('mac '+str(NOTE))+",'cx-t0',o);d.ready();assert d.boot.strip()=="+repr(BOOT)+";rc,t=d.shell("+repr(cmd)+",required=False);(o/'output.txt').write_text(t+'\\n');print(t);raise SystemExit(rc)"
 p=subprocess.run(['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3','-c',code],capture_output=True,text=True)
 out.parent.joinpath(out.name+'-transport.txt').write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError('VM board command failed rc='+str(p.returncode)+': '+p.stderr[-600:])
 return p.stdout.strip()
def identity(out,parent_required):
 rc=subprocess.run([sys.executable,str(BASE/'t3/verify_identity.py'),'--serial',SERIAL,'--out',str(out)]).returncode
 r=read(out/'identity.json')
 assert not r['diff'] and r['unique_identity_paths']==319 and r['runtime']=='452447a4a0ba' and r['boot']=='ee927db88a67' and r['boot_before']==r['boot_after']==BOOT
 if parent_required:assert rc==0 and r['passed']
 else:assert rc in (0,1) and (r.get('parent_pid','')=='' or r.get('parent_pid','').isdigit()),'expected initial ONDEMAND_NOT_STARTED or one init parent'
 return r

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--resume-existing',action='store_true');ap.add_argument('--keep-lock',action='store_true');a=ap.parse_args()
 if not a.execute:ap.error('outer authorization + --execute required')
 a.out.mkdir(exist_ok=a.resume_existing);os.environ.update(WORKSPACES=str(WS),MAC_HOME=str(Path.home()))
 cfg=read(ROOT/'round.json')
 for binding in cfg['bindings'].values():
  p=Path(binding['path'].replace('$WORKSPACES',str(WS)));assert hashlib.sha256(p.read_bytes()).hexdigest()==binding['sha256'],'original dispatch drift: '+str(p)
 keys=(D/'resume-organicmaps/compare-observed-89/suspect.keys').read_text().split();assert len(keys)==26 and len(set(keys))==26
 apps={x['key']:x for x in read(ROOT/'batch-apps.json')['apps']};tiers={x['key']:x['screenshot_seconds'] for x in read(ROOT/'shot-tiers.json')['apps']}
 control=['cv2-com-edward-studytracker','cv2-com-harr1424-listmaker','cv2-com-kaajjo-libresudoku'];assert set(control)<=set(keys)
 subprocess.run(['orb','-m','a2hlab','true'],check=True,timeout=20)
 identity(a.out/('resume-identity' if a.resume_existing else 'pre-lock-identity'),False)
 note('宣布5cd SELinux单变量<=45min：新boot707ef9d2；原manifest/runner图标点击launch-only，Enforcing26suspect→Permissive同26suspect→finally恢复Enforcing。原轮89+39不续；不重装/不写sandbox/不installer/不reboot。')
 if not a.resume_existing:subprocess.run([str(NOTE),'lock',str(BOARD),SERIAL,'cx-t0','#91 approved Enforcing/Permissive icon-click A/B <=45min'],check=True)
 else:
  h=subprocess.check_output([str(NOTE),'held',SERIAL],text=True);assert 'cx-t0' in h; (a.out/'resume-held.txt').write_text(h)
 start=read(a.out/'result.json')['lock_epoch'] if a.resume_existing else time.time();result={'serial':SERIAL,'boot_id':BOOT,'lock_epoch':start,'deadline':start+45*60,'groups':[],'sandbox_modified':False,'runtime_modified':False}
 env=dict(os.environ,DEMO_T3_MODE='launch',DEMO_INSTALL_INDEX=str(ROOT/'install-index.json'),DEMO_ABILITY_PINS='{}',DEMO_SHOT_TIERS=str(ROOT/'shot-tiers.json'),DEMO_SHOT_TIERS_SHA=cfg['bindings']['shot-tiers.json']['sha256'])
 groups=[]
 grouped={}
 for k in keys:grouped.setdefault((apps[k]['input_root'],tiers[k]),[]).append(k)
 groups += [(mode+'-%d-t%d'%(i,tier),root,tier,ks) for mode in ('enforcing','permissive') for i,((root,tier),ks) in enumerate(grouped.items())]
 try:
  assert shell('cat /sys/fs/selinux/enforce',a.out/('enforce-resume' if a.resume_existing else 'enforce-initial'))=='1'
  for index,(name,input_root,tier,members) in enumerate(groups):
   if a.resume_existing and (a.out/name).exists():
    records=list((a.out/name).glob('*/*/*/record.json'));assert len(records)==len(members) and all(read(p).get('finished_at') and read(p).get('status') not in ('started','batch_interrupted') for p in records),'resume refuses incomplete existing group'
    result['groups'].append({'name':name,'return_code':'existing-all-wrapped','records':len(records),'requested':members,'wrapped':True,'mode':'Enforcing' if name.startswith('enforcing') else 'Permissive'});save(a.out/'result.json',result);continue
   if index==len(grouped):
    shell('setenforce 0',a.out/'set-permissive');assert shell('cat /sys/fs/selinux/enforce',a.out/'read-permissive')=='0';note('5cd已setenforce0并读回0；Enforcing26对照记录已收，开始26suspect同图标路径；finally强制恢复1。')
   keyfile=a.out/(name+'.keys');keyfile.write_text('\n'.join(members)+'\n')
   # HOME belongs to the VM. Resolve in VM through a shell-free Python env wrapper below.
   args=['python3',str(HERE/'batch_readonly_prep.py'),'--execute','--serial',SERIAL,'--lane','cx-t0','--hdc-cmd',str(WS/'westlake-inputs/tools/hdc_mac.sh'),'--lock-cmd','mac '+str(NOTE),'--manifest',str(ROOT/'batch-apps.json'),'--input-root',input_root,'--keys',','.join(members),'--out',str(a.out/name),'--hilog','--shots','5,20','--stop-new-keys-at',str(start+40*60)]
   vmcode="import os,subprocess,sys;args="+repr(args)+";args=[os.path.expandvars(x) for x in args];raise SystemExit(subprocess.call(args))"
   cmd=['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'PATH='+str(ROOT/'vm-tools')+':/usr/local/bin:/usr/bin:/bin','DEMO_T3_MODE=launch','DEMO_INSTALL_INDEX='+env['DEMO_INSTALL_INDEX'],'DEMO_ABILITY_PINS={}','DEMO_SHOT_TIERS='+env['DEMO_SHOT_TIERS'],'DEMO_SHOT_TIERS_SHA='+env['DEMO_SHOT_TIERS_SHA'],'python3','-c',vmcode]
   with (a.out/(name+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
   records=list((a.out/name).glob('*/*/*/record.json'));wrapped=bool(records) and all(read(p).get('finished_at') and read(p).get('status') not in ('started','batch_interrupted') for p in records)
   result['groups'].append({'name':name,'return_code':rc,'records':len(records),'requested':members,'wrapped':wrapped,'mode':'Enforcing' if name.startswith('enforcing') else 'Permissive'})
   save(a.out/'result.json',result)
   facts='\n'.join(p.read_text() for p in (a.out/name).glob('*/*/facts.txt'));(a.out/(name+'-facts.txt')).write_text(facts)
   note('5cd '+name+' facts原样:\n'+facts)
   if rc>=2 or not wrapped:raise RuntimeError('batch transport/cleanup/unfinished refusal: '+name)
   if time.time()>=start+40*60:break
 finally:
  try:
   shell('setenforce 1',a.out/'restore-enforcing');assert shell('cat /sys/fs/selinux/enforce',a.out/'read-restored-enforcing')=='1'
   identity(a.out/'final-identity',True)
   result.update(restored_enforcing=True,final319=True,finished=time.time());save(a.out/'result.json',result)
   result['lock_retained']=a.keep_lock;save(a.out/'result.json',result)
   if not a.keep_lock:subprocess.run([str(NOTE),'unlock',str(BOARD),SERIAL,'cx-t0'],check=True)
   note('5cd SELinux A/B收尾：Enforcing读回1，319 diff{}，runtime452447a4a0ba/boot ee927db88a67，'+('保锁接Boat用户新派' if a.keep_lock else 'UNLOCK')+'；原始分组记录='+portable(a.out)+'。UI待外环，首致命/拼图随后离线归档。')
  except BaseException as e:
   result.update(restoration_failed=str(e));save(a.out/'result.json',result);note('5cd恢复拒绝、保锁：'+str(e));raise
 return 0
if __name__=='__main__':raise SystemExit(main())
