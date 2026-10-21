#!/usr/bin/env python3
"""Offline adversarial calls to the actual derived Device class. No HDC executable."""
import argparse, hashlib, importlib.util, json, subprocess, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BOOT='12345678-1234-1234-1234-123456789abc'
HOLDER='inner(cc-video) 12 2026-10-21T09:00:00+08:00'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 source=a.source.read_bytes(); spec=importlib.util.spec_from_file_location('peer_actual_deploy',a.source); d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
 rows=[]
 for case in ['holder_drift','boot_drift','transport_nonzero','target_timeout','remote_failure','duplicate_frame','expired_budget','successful_frame']:
  with tempfile.TemporaryDirectory(prefix='guardian-deploy-peer-') as td:
   out=Path(td);session={'holder':HOLDER,'start':time.time()-10};calls=[]
   if case=='expired_budget':session['start']=time.time()-1201
   dev=d.Device(out,session,Path('/offline-repo'),BOOT)
   def run(argv,**kw):
    calls.append({'argv':argv,'timeout':kw.get('timeout')})
    n=len(calls)
    if n==1:return SimpleNamespace(returncode=0,stdout=(('foreign' if case=='holder_drift' else HOLDER)+'\n').encode(),stderr=b'')
    if n==2:return SimpleNamespace(returncode=0,stdout=(('wrong-boot' if case=='boot_drift' else BOOT)+'\n').encode(),stderr=b'')
    if case=='target_timeout':raise subprocess.TimeoutExpired(argv,kw['timeout'],output=b'partial\xff',stderr=b'error\xfe')
    if case=='transport_nonzero':return SimpleNamespace(returncode=9,stdout=b'transport partial',stderr=b'failed')
    body=b'ICON_REMOTE_RC=0\n'
    if case=='remote_failure':body=b'ICON_REMOTE_RC=23\n'
    if case=='duplicate_frame':body=b'ICON_REMOTE_RC=0\nICON_REMOTE_RC=0\n'
    return SimpleNamespace(returncode=0,stdout=body,stderr=b'')
   error=None
   with patch.object(d.subprocess,'run',side_effect=run):
    try:dev.shell('printf target')
    except Exception as e:error=type(e).__name__+': '+str(e)
   artifacts={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'hex':p.read_bytes().hex()} for p in out.iterdir() if p.is_file()}
   count={'holder_drift':1,'boot_drift':2,'expired_budget':0}.get(case,3)
   passed=len(calls)==count and ((error is None)==(case=='successful_frame'))
   if case=='target_timeout':passed=passed and (out/'003.stdout.txt').read_bytes()==b'partial\xff' and (out/'003.stderr.txt').read_bytes()==b'error\xfe' and (out/'003.rc').read_text().strip()=='124'
   if case=='transport_nonzero':passed=passed and (out/'003.rc').read_text().strip()=='9'
   rows.append({'case':case,'passed':passed,'calls':calls,'error':error,'raw_artifacts':artifacts})
 result={'host_only':True,'source_sha256':hashlib.sha256(source).hexdigest(),'source_after_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'cases':rows};result['passed']=all(x['passed'] for x in rows) and result['source_sha256']==result['source_after_sha256'];(a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'cases':len(rows),'source_sha256':result['source_sha256']}));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
