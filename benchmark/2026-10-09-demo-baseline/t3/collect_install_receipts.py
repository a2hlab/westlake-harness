#!/usr/bin/env python3
"""Read recorded install receipts; never launch a stale or unverified APK.
Build a pinned launch index and symlink-only facts views without altering records.
"""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def proof(app, path):
 r=json.loads(path.read_text());ins=r.get('install') or {}
 success=(r.get('key')==app['key'] and r.get('package')==app['package'] and
          r.get('apk_sha256')==app['apk_sha256'] and ins.get('return_code')==0 and
          ins.get('success_text') is True and (r.get('bms') or {}).get('queryable') is True and
          r.get('status') in {'installed','captured','foreground_unconfirmed'})
 return {'apk_sha256':app['apk_sha256'],'success':success,'record':str(path.resolve()),
         'record_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'status':r.get('status'),
         'error':r.get('error')}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 apps=json.loads((HERE/'plans-v1/batch-apps.json').read_text())['apps']
 records={}
 for p in (HERE/'plans-v1').glob('*/runner/0*/*/*/*/record.json'):
  if p.relative_to(HERE/'plans-v1').parts[0]!='window-01' and not p.relative_to(HERE/'plans-v1').parts[0].startswith('install-'):continue
  r=json.loads(p.read_text());key=r.get('key')
  if key in records:raise SystemExit('duplicate install receipt: '+str(key))
  records[key]=p
 index={app['key']:proof(app,records[app['key']]) if app['key'] in records else
        {'apk_sha256':app['apk_sha256'],'success':False,'error':'not installed yet'} for app in apps}
 a.out.write_text(json.dumps(index,indent=2)+'\n')
 print(json.dumps({'keys':len(index),'successful_install_receipts':sum(x['success'] for x in index.values()),
                   'unverified':[k for k,v in index.items() if not v['success']]},indent=2))
if __name__=='__main__':main()
