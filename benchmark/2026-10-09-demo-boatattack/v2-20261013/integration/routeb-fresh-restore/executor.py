#!/usr/bin/env python3
"""Current-prestate adapter: original487 transaction, atomic non-CFG placement, no reboot."""
import argparse,copy,json,math,os,re,subprocess,sys,time
from pathlib import Path
import prepare as p
HERE=Path(__file__).resolve().parent

def directory_check(core,dev,plan):
 for target,row in plan['fresh_rebase']['all_directories'].items():
  want=':'.join(str(row[k]) for k in ('mode','uid','gid','label','identity'))
  got=dev.shell('exact-existing-directory','set -eu; test -d '+core.q(target)+'; test ! -L '+core.q(target)+"; stat -c '%a:%u:%g:%C:%d:%i' "+core.q(target))
  p.need(got==want,'existing directory metadata/inode changed: '+target)

def stage_path(plan,target):
 if target=='/system/etc/init/01_westlake_u13_toutiao.cfg':return '/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/cfg-rebase-'+plan['_sha'][:24]
 return target+'.routeb-recovery-'+plan['_sha'][:24]

def atomic_place(core,dev,row,expected,plan,out):
 """The signed preimage is checked BEFORE the first stage/send, then again in rename CAS."""
 before=dev.probe(row['target']);p.need(core.equal(before,expected),'atomic authorized preimage drift '+row['target'])
 p.need(expected['exists'] is True,'current rebase only replaces existing files')
 target=row['target'];stage=stage_path(plan,target);p.need(not dev.probe(stage)['exists'],'foreign staging file')
 n=next(i for i,r in enumerate(plan['members']) if r['target']==target)
 core.save(out/('atomic-intent-%03d.json'%n),dict(plan_sha256=plan['_sha'],target=target,stage=stage,expected_before=expected,after_sha256=row['sha256']))
 try:
  dev.send('atomic-stage',core.resolve(row['source']),stage)
  meta=row['after'];desired=dict(exists=True,sha256=row['sha256'],**meta)
  stage_meta='set -eu; chown '+core.q(str(meta['uid'])+':'+str(meta['gid']))+' '+core.q(stage)+'; chmod '+core.q(meta['mode'])+' '+core.q(stage)+'; chcon '+core.q(meta['label'])+' '+core.q(stage)+'; '
  stage_meta+='test \"$(sha256sum '+core.q(stage)+' | cut -d\' \' -f1)\" = '+core.q(row['sha256'])+'; test \"$(stat -c %a:%u:%g:%C '+core.q(stage)+')\" = '+core.q(':'.join(str(meta[k]) for k in ('mode','uid','gid','label')))+'; '
  want=':'.join(str(expected[k]) for k in ('mode','uid','gid','label'))
  script=('set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+core.q(plan['_active_boot'])+'; test ! -L '+core.q(target)+'; test -f '+core.q(target)+'; test ! -L '+core.q(stage)+'; '
          'test "$(sha256sum '+core.q(target)+' | cut -d\' \' -f1)" = '+core.q(expected['sha256'])+'; '
          'test "$(stat -c %a:%u:%g:%C '+core.q(target)+')" = '+core.q(want)+'; '
          'test "$(sha256sum '+core.q(stage)+' | cut -d\' \' -f1)" = '+core.q(row['sha256'])+'; '
          'test "$(stat -c %a:%u:%g:%C '+core.q(stage)+')" = '+core.q(':'.join(str(meta[k]) for k in ('mode','uid','gid','label')))+'; '
          'mv '+core.q(stage)+' '+core.q(target))
  if target==core.CFG:
   remount="set -eu; reseal=0; trap 'rc=$?; if [ \"$reseal\" = 1 ]; then mount -o ro,remount / || rc=1; fi; exit \"$rc\"' EXIT; opts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4); case ,$opts, in *,rw,*) ;; *,ro,*) mount -o rw,remount /; reseal=1;; *) exit 2;; esac; "
   # Cross-filesystem source staging is copied to a fresh sibling on root before the guarded final rename.
   temp=target+'.routeb-recovery-'+plan['_sha'][:24]
   script=remount+'test ! -e '+core.q(temp)+'; test ! -L '+core.q(temp)+'; cp '+core.q(stage)+' '+core.q(temp)+'; chown '+core.q(str(meta['uid'])+':'+str(meta['gid']))+' '+core.q(temp)+'; chmod '+core.q(meta['mode'])+' '+core.q(temp)+'; chcon '+core.q(meta['label'])+' '+core.q(temp)+'; '+script.replace(core.q(stage),core.q(temp))
  script=stage_meta+script+'; test \"$(sha256sum '+core.q(target)+' | cut -d\' \' -f1)\" = '+core.q(row['sha256'])+'; test \"$(stat -c %a:%u:%g:%C '+core.q(target)+')\" = '+core.q(':'.join(str(meta[k]) for k in ('mode','uid','gid','label')))
  p.need(time.time()<plan.get('_authorization_expires',float('inf')),'expired before atomic CAS')
  dev.shell('atomic-cas-rename',script)
 except (ValueError,OSError,KeyError,TypeError) as exc:
  obs=None
  try:obs=dev.probe(stage)
  except (ValueError,OSError,KeyError,TypeError):pass
  failure=dict(plan_sha256=plan['_sha'],target=target,stage=stage,observation=obs,error=str(exc))
  if target==core.CFG:
   failure['root_temp']=target+'.routeb-recovery-'+plan['_sha'][:24]
   try:failure['root_temp_observation']=dev.probe(failure['root_temp'])
   except (ValueError,OSError,KeyError,TypeError):failure['root_temp_observation']=None
  core.save(out/('atomic-failed-%03d.json'%n),failure)
  raise

def guard(recipe,plan,authpath,authsha,adpath,adsha,action,now=None):
 now=time.time() if now is None else now
 p.need(p.sha(authpath)==authsha and p.sha(adpath)==adsha,'independent authorization/admission pins')
 auth=p.read(authpath);ad=p.read(adpath)
 p.need(auth.get('approved_by')=='outer(codex)' and ad.get('signed_by')=='outer(claude)' and ad.get('admitted') is True,'separate original outer roles')
 for doc in (auth,ad):
  for key,value in dict(recipe_sha256=recipe['_sha'],plan_sha256=plan['_sha'],executor_sha256=p.sha(__file__),serial=plan['serial'],boot_id=plan['boot_id'],action=action).items():p.need(doc.get(key)==value,'scope/pin '+key)
  expiry=doc.get('expires_epoch');p.need(type(expiry) in (int,float) and math.isfinite(expiry) and now<expiry<=now+2700,'current maximum45min authorization')
  p.need(doc.get('synthetic',False) is False and isinstance(doc.get('holder'),str) and doc['holder'],'actual holder')
 p.need(ad['authorization_sha256']==authsha and ad['holder']==auth['holder'] and ad['lock_tool']==auth['lock_tool'],'independent admission binding')
 p.need(ad.get('target_sha256')==recipe['targets'],'complete487 admission')
 if action=='apply':
  deadline=auth.get('apply_deadline_epoch');p.need(type(deadline) in (int,float) and math.isfinite(deadline) and now<deadline<=min(auth['expires_epoch'],ad['expires_epoch'])-600,'ten minute independent rollback reserve required')
  p.need(ad.get('apply_deadline_epoch')==deadline,'independent admission apply deadline')
 p.checked(auth['lock_tool'])
 return auth,ad

def held(auth,runner=subprocess.run):
 lock=p.checked(auth['lock_tool']);r=runner(['bash',str(lock),'held',auth['serial']],capture_output=True,text=True,timeout=15)
 p.need(r.returncode==0 and not r.stderr and r.stdout.strip()==auth['holder'],'exact held full line changed')

def member_receipts(core,plan,out):
 tx=core.read(out/'transaction.json');wanted=[dict(target=r['target'],before=r['before'],backup='backup-%03d'%i,candidate_sha256=r['sha256']) for i,r in enumerate(plan['members'])]
 p.need(tx==dict(plan_sha256=plan['_sha'],serial=plan['serial'],boot_id=plan['boot_id'],backups=wanted),'current full487 transaction')
 p.need(core.read(out/'placed.json')['state']=='PLACED_ONLY','current placed summary')
 p.need(len(list(out.glob('placed-[0-9][0-9][0-9].json')))==487,'exact487 current receipts')
 for i,row in enumerate(plan['members']):
  p.need(core.read(out/('placed-%03d.json'%i))==dict(target=row['target'],sha256=row['sha256']),'current placed member mismatch')
  p.need(core.digest(out/('backup-%03d'%i))==row['before']['sha256'],'actual backup SHA')
 return [p.pin(out/('placed-%03d.json'%i)) for i in range(487)]

def execute(recipe_path,recipe_sha,authpath,authsha,adpath,adsha,out,action,device_factory=None,lock_runner=subprocess.run):
 recipe,plan,planpath=p.verify(recipe_path,recipe_sha);recipe['_sha']=recipe_sha;plan['_sha']=p.sha(planpath)
 auth,ad=guard(recipe,plan,authpath,authsha,adpath,adsha,action)
 core=p.load(p.checked(plan['fresh_rebase']['original_executor']),'routeb_original487_executor')
 # Enabling is confined to the explicitly authorized in-memory invocation; the signed disabled plan is unchanged.
 active=copy.deepcopy(plan);active['execution_enabled']=True;active['_active_boot']=auth['boot_id'];active['_authorization_expires']=min(auth['expires_epoch'],ad['expires_epoch'],auth['apply_deadline_epoch'] if action=='apply' else float('inf'))
 core.validate(active,authpath,authorization_sha256=authsha);held(auth,lock_runner)
 if action=='apply':out.mkdir(parents=True,exist_ok=False)
 else:p.need(out.is_dir(),'original transaction required')
 dev=device_factory(active,out) if device_factory else core.Device(active,out)
 result=dict(schema='routeb-current-restore-receipt/v1',complete=False,executor_rc=None,serial=plan['serial'],boot_id=plan['boot_id'],recipe_sha256=recipe_sha,plan_sha256=plan['_sha'],action=action,reboots=0,original_activation_binding=plan['fresh_rebase']['original_activation_binding'],original_realization=plan['fresh_rebase']['original_realization'],authorization=p.pin(authpath),admission=p.pin(adpath),user_data_deleted=False)
 original_fresh=core.fresh;original_place=core.place;original_identity=core.check_identity
 def identity(d,pl):
  p.need(time.time()<active['_authorization_expires'],'execution deadline reached; reserved rollback time retained');held(auth,lock_runner);original_identity(d,pl)
 def fresh(d,pl):directory_check(core,d,pl);original_fresh(d,pl)
 core.check_identity=identity;core.fresh=fresh
 expected={r['target']:r['before'] for r in plan['members']}
 # Exact before==after is deliberate: this replays real placement of the admitted current files.
 # The original rollback short path preserves existing user directories and never removes unknown data.
 def place(d,row):
  return atomic_place(core,d,row,expected[row['target']],active,out)
 core.place=place
 try:
  directory_check(core,dev,active)
  if action=='apply':
   core.apply(active,dev,out);members=member_receipts(core,active,out)
   # Full final verification includes every original target, not only per-send readbacks.
   for row in active['members']:p.need(core.equal(dev.probe(row['target']),dict(exists=True,sha256=row['sha256'],**row['after'])),'final member drift')
   directory_check(core,dev,active);identity(dev,active)
   core.save(out/'directory-complete.json',dict(state='EXISTING_DIRECTORIES_VERIFIED',count=29,directories=active['fresh_rebase']['all_directories'],reboots=0,user_data_deleted=False))
   cfg=next(r for r in active['members'] if r['target']==core.CFG);stage=stage_path(active,core.CFG);staged=dev.probe(stage);p.need(core.equal(staged,dict(exists=True,sha256=cfg['sha256'],**cfg['after'])),'cfg audit stage drift')
   result['retained_audit']=[dict(target=stage,observed=staged)]
   result.update(complete=True,executor_rc=0,placed_count=487,member_receipts=members,transaction=p.pin(out/'transaction.json'),directory_receipt=p.pin(out/'directory-complete.json'),status='RESTORED487_WITH_DIRECTORY_COMPLETION_NOT_UI_ACCEPTANCE')
  else:
   retained=[]
   for f in sorted(out.glob('atomic-failed-*.json')):
    v=core.read(f);p.need(v['plan_sha256']==plan['_sha'] and v['stage']==stage_path(plan,v['target']) and v['observation'] is not None,'unknown stage ownership')
    observed=dev.probe(v['stage']);p.need(core.equal(observed,v['observation']),'foreign stage drift');retained.append(dict(target=v['stage'],observed=observed,evidence=p.pin(f)))
    if 'root_temp' in v:
     p.need(v['root_temp']==v['target']+'.routeb-recovery-'+plan['_sha'][:24] and v.get('root_temp_observation') is not None,'unknown cfg temp')
     got=dev.probe(v['root_temp']);p.need(core.equal(got,v['root_temp_observation']),'foreign cfg temp');retained.append(dict(target=v['root_temp'],observed=got,evidence=p.pin(f)))
   core.rollback(active,dev,out)
   for row in active['members']:p.need(core.equal(dev.probe(row['target']),row['before']),'rollback did not restore exact before')
   directory_check(core,dev,active);identity(dev,active)
   result.update(complete=True,executor_rc=0,status='CURRENT_PRESTATE_RESTORED_WITH_DECLARED_AUDIT',retained_audit=retained)
  return result,0
 except (ValueError,OSError,KeyError,TypeError) as exc:
  result.update(executor_rc=2,status='INCOMPLETE_PRESERVE_TRANSACTION',error=str(exc));return result,2
 finally:
  name='recipe-receipt.json' if action=='apply' else 'rollback-receipt-'+str(time.time_ns())+'.json'
  core.save(out/name,result)

def main():
 a=argparse.ArgumentParser();a.add_argument('--recipe',type=Path,required=True);a.add_argument('--recipe-sha256',required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--execute',action='store_true');a.add_argument('--action',choices=['apply','rollback'],default='apply')
 for n in ('authorization','admission'):a.add_argument('--'+n,type=Path);a.add_argument('--'+n+'-sha256')
 args=a.parse_args()
 try:
  if not args.execute:
   r,p0,_=p.verify(args.recipe,args.recipe_sha256);print(json.dumps(dict(status='DISABLED_CURRENT487_PREVIEW',members=487,directories=29,boot_id=p0['boot_id'],device_calls=0)));return 0
  result,rc=execute(args.recipe,args.recipe_sha256,args.authorization,args.authorization_sha256,args.admission,args.admission_sha256,args.out,args.action);print(json.dumps(dict(status=result['status'],complete=result['complete'],executor_rc=rc)));return rc
 except (ValueError,OSError,KeyError,TypeError,AssertionError) as exc:print('REFUSE '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
