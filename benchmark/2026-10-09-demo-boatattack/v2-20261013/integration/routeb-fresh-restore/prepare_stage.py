#!/usr/bin/env python3
"""Offline exact successor recipe. Never grants execution or renews a completed grant."""
import argparse,json,sys
from pathlib import Path
import prepare as p
import restore_entry as entry
import receipt_check
HERE=Path(__file__).resolve().parent

def ref(path):
 path=Path(path).resolve()
 try:name=p.portable(path)
 except ValueError:name=str(path)
 return dict(path=name,sha256=p.sha(path))

def build(args):
 recipe,plan,_=p.verify(args.directory_recipe,args.directory_recipe_sha256)
 p.need(not args.out.exists(),'fresh stage output')
 dep=entry.pin(dict(path=str(args.deployment.resolve()),sha256=args.deployment_sha256),Path.cwd());deployment=p.read(dep)
 seal=entry.pin(dict(path=str(args.seal.resolve()),sha256=args.seal_sha256),Path.cwd())
 hdc=entry.pin(dict(path=str(args.hdc.resolve()),sha256=args.hdc_sha256),Path.cwd())
 provider=[v for v in deployment['providers'] if v.get('layer')=='boatattack'];p.need(len(provider)==1,'one Boat provider')
 need_pair=(args.completed_receipt is not None)==(args.completed_receipt_sha256 is not None);p.need(need_pair,'paired completed receipt pin')
 mode='resume-completed-restore' if args.completed_receipt else 'restore-directory-complete'
 if args.completed_receipt:receipt_check.admit(args.directory_recipe,args.directory_recipe_sha256,args.completed_receipt,args.completed_receipt_sha256)
 live=p.MAIN/'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py';p.need(p.sha(live)==entry.R5,'frozen original R5 entry')
 rb=dict(mode=mode,realization=recipe['origin']['original_realization'],activation_binding=recipe['origin']['original_activation_binding'],directory_recipe=ref(args.directory_recipe),entry=ref(HERE/'executor.py'),live_entry=ref(live),hdc=ref(hdc))
 if args.completed_receipt:rb['completed_receipt']=ref(args.completed_receipt)
 data=dict(schema='boat-v2-staged-restore/v1',phase='placement',serial=recipe['serial'],boot_id=recipe['boot_id'],execution_enabled=False,signed_by=None,execution_cwd=p.portable(p.MAIN),successor_programs={name:ref(HERE/file) for name,file in [('entry','restore_entry.py'),('history_checker','receipt_check.py'),('core','executor.py'),('generator','prepare.py')]},route_b=rb,boat=dict(program=provider[0]['program'],deployment=ref(dep),seal=ref(seal)))
 args.out.mkdir(parents=True);output=args.out/'recipe.disabled.json';p0=json.dumps(data,indent=2)+'\n';output.write_text(p0)
 prepared=entry.prepare(argparse.Namespace(v2_recipe=output,recipe_sha256=p.sha(output),out=args.out/'execution',execute=False))
 (args.out/'preview.json').write_text(json.dumps(dict(status='OFFLINE_V2_STAGE_PREVIEW',mode=mode,steps=[dict(name=n,argv=argv) for n,argv in prepared[3]],device_calls=0,execution_authority=False),indent=2)+'\n')
 return output

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('directory-recipe','deployment','seal','hdc'):
  ap.add_argument('--'+name,type=Path,required=True);ap.add_argument('--'+name+'-sha256',required=True)
 ap.add_argument('--completed-receipt',type=Path);ap.add_argument('--completed-receipt-sha256');ap.add_argument('--out',type=Path,required=True)
 try:
  path=build(ap.parse_args());print(json.dumps(dict(status='DISABLED_SUCCESSOR_PREPARED',recipe=ref(path),device_calls=0)));return 0
 except (ValueError,KeyError,TypeError,OSError) as exc:print('REFUSE '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
