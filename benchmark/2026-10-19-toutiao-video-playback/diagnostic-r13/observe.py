#!/usr/bin/env python3
"""Explicit outer-only execution. Validation/preview never invokes HDC or LLDB."""
import argparse, json, os, signal, subprocess, sys, time
from pathlib import Path
from core import validate, path, sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--admission',required=True);p.add_argument('--port',required=True,type=int);p.add_argument('--out',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    out=path(a.out);out.mkdir(parents=True,exist_ok=False)
    try:
        obj=json.loads(path(a.admission).read_text());validate(obj)
        if not 1024<=a.port<=65535:raise ValueError('port range')
        (out/'admission.json').write_text(json.dumps(obj,indent=2)+'\n')
        root=Path(__file__).resolve().parent
        pins={x.name:sha(x) for x in root.glob('*.py')}
        body='import sys; sys.path.insert(0, '+repr(str(root))+'); import observer; observer.entry('+repr(str(out/'admission.json'))+', '+repr(str(out))+', '+str(a.port)+')'
        argv=[str(path(obj['host']['path'])),'--no-lldbinit','--batch','-o','script '+body,'-o','quit']
        (out/'invocation.json').write_text(json.dumps({'argv':argv,'sources':pins,'executed':a.execute,'observation_limit_seconds':120,'cleanup_grace_seconds':35},indent=2)+'\n')
        if not a.execute:
            (out/'preview.json').write_text('{"execution":false,"device_calls":0,"status":"OFFLINE_VALIDATION_ONLY"}\n');return 0
        with (out/'host.stdout.txt').open('wb') as stdout,(out/'host.stderr.txt').open('wb') as stderr:
            proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
            timed=False
            try:rc=proc.wait(timeout=145)
            except subprocess.TimeoutExpired:
                timed=True;proc.send_signal(signal.SIGTERM)
                try:rc=proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();rc=proc.wait()
        (out/'host.rc.json').write_text(json.dumps({'rc':rc,'local_client_timeout':timed,'outer_recovery_required':timed})+'\n')
        r=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else {}
        return 0 if rc==0 and not timed and r.get('cleanup',{}).get('verified') and r.get('exit_reason')=='event_budget_complete' else 2
    except Exception as ex:
        (out/'refusal.json').write_text(json.dumps({'error':str(ex),'status':'REFUSED','playback':'UNKNOWN'})+'\n');return 2
if __name__=='__main__':sys.exit(main())
