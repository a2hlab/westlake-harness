#!/usr/bin/env python3
"""Seal the offline increment and its input identities; no git/device operations."""
import datetime,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];B10=HERE.parent/'2026-09-29-static-wall-prediction'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
    # Preserve the original forecast/results, including the original poor baseline comparison.
    guard=json.loads((HERE/'preserved-inputs.json').read_text())
    for name,h in guard['files'].items():
        if sha(ROOT/name)!=h:raise ValueError('prior evidence changed: '+name)
    dependencies=[B10/n for n in ['rules_feedback_v2.py','scan_feedback_v2.py','test_feedback_v2.py','scan_apps.py','scan_reachability.py','scan_jni.py','scan_classes_v3.py']]
    dependencies += [HERE.parent/'2026-09-30-background-start-prospective'/n for n in ['detector.py','scan.py']]
    dependencies += [ROOT/'specs/bms-static-v3/t8-v2-feedback.spec.md',ROOT/'tools/spec-checks/src/lib.rs']
    tool=Path.home()/'Library/Android/sdk/build-tools/37.0.0/dexdump'
    scan=json.loads((HERE/'scan-results.json').read_text());profile=json.loads((HERE/'profile.json').read_text())
    dump(HERE/'provenance.json',{'analysis':'post-hoc','published_at':datetime.datetime.now().astimezone().isoformat(),
         'sources':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in dependencies],
         'tool':{'path':str(tool),'sha256':sha(tool)},'profile':profile['inputs'],
         'apks':[{'key':r['key'],'path':r.get('apk'),'sha256':r['apk_sha256'],'status':r['status'],'error':r.get('error')} for r in scan],
         'preserved_forecast_and_report_files':len(guard['files']),
         'R2':{'verified':'65 APK static scan, 198-row coverage, tests, preserved forecast/report hashes',
               'partially':'post-hoc family coverage with unresolved resource provenance, callbacks and branch feasibility',
               'unverified':'new board behavior, grant-only causal effect, and prospective improvement'},
         'board_io':False,'git_commit':'outer-loop to commit; git metadata read-only here'})
    files=[p for p in HERE.rglob('*') if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts]
    lines=[f'{sha(p)}  {p.relative_to(HERE)}' for p in sorted(files)]
    lines += [f'{sha(p)}  {Path("../2026-09-29-static-wall-prediction")/p.name}' for p in dependencies[:3]]
    (HERE/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'matrix_sha256':sha(HERE/'matrix.csv'),'predictions_sha256':sha(HERE/'predictions.csv'),'results_sha256':sha(HERE/'results.json'),'manifest_sha256':sha(HERE/'SHA256SUMS'),'files':len(lines)}))
if __name__=='__main__':main()
