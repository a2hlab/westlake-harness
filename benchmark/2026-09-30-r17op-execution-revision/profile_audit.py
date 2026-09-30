#!/usr/bin/env python3
"""Companion profile strata; immutable v3 scoring rules are not relaxed."""
import argparse,collections,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parent/'2026-09-30-r17op-prospective'
sys.path.insert(0,str(ORIGINAL))
import engine
from audit_run import read_hashes,projected_hashes,audit_run
FREEZE=ORIGINAL/'freezes/v3'
JAR='/system/android/framework/oh-adapter-runtime.jar'
HWUI='/system/android/lib64/libhwui.so'

def context():
    receipt=engine.verify(FREEZE)
    for name in ['score.py','engine.py','audit_run.py']:
        if engine.sha(ORIGINAL/name)!=receipt['hashes']['code/'+name]:raise ValueError('Original scorer changed: '+name)
    return json.loads((FREEZE/'profiles.json').read_text()),json.loads((FREEZE/'evidence/v3c-package.json').read_text())

def compare(rows,board,profiles,package):
    comparisons={}
    for variant,profile in profiles.items():
        expected,_=projected_hashes(package,profile)
        missing=sorted(set(expected)-set(rows));changed=[{'path':p,'expected':h,'actual':rows[p]} for p,h in expected.items() if p in rows and rows[p]!=h]
        installer={};installer_ok=True
        for name,digest in profile['installer_sha256'].items():
            measured={p:h for p,h in rows.items() if Path(p).name==name}
            installer[name]=measured
            installer_ok &= bool(measured) and all(h==digest for h in measured.values())
        extra_android=sorted(p for p in rows if p.startswith('/system/android/') and p not in expected)
        comparisons[variant]={'missing':missing,'changed':changed,'unexpected_android':extra_android,'installer':installer,
          'projection_matches':not missing and not changed and not extra_android and installer_ok and board in profile['boards']}
    jar_variant=next((v for v,p in profiles.items() if p['jar_sha256']==rows.get(JAR)),None)
    exact=[v for v,d in comparisons.items() if d['projection_matches']]
    classification='exact_frozen_projection' if exact else 'known_jar_profile_drift' if jar_variant else 'unfrozen_or_missing_jar'
    return {'classification':classification,'actual_jar_sha256':rows.get(JAR),'actual_hwui_sha256':rows.get(HWUI),
            'matching_jar_column':jar_variant,'matching_projection_columns':exact,'comparisons':comparisons,
            'column_policy':'Same JAR with different native components is descriptive-only; unknown JAR has no forecast column. Never choose the closer/better-scoring column.'}

def inspect_run(run,profiles,package,installer_readback=None):
    run=Path(run);errors=[];sources={};rows={};fingerprint=None
    for filename in ['facts.txt','runtime-fingerprint.txt','baseline.json']:
        p=run/filename
        if not p.exists():errors.append(filename+'_missing')
        else:sources[filename]=engine.sha(p)
    if 'runtime-fingerprint.txt' in sources:
        body=(run/'runtime-fingerprint.txt').read_text().strip();fingerprint=hashlib.sha256(body.encode()).hexdigest()[:12]
        try:rows=read_hashes(body)
        except ValueError as exc:errors.append(str(exc))
        if not rows:errors.append('empty_runtime_fingerprint')
    if 'facts.txt' in sources:
        text=(run/'facts.txt').read_text();first=text.splitlines()[0] if text else ''
        match=re.fullmatch(r'RUNTIME fingerprint=([0-9a-f]{12}) files=(\d+) .*',first)
        if not match or match[1]!=fingerprint or int(match[2])!=len(rows):errors.append('facts_fingerprint_mismatch')
    if 'baseline.json' in sources:
        try:
            b=json.loads((run/'baseline.json').read_text())
            if b.get('runtime_fingerprint')!=fingerprint:errors.append('baseline_fingerprint_mismatch')
            if not b.get('boot_id'):errors.append('baseline_boot_missing')
        except (ValueError,TypeError):errors.append('baseline_invalid')
    result={'run':str(run),'board':run.name,'source_hashes':sources,'runtime_fingerprint':fingerprint,'integrity_errors':errors,
            'same_profile_score_eligible':False,'projection_stratum':None,'exact_profile_audit':None}
    if errors:result['classification']='invalid_evidence';return result
    detail=compare(rows,run.name,profiles,package);result.update(detail)
    identity={'board':run.name,'runtime_hashes':rows}
    result['projection_stratum']=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    variant=detail['matching_jar_column']
    if variant:
        audit=audit_run(run,FREEZE/'variants'/variant,installer_readback,None)
        result['exact_profile_audit']=audit
        result['same_profile_score_eligible']=bool(audit['verified'] and detail['matching_projection_columns']==[variant])
    result['metric_policy']='Profile gate only. Even a matching run still needs per-record APK/time/permission/launcher/sidecar and screenshot gates in the original scorer.'
    return result

def report(runs,profiles,package,installer_readback=None):
    audited=[inspect_run(r,profiles,package,installer_readback) for r in runs];groups=collections.defaultdict(list)
    for r in audited:
        key=r['projection_stratum'] or 'invalid-evidence:'+r['run'];groups[key].append(r)
    strata=[]
    for key,rs in groups.items():
        strata.append({'id':key,'board':rs[0]['board'],'classification':rs[0]['classification'],
            'actual_jar_sha256':rs[0].get('actual_jar_sha256'),'actual_hwui_sha256':rs[0].get('actual_hwui_sha256'),
            'runs':[r['run'] for r in rs],'eligible_runs':sum(r['same_profile_score_eligible'] for r in rs),
            'same_profile_accuracy':None,'accuracy_status':'not scored here; mismatch strata are excluded from v3 same-profile accuracy'})
    return {'freeze_sha256':engine.sha(FREEZE/'freeze.json'),'revision_sha256':engine.sha(HERE/'execution-revision.json'),
            'runs':audited,'strata':strata,'outcomes_read':False,'forecast_modified':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,action='append',required=True);p.add_argument('--installer-readback',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    profiles,package=context();result=report(a.run,profiles,package,a.installer_readback)
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result['strata'],indent=2))
if __name__=='__main__':main()
