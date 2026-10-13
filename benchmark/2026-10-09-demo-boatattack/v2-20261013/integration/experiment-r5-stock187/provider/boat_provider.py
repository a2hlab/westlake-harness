#!/usr/bin/env python3
"""Standard t5 argv, exact Boat placement/rollback only; never claims post-boot restoration."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def need(ok, why):
    if not ok: raise ValueError(why)

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def save(p,x): Path(p).write_text(json.dumps(x,indent=2)+'\n')
def resolve(text,base):
    p=Path(str(text).replace('$WORKSPACES',os.environ['WORKSPACES']))
    return p.resolve() if p.is_absolute() else (base/p).resolve()
def pinned(ref,base):
    need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'typed independent pin required')
    p=resolve(ref['path'],base);need(digest(p)==ref['sha256'],'pin drift: '+ref['path']);return p


def run(a):
    base=Path(a.deployment).resolve().parent;dep=read(a.deployment);seal=read(a.seal)
    need(dep.get('schema')=='demo-restore-deployment/v1','deployment schema')
    need(seal.get('schema')=='demo-seal/v1' and seal.get('seal_stage')=='v2','explicit v2 seal/candidate required')
    need(a.serial=='5cd1e3dd00000000000000000923012c' and seal.get('serial')==a.serial,'5cd candidate only')
    rows=[p for p in dep['providers'] if p.get('layer')=='boatattack'];need(len(rows)==1,'one Boat provider required');p=rows[0]
    need(pinned(p['program'],base)==Path(__file__).resolve(),'provider self-pin')
    need(p['common']['sha256']=='df39c939529c9b571091c6df1c11b10c19003298d3f1f42bc98ce0e8ca915341','reviewed common SHA')
    common=pinned(p['common'],base);executor=pinned(p['executor'],base);planpath=pinned(p['prepared'],base)
    # Common and executor are distinct typed pins. No dynamic code is loaded before pin validation.
    spec=importlib.util.spec_from_file_location('boat_candidate_common',common);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    need(common.name=='provider_common.py' and callable(c.pinned),'original common required')
    need(p['serial']==a.serial and p['action'] in ('apply','rollback'),'provider scope/action')
    plan=read(planpath);need(plan['serial']==a.serial,'plan serial')
    need(plan['installer_sha256']==p['executor']['sha256'],'executor independent/self pin differs')
    expected={r['target']:r['sha256'] for r in plan['members']+plan['binds']}
    need(len(expected)==16 and len(p['targets'])==16 and set(p['targets'])==set(expected),'complete16 Boat target coverage')
    overlays=[r for r in seal.get('overlay_deployments',[]) if r.get('id')=='boatattack']
    need(len(overlays)==1 and overlays[0]['state']=='active','active declared Boat layer required')
    need({r['target']:r['sha256'] for r in overlays[0]['files']}==expected,'Boat declaration differs from exact package')
    allfiles={}
    for group in seal['files'].values():
        for target,h in group.items():
            need(target not in allfiles or allfiles[target]==h,'conflicting seal SHA');allfiles[target]=h
    need(all(allfiles.get(t)==h for t,h in expected.items()),'sealed Boat SHA mismatch')
    executor_spec=importlib.util.spec_from_file_location('boat_candidate_executor',executor)
    e=importlib.util.module_from_spec(executor_spec);executor_spec.loader.exec_module(e)
    e.validate(plan,e.core_for(plan))
    if dep.get('execution_enabled') is not True:
        print(json.dumps({'status':'DISABLED_PREVIEW','targets':16,'placement_members':10,'boot_binds':6,
                         'pending':plan.get('pending_capture',[]),'device_calls':0,'restored':False}));return 0
    need(not dep.get('synthetic') and not seal.get('synthetic'),'synthetic execution forbidden')
    need(plan.get('execution_enabled') is True and not plan.get('pending_capture'),'incomplete/disabled plan')
    authorization=pinned(p['authorization'],base)
    out=Path(a.out).resolve();need(not out.exists(),'fresh provider output required')
    txn=out/'transaction' if p['action']=='apply' else resolve(p['transaction_dir'],base)
    if p['action']=='rollback':
        need(pinned(p['transaction'],base)==txn/'transaction.json','rollback original transaction pin')
    out.mkdir(parents=True)
    command=[sys.executable,str(executor),'--plan',str(planpath),'--action',p['action'],'--execute',
             '--authorization',str(authorization),'--authorization-sha256',p['authorization']['sha256'],'--out',str(txn)]
    receipt={'schema':'boat-provider-placement/v1','serial':a.serial,'plan_sha256':digest(planpath),
             'action':p['action'],'restored':False,'reboots':0,'command':command,'executor_rc':None}
    try:
        result=subprocess.run(command,capture_output=True,timeout=2700)
        (out/'executor.stdout').write_bytes(result.stdout);(out/'executor.stderr').write_bytes(result.stderr)
        receipt['executor_rc']=result.returncode;need(result.returncode==0,'Boat executor failed')
        if p['action']=='apply':
            placed=read(txn/'placed.json');need(placed.get('state')=='PLACED_ONLY','missing actual placement receipt')
            tx=read(txn/'transaction.json')
            backups=[dict(target=r['target'],before=r['before'],backup='backup-%03d'%n if r['before']['exists'] else None,candidate_sha256=r['sha256']) for n,r in enumerate(plan['members'])]
            need(tx==dict(plan_sha256=digest(planpath),serial=a.serial,boot_id=plan['boot_id'],backups=backups),'actual transaction identity/member mismatch')
            protected=read(txn/'preserved-verified.json')
            need(protected==dict(plan_sha256=digest(planpath),serial=a.serial,boot_id=plan['boot_id'],count=len(plan['preserved']),success=True),'protected RouteB readback incomplete')
            need(len(list(txn.glob('placed-[0-9][0-9][0-9].json')))==10,'exact10 placement receipts')
            for n,row in enumerate(plan['members']):
                member=read(txn/('placed-%03d.json'%n))
                need(member=={'target':row['target'],'sha256':row['sha256']},'placement member receipt mismatch')
            receipt['status']='PLACED_PENDING_AUTHORIZED_SINGLE_BOOT'
        else:
            results=list(txn.glob('rollback-*.json'));need(results,'rollback receipt missing')
            latest=max(results,key=lambda f:f.name)
            need(read(latest).get('state')=='RESTORED_RETAINED_AUDIT_VERIFIED' and read(latest).get('success') is True,'rollback incomplete')
            receipt['status']='ROLLED_BACK_RETAINED_AUDIT'
        return 0
    except subprocess.TimeoutExpired as exc:
        (out/'executor.stdout').write_bytes(exc.stdout or b'');(out/'executor.stderr').write_bytes(exc.stderr or b'')
        receipt.update(status='TIMEOUT_PRESERVE_TRANSACTION',error='2700 second execution budget exceeded');return 124
    except (ValueError,OSError,KeyError) as exc:
        receipt.update(status='INCOMPLETE_PRESERVE_TRANSACTION',error=str(exc));return 2
    finally:save(out/'receipt.json',receipt)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['seal','serial','deployment','out']:ap.add_argument('--'+name,required=True)
    try:return run(ap.parse_args())
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('BOAT PROVIDER REFUSED: '+str(exc),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
