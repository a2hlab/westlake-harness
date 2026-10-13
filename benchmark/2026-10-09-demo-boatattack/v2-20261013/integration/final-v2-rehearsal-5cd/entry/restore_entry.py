#!/usr/bin/env python3
"""Explicit v2 staging: frozen RouteB check/restore, then Boat; no reboot or acceptance bypass."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
SERIAL='5cd1e3dd00000000000000000923012c'
R5='a5eb301d77f92c1755c53c93e9d59ca60d5da5030b77f495d5859b2cf68012d8'
R2='6a5b6bf5a1284304e14fa23def844db36b59c47b014faee1b981fe8bda3bd759'
DIRECTORY_ENTRY='302c47c1fea1c1f2e327435a0b94b19558c09fab4bb24173531fa952e749075c'
BUILDER='8f8b1553eff79d934383f62e014c5a5869d98f533f8fe8da972b1e1a67594367'
PROVIDER='641a82eeb1064f747ccccff1f990e97b72e7cdbd279220e06f02269070e12851'
def need(ok,msg):
    if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):
    with Path(p).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
def path(text,base):
    p=Path(str(text).replace('$WORKSPACES',os.environ.get('WORKSPACES',str(next(p for p in HERE.parents if (p/"scripts/lab/lab_paths.py").is_file()).parent))))
    return p.resolve() if p.is_absolute() else (base/p).resolve()
def pin(ref,base,expected=None):
    need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'typed independent pin required')
    p=path(ref['path'],base);need(sha(p)==ref['sha256'] and (expected is None or ref['sha256']==expected),'input pin drift: '+ref['path']);return p

def prepare(args):
    recipe=args.v2_recipe.resolve();need(sha(recipe)==args.recipe_sha256,'recipe independent pin mismatch')
    data=read(recipe);base=recipe.parent
    need(data['schema']=='boat-v2-staged-restore/v1' and data['serial']==SERIAL,'recipe schema/5cd scope')
    need(data.get('signed_by') is None,'recipe cannot sign seal')
    if data.get('phase')=='preinstall':
        request=pin(data['preinstall']['request'],base);req=read(request)
        need(req['serial']==SERIAL and req['boot_id']==data['boot_id'],'preinstall scope/boot')
        entry=pin(data['preinstall']['program'],base)
        need(entry==(HERE/'prepare_boat.py').resolve(),'only local reviewed missing-only entry')
        if args.execute:need(data.get('execution_enabled') is True and not data.get('synthetic'),'disabled/synthetic recipe')
        command=[sys.executable,str(entry),'--request',str(request),'--request-sha256',data['preinstall']['request']['sha256'],'--out',str(args.out/'preinstall')]
        if args.execute:command.append('--execute')
        return data,None,None,[('boat-preinstall',command)]
    need(data.get('phase')=='placement','explicit preinstall or placement phase required')
    rb=data['route_b'];boat=data['boat'];need(rb['mode'] in ('verify-existing','restore-directory-complete'),'explicit RouteB mode')
    proofpath=pin(rb['realization'],base);proof=read(proofpath)
    need(proof['schema']=='exact-realization/v1' and proof['parameters']['serial']==SERIAL,'RouteB proof serial')
    boot=data['boot_id'] # Current readback boot is independent of historical placement boot.
    need(proof['parameters']['host_uid']==proof['parameters']['host_gid']==20011300 and proof['parameters']['control_root']=='/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012','actual5cd RouteB derivation')
    sealpath=pin(boat['seal'],base);sealp=read(sealpath)
    need(sealp['serial']==SERIAL and sealp['seal_stage']=='v2','v2 full identity required')
    dep_path=pin(boat['deployment'],base);dep=read(dep_path)
    providers=[p for p in dep['providers'] if p.get('layer')=='boatattack'];need(len(providers)==1,'one Boat provider')
    provider=pin(boat['program'],base,PROVIDER)
    need(pin(providers[0]['program'],dep_path.parent,PROVIDER)==provider and providers[0]['action']=='apply','same apply provider')
    planpath=pin(providers[0]['prepared'],dep_path.parent);plan=read(planpath)
    executor=pin(providers[0]['executor'],dep_path.parent)
    need(executor==(HERE.parent/'provider/installer.py').resolve() and plan['installer_sha256']==providers[0]['executor']['sha256'],'r2 UID-checked executor required')
    need(plan['serial']==SERIAL and plan['boot_id']==boot,'Boat/RouteB serial and origin boot differ')
    if args.execute:
        need(data.get('execution_enabled') is True and not data.get('synthetic'),'disabled/synthetic recipe')
        need(dep.get('execution_enabled') is True and plan.get('execution_enabled') is True and not plan.get('synthetic'),'disabled/synthetic Boat')
    steps=[]
    if rb['mode']=='verify-existing':
        entry=pin(rb['entry'],base,R5);hdc=pin(rb['hdc'],base)
        binding_path=pin(rb['activation_binding'],base)
        binding=read(binding_path)
        need(binding['realization']['sha256']==rb['realization']['sha256'] and not binding.get('synthetic'),'5cd actual activation binding')
        command=[sys.executable,str(entry),'--checker','activation','--activation-binding',str(binding_path),'--binding-sha256',rb['activation_binding']['sha256'],'--serial',SERIAL,'--boot-id',boot,'--hdc',str(hdc),'--out',str(args.out/'route-b-selfcheck.json')]
        steps.append(('route-b-selfcheck',command))
    else:
        entry=pin(rb['entry'],base,DIRECTORY_ENTRY)
        recipe_path=pin(rb['directory_recipe'],base);directory=read(recipe_path)
        need(directory['mode']=='restore-then-complete','fresh complete restore recipe required; no historical replay authority')
        need(directory['core']['realization']['sha256']==rb['realization']['sha256'],'same RouteB restore origin')
        manifest=read(pin(directory['supplement']['manifest'],recipe_path.parent))
        need(manifest['serial']==SERIAL and manifest['boot_id']==boot,'directory completion serial/boot')
        command=[sys.executable,str(entry),'--directory-recipe',str(recipe_path),'--recipe-sha256',rb['directory_recipe']['sha256'],'--out',str(args.out/'route-b-completed')]
        if args.execute:command.append('--execute')
        steps.append(('route-b-complete',command))
    steps.append(('boat-placement',[sys.executable,str(provider),'--seal',str(sealpath),'--serial',SERIAL,'--deployment',str(dep_path),'--out',str(args.out/'boat')]))
    return data,plan,planpath,steps

def check_step(name,out,plan,planpath,data):
    if name=='boat-preinstall':
        r=read(out/'preinstall/preinstall-receipt.json')
        need(r.get('status')=='PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE' and r.get('serial')==SERIAL and r.get('boot_id')==data['boot_id'],'preinstall incomplete')
        need(r.get('stock_libraries_preserved') is True and r.get('provider_compiled') is False,'fresh capture barrier missing')
    elif name=='route-b-selfcheck':
        r=read(out/'route-b-selfcheck.json')
        need(r.get('mode')=='live-readonly' and r.get('status')=='PASS' and r.get('passed') is True and not r.get('synthetic'),'real live RouteB selfcheck required')
        need(r['serial']==SERIAL and r['boot_before']==r['boot_after']==data['boot_id'],'RouteB selfcheck boot changed')
        need(r['activation']['realization']['sha256']==data['route_b']['realization']['sha256'] and r['activation']['binding']['sha256']==data['route_b']['activation_binding']['sha256'],'RouteB activated proof receipt binding')
        checks={x['target']:x for x in r['checks']}
        for row in plan['preserved']:
            if row['target'] in {x['target'] for x in plan['binds']} or row['target'].endswith('/com.Unity3d.BoatAttackDay/android/base.apk'):continue
            check=checks[row['target']];need(check['equal'] is True and check['actual']==row['before']['sha256'],'RouteB preserved SHA differs from live check')
    elif name=='route-b-complete':
        root=out/'route-b-completed';r=read(root/'recipe-receipt.json')
        need(r.get('complete') is True and type(r.get('executor_rc')) is int and r['executor_rc']==0 and r.get('core_rc')==0 and r.get('reboots')==0,'actual complete r2+r4b restoration required')
        binding=read(root/'activation-binding.json')
        need(binding['schema']=='exact-activation-selfcheck-binding/v1' and not binding.get('synthetic') and len(binding['member_receipts'])==487 and sha(root/'activation-binding.json')==r['history_binding_sha256'],'all487 history binding required')
        applied=root/'directory-transaction/applied.json';a=read(applied)
        need(sha(applied)==r['directory_receipt_sha256'] and type(a.get('executor_rc')) is int and a['executor_rc']==0 and a['state'] in ('CREATED_VERIFIED','ALREADY_EQUAL'),'exact empty directory completion required')
    elif name=='boat-placement':
        r=read(out/'boat/receipt.json')
        need(type(r.get('executor_rc')) is int and r['executor_rc']==0 and r.get('status')=='PLACED_PENDING_AUTHORIZED_SINGLE_BOOT' and r.get('restored') is False and r.get('reboots')==0,'Boat actual placement incomplete')
        need(r['serial']==SERIAL and r['plan_sha256']==sha(planpath),'Boat receipt scope')

def run(args,runner=subprocess.run):
    args.out=args.out.resolve();need(not args.out.exists(),'fresh output required')
    data,plan,planpath,steps=prepare(args)
    if not args.execute:
        print(json.dumps({'status':'OFFLINE_V2_STAGE_PREVIEW','steps':[{'name':n,'argv':a} for n,a in steps],'device_calls':0,'restored':False}));return 0
    args.out.mkdir(parents=True)
    receipt={'schema':'boat-v2-staged-restore-receipt/v1','recipe_sha256':args.recipe_sha256,'serial':SERIAL,'boot_id':data['boot_id'],'steps':[], 'restored':False,'reboots':0,'sealed':False,'status':'INCOMPLETE_PRESERVE_EVIDENCE'}
    try:
        for name,argv in steps:
            # Each reviewed child keeps its own original timeout/admission/lock.
            # No parent timeout can kill a legal child transaction mid-write.
            result=runner(argv,capture_output=True,text=True,cwd=path(data.get('execution_cwd','.'),args.v2_recipe.resolve().parent))
            (args.out/(name+'.stdout')).write_text(result.stdout);(args.out/(name+'.stderr')).write_text(result.stderr)
            receipt['steps'].append({'name':name,'argv':argv,'rc':result.returncode})
            need(result.returncode==0,name+' failed; STOP before next stage')
            check_step(name,args.out,plan,planpath,data)
        receipt['status']='PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE' if data['phase']=='preinstall' else 'PLACED_PENDING_AUTHORIZED_SINGLE_BOOT_AND_FINAL_SELFCHECK';return 0
    except (ValueError,KeyError,TypeError,OSError) as e:receipt['error']=str(e);return 2
    finally:save(args.out/'staged-receipt.json',receipt)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--v2-recipe',type=Path,required=True);ap.add_argument('--recipe-sha256',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--execute',action='store_true')
    try:return run(ap.parse_args())
    except (ValueError,KeyError,TypeError,OSError) as e:print('V2 STAGE REFUSED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
