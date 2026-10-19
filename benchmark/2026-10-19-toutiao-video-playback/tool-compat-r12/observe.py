#!/usr/bin/env python3
"""Default refusal. Outer owns isolated processes, lock and forwarding."""
import argparse,json,signal,subprocess,sys
from pathlib import Path
from policy import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--admission',required=True);p.add_argument('--out',required=True);p.add_argument('--execute',action='store_true');p.add_argument('--validate-only',action='store_true');args=p.parse_args()
 out=path(args.out);out.mkdir(parents=True,exist_ok=False)
 try:
  need(args.execute != args.validate_only,'explicit execute or validate-only required')
  a=json.loads(path(args.admission).read_text());validate(a)
  (out/'admission.json').write_text(json.dumps(a,indent=2)+'\n')
  if args.validate_only:(out/'preview.json').write_text('{"device_calls":0,"status":"LOCAL_VALIDATION_ONLY"}\n');return 0
  root=Path(__file__).resolve().parent
  body='import sys; sys.path.insert(0,'+repr(str(root))+'); import engine; engine.entry('+repr(str(out/'admission.json'))+','+repr(str(out))+')'
  cmd=[str(path(a['host']['path'])),'--no-lldbinit','--batch','-o','script '+body,'-o','quit']
  (out/'invocation.json').write_text(json.dumps({'argv':cmd,'source_pins':{f.name:sha(f) for f in root.glob('*.py')},'observation_limit':60,'outer_recovery_required_on_any_missing_receipt':True},indent=2)+'\n')
  with (out/'host.stdout.txt').open('wb') as stdout,(out/'host.stderr.txt').open('wb') as stderr:
   proc=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,start_new_session=True);timed=False
   try:rc=proc.wait(timeout=85)
   except subprocess.TimeoutExpired:
    timed=True;proc.send_signal(signal.SIGTERM)
    try:rc=proc.wait(timeout=8)
    except subprocess.TimeoutExpired:proc.kill();rc=proc.wait()
  (out/'host.rc.json').write_text(json.dumps({'rc':rc,'local_timeout':timed})+'\n')
  r=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else {}
  return 0 if not timed and rc==0 and r.get('two_hits') and r.get('cleanup',{}).get('verified') else 2
 except Exception as ex:
  (out/'refusal.json').write_text(json.dumps({'error':str(ex),'status':'REFUSED','scope':'tool compatibility only'})+'\n');return 2
if __name__=='__main__':sys.exit(main())
