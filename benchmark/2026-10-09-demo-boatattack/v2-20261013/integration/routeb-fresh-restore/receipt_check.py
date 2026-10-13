"""Readonly admission of this new487 execution; historical pins never renew authority."""
from pathlib import Path
import executor as e
p=e.p

def admit(recipe_path,recipe_sha,receipt_path,receipt_sha):
 p.need(p.sha(receipt_path)==receipt_sha,'completed receipt independent pin')
 recipe,plan,planpath=p.verify(recipe_path,recipe_sha);recipe['_sha']=recipe_sha;plan['_sha']=p.sha(planpath)
 r=p.read(receipt_path);p.need(r.get('schema')=='routeb-current-restore-receipt/v1' and r.get('complete') is True and type(r.get('executor_rc')) is int and r['executor_rc']==0,'new restoration executor_rc0 required')
 p.need(r['status']=='RESTORED487_WITH_DIRECTORY_COMPLETION_NOT_UI_ACCEPTANCE' and r['action']=='apply' and r['reboots']==0 and r['placed_count']==487,'full current restoration receipt')
 for key,value in dict(recipe_sha256=recipe_sha,plan_sha256=plan['_sha'],serial=plan['serial'],boot_id=plan['boot_id'],original_realization=plan['fresh_rebase']['original_realization'],original_activation_binding=plan['fresh_rebase']['original_activation_binding']).items():p.need(r.get(key)==value,'restoration result scope '+key)
 auth=p.checked(r['authorization']);ad=p.checked(r['admission']);a=p.read(auth);d=p.read(ad)
 # Like original history admission, validate a once-valid grant without reusing it for execution.
 when=min(a['apply_deadline_epoch'],a['expires_epoch'],d['expires_epoch'])-1
 e.guard(recipe,plan,auth,p.sha(auth),ad,p.sha(ad),'apply',now=when)
 core=p.load(p.checked(plan['fresh_rebase']['original_executor']),'routeb_receipt_original_core')
 out=Path(receipt_path).resolve().parent
 p.need(r['member_receipts']==e.member_receipts(core,plan,out) and r['transaction']==p.pin(out/'transaction.json'),'exact current487 records')
 directory=p.checked(r['directory_receipt']);p.need(directory==out/'directory-complete.json','directory receipt location')
 p.need(p.read(directory)==dict(state='EXISTING_DIRECTORIES_VERIFIED',count=29,directories=plan['fresh_rebase']['all_directories'],reboots=0,user_data_deleted=False),'current29 directory completion')
 cfg=next(row for row in plan['members'] if row['target']==core.CFG)
 p.need(r['retained_audit']==[dict(target=e.stage_path(plan,core.CFG),observed=dict(exists=True,sha256=cfg['sha256'],**cfg['after']))],'declared cfg audit stage')
 return dict(status='ADMITTED_COMPLETED_CURRENT487_HISTORY',serial=plan['serial'],boot_id=plan['boot_id'],recipe=p.pin(recipe_path),receipt=p.pin(receipt_path),placed_count=487,directory_count=29,execution_authority=False)
