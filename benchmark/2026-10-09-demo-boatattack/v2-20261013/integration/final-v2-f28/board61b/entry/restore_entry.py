#!/usr/bin/env python3
"""Explicit v2 staging: frozen RouteB check/restore, then Boat; no reboot or acceptance bypass."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
SERIAL='61b0657200000000000000000324012c'
R5='a5eb301d77f92c1755c53c93e9d59ca60d5da5030b77f495d5859b2cf68012d8'
R2='6a5b6bf5a1284304e14fa23def844db36b59c47b014faee1b981fe8bda3bd759'
BUILDER='8f8b1553eff79d934383f62e014c5a5869d98f533f8fe8da972b1e1a67594367'
PROVIDER='c8d17ab84da3ce3f3d7ec2f431625735b21e9171a19dc25def801aa9cd8728b7'
def need(ok,msg):
    if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):
    with Path(p).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
def path(text,base):
    p=Path(str(text).replace('$WORKSPACES',os.environ.get('WORKSPACES',str(HERE.parents[5]))))
    return p.resolve() if p.is_absolute() else (base/p).resolve()
def pin(ref,base,expected=None):
    need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'typed independent pin required')
    p=path(ref['path'],base);need(sha(p)==ref['sha256'] and (expected is None or ref['sha256']==expected),'input pin drift: '+ref['path']);return p

def prepare(args):
    recipe=args.v2_recipe.resolve();need(sha(recipe)==args.recipe_sha256,'recipe independent pin mismatch')
    data=read(recipe);base=recipe.parent
    need(data['schema']=='boat-v2-staged-restore/v1' and data['serial']==SERIAL,'recipe schema/61b scope')
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
    rb=data['route_b'];boat=data['boat'];need(rb['mode'] in ('verify-existing','restore'),'explicit RouteB mode')
    proofpath=pin(rb['realization'],base);proof=read(proofpath)
    need(proof['schema']=='exact-realization/v1' and proof['parameters']['serial']==SERIAL,'RouteB proof serial')
    boot=proof['parameters']['boot_id'];need(boot==data['boot_id'],'origin boot binding')
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
        command=[sys.executable,str(entry),'--checker','realization','--realization',str(proofpath),'--serial',SERIAL,'--boot-id',boot,'--hdc',str(hdc),'--out',str(args.out/'route-b-selfcheck.json')]
        steps.append(('route-b-selfcheck',command))
    else:
        entry=pin(rb['entry'],base,R2);manifest=pin(rb['prepared_manifest'],base)
        admission=pin(rb['admission'],base);auth=pin(rb['authorization'],base);lock=pin(rb['lock_tool'],base)
        builder=pin(rb['history_builder'],base,BUILDER);adapter=pin(rb['restore_adapter'],base)
        need(adapter==entry.parent/'restore.py','original adjacent r2 adapter required')
        txn=args.out/'route-b-transaction'
        command=[sys.executable,str(entry),'--realization',str(proofpath),'--prepared',str(manifest.parent),'--admission',str(admission),'--admission-sha256',rb['admission']['sha256'],'--authorization',str(auth),'--authorization-sha256',rb['authorization']['sha256'],'--lock-tool',str(lock),'--lock-tool-sha256',rb['lock_tool']['sha256'],'--transaction-action','apply','--execute','--out',str(txn)]
        steps.append(('route-b-restore',command))
        command=[sys.executable,str(builder),'--realization',str(proofpath),'--origin-realization',str(proofpath),'--prepared-manifest',str(manifest),'--admission',str(admission),'--restore-adapter',str(adapter),'--execution-receipt',str(txn)+'.realization-receipt.json','--transaction-dir',str(txn),'--execution-cwd',str(path(rb['execution_cwd'],base)),'--out',str(args.out/'activation-binding.json')]
        steps.append(('route-b-history487',command))
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
        need(r['realization']['sha256']==data['route_b']['realization']['sha256'],'RouteB proof receipt binding')
        checks={x['target']:x for x in r['checks']}
        for row in plan['preserved']:
            if row['target'] in {x['target'] for x in plan['binds']} or row['target'].endswith('/com.Unity3d.BoatAttackDay/android/base.apk'):continue
            check=checks[row['target']];need(check['equal'] is True and check['actual']==row['before']['sha256'],'RouteB preserved SHA differs from live check')
    elif name=='route-b-restore':
        r=read(str(out/'route-b-transaction')+'.realization-receipt.json')
        need(type(r.get('executor_rc')) is int and r['executor_rc']==0 and r.get('action')=='apply','actual r2 executor success required')
    elif name=='route-b-history487':
        binding=read(out/'activation-binding.json')
        need(binding['schema']=='exact-activation-selfcheck-binding/v1' and not binding.get('synthetic') and len(binding['member_receipts'])==487,'admitted full487 binding required')
        need(len(list((out/'route-b-transaction').glob('placed-[0-9][0-9][0-9].json')))==487,'actual487 placed receipts required')
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
