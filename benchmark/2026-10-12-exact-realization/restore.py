"""Explicit realization restoration admission; unchanged v6 executor underneath.

Preview materializes a separately reviewable enabled plan, never authority.
No original seal is forged. The two existing outer roles remain separate.
"""
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import realization as r


def prepare(proof,out):
    r.need(proof.get('purpose')!='same-board-selfcheck','same-board proof has no restoration authority')
    out=Path(out);r.need(not out.exists(),'fresh restoration preview directory required')
    shutil.copytree(proof['package'],out)
    startup=out/'payload/startup.env';data=startup.read_text()
    changes=[]
    for field,old,new in [('STARTUP_APPROVED_BY','PENDING','outer(codex)'),('STARTUP_ENABLED','0','1')]:
        before=f"{field}='{old}'";after=f"{field}='{new}'"
        r.need(data.count(before)==1,'startup activation field drift: '+field)
        changes.append({'field':field,'before':old,'after':new,'reason':'prospective startup policy; separate outer admission required'})
        data=data.replace(before,after)
    startup.write_text(data);(out/'payload/startup.expected.sha256').write_text(r.digest(startup)+'\n')
    plan=r.read(out/'plan.json');plan['execution_enabled']=True
    for row in plan['members']:row['sha256']=r.digest(out/row['source'].removeprefix('$PACKAGE/'))
    r.write(out/'plan.json',plan)
    # binding/derivation retain the exact disabled baseline provenance.
    r.write(out/'activation.json',{'schema':'exact-startup-preview/v1','status':'NOT_AUTHORIZED','proof_sha256':proof['proof_sha256'],
        'changes':changes,'original_seal':proof['source_seal'],'source_identity':proof['source_identity'],'device_calls':0})
    inventory=[{'path':str(p.relative_to(out)),'sha256':r.digest(p),'bytes':p.stat().st_size}
               for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json']
    r.write(out/'manifest.json',{'schema':'exact-restoration-package/v1','status':'NOT_AUTHORIZED','files':inventory,
        'proof_sha256':proof['proof_sha256'],'plan_sha256':r.digest(out/'plan.json'),'executor_sha256':r.digest(out/'executor.py')})
    return {'status':'PREVIEW_NOT_RESTORED','source_identity':proof['source_identity'],'source_seal':proof['source_seal'],
        'realization_sha256':proof['proof_sha256'],'prepared_manifest_sha256':r.digest(out/'manifest.json'),
        'plan_sha256':r.digest(out/'plan.json'),'executor_sha256':r.digest(out/'executor.py'),
        'target_sha256':{x['target']:x['sha256'] for x in plan['members']},'device_calls':0,'authority_created':False}

def checked_package(proof,package):
    package=Path(package).resolve()
    with tempfile.TemporaryDirectory(prefix='exact-activation-check-') as td:
        expected=Path(td)/'package';receipt=prepare(proof,expected)
        r.need(r.digest(package/'manifest.json')==receipt['prepared_manifest_sha256'],'restoration manifest drift')
        for row in r.read(expected/'manifest.json')['files']:
            path=package/row['path'];r.need(path.is_file() and r.digest(path)==row['sha256'],'restoration member drift: '+row['path'])
    return r.read(package/'plan.json'),receipt

def guard(proof,package,admission_ref,authorization_ref,base,now=None,action='apply'):
    now=time.time() if now is None else now
    plan,receipt=checked_package(proof,package)
    admission_path=r.pin(admission_ref,base);ad=r.read(admission_path)
    r.need(ad.get('schema')=='exact-realization-admission/v1' and ad.get('admitted') is True,'missing explicit realization admission')
    r.need(ad.get('signed_by')=='outer(claude)','original spare-rehearsal outer role required')
    r.need(ad.get('generator_sha256')==r.digest(Path(__file__)),'restore adapter independent self pin')
    for key,value in [('realization_sha256',proof['proof_sha256']),('source_identity_sha256',proof['source_identity']['sha256']),
                      ('source_seal_sha256',proof['source_seal']['sha256'] if proof['source_seal'] else None),
                      ('prepared_manifest_sha256',receipt['prepared_manifest_sha256']),('plan_sha256',receipt['plan_sha256']),
                      ('executor_sha256',r.EXECUTOR_SHA),('serial',proof['parameters']['serial'])]:
        r.need(key in ad and ad[key]==value,'admission binding drift: '+key)
    r.need(type(ad.get('expires_epoch')) in (int,float) and ad['expires_epoch']>now,'admission expired')
    r.need(ad.get('target_sha256')==receipt['target_sha256'],'admission complete target map differs')
    identity_path=r.pin(proof['source_identity'],Path(proof['request']['path']).parent)
    r.need(not r.read(identity_path).get('synthetic') and not proof['parameter_evidence'].get('synthetic'),'synthetic inputs cannot execute')
    r.need(not any(x['parameter_evidence'].get('synthetic') for x in proof.get('source_window_normalization',[])),'synthetic source evidence cannot execute')
    authorization=r.pin(authorization_ref,base)
    executor=r.load(Path(package)/'executor.py','exact_unchanged_executor')
    r.need(r.digest(Path(package)/'executor.py')==r.EXECUTOR_SHA,'executor changed')
    # Original validation, including every known before image, directory,
    # prerequisite/tool, action, outer(codex), board, boot and expiry.
    plan['_sha']=r.digest(Path(package)/'plan.json')
    auth=executor.validate(plan,authorization,now=now,authorization_sha256=authorization_ref['sha256'])
    r.need(auth.get('derived_manifest_sha256')==receipt['prepared_manifest_sha256'],'independent derived manifest authorization')
    r.need(action in {'apply','rollback'} and ad.get('action')==action,'admission action mismatch')
    r.need(ad.get('boot_id')==auth.get('boot_id'),'admission current boot drift')
    if action=='apply':r.need(auth.get('boot_id')==proof['parameters']['boot_id'],'current authorization boot drift')
    r.need(isinstance(auth.get('holder'),str) and auth['holder'] and ad.get('holder')==auth['holder'],'external holder binding')
    return plan,ad,auth,authorization,receipt

def execute(proof,package,admission_ref,authorization_ref,lock_ref,base,out,runner=subprocess.run,action='apply'):
    plan,ad,auth,authorization,receipt=guard(proof,package,admission_ref,authorization_ref,base,action=action)
    lock=r.pin(lock_ref,base)
    r.need(ad.get('lock_tool')==lock_ref,'independent lock tool pin')
    held=runner(['bash',str(lock),'held',plan['serial']],capture_output=True,text=True,timeout=15)
    r.need(held.returncode==0 and not held.stderr and held.stdout.strip()==auth['holder'],'external held lock differs')
    cmd=[sys.executable,str(Path(package)/'executor.py'),'--plan',str(Path(package)/'plan.json'),'--execute',
         '--authorization',str(authorization),'--authorization-sha256',authorization_ref['sha256'],
         '--out',str(out),'--action',action]
    run=runner(cmd,capture_output=True,text=True,timeout=900)
    sys.stdout.write(run.stdout);sys.stderr.write(run.stderr)
    return {'schema':'exact-restoration-receipt/v1','realization_sha256':proof['proof_sha256'],
        'source_identity':proof['source_identity'],'source_seal':proof['source_seal'],
        'action':action,'plan_sha256':receipt['plan_sha256'],'command':cmd,'executor_rc':run.returncode,
        'seal_signed':False,'ui_accepted':False},run.returncode
