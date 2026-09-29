#!/usr/bin/env python3
import concurrent.futures,csv,datetime,gzip,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRE=HERE.parent/'2026-09-29-static-wall-prediction'
sys.path.insert(0,str(PRE))
from scan_reachability import scan
from scan_io import load
from rules import FAMILIES,POLICY,inspect_method,manifest_providers,provider_gaps

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def table(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
def analyze(app):
 graph=scan({**app,'calls':[],'features':{}},HERE/'evidence',inspect_method)
 raw=(HERE/'evidence'/f'manifest-{app["key"]}.txt').read_text()
 providers=provider_gaps(manifest_providers(raw,graph['manifest']['package']),graph['extra_calls'])
 dump(HERE/'evidence'/f'providers-{app["key"]}.json',providers)
 rows=[]
 for family in FAMILIES:
  calls=[c for c in graph['extra_calls'] if c['family']==family]
  gaps=[p for p in providers if p['is_gap']] if family=='documents-provider-permission' else []
  rows.append({'app':app['key'],'apk_sha256':app['sha256'],'family':family,'policy':POLICY[family],'reference_count':len(calls),'startup_reference_count':sum(c['startup_reachable']=='yes-static' for c in calls),'startup_reachable':'yes-static' if any(c['startup_reachable']=='yes-static' for c in calls) else 'unknown','manifest_gap_count':len(gaps),'verdict':'static-manifest-contract-gap' if gaps else 'conditional-runtime-requirement' if calls else 'no-static-evidence','runtime_null_or_missing_implementation':'unknown','evidence':f'evidence/reachability-{app["key"]}.json.gz','provider_evidence':f'evidence/providers-{app["key"]}.json' if family=='documents-provider-permission' else ''})
 p=HERE/'evidence'/f'reachability-{app["key"]}.json';Path(str(p)+'.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()
 return rows
def main():
 if (HERE/'freeze.json').exists():raise SystemExit('Frozen feedback exists; use a new version')
 cohort=load(PRE/'v3/classes/cohort.json')['apps']
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:groups=list(pool.map(analyze,cohort))
 rows=[r for group in groups for r in group];table(HERE/'matrix.csv',rows);dump(HERE/'matrix.json',rows)
 actual=load(HERE.parent/'2026-09-30-r16-prospective/observed/observations-reviewed.json')
 identities={a['key']:a['sha256'] for a in cohort}
 coverage=[{'app':key,'recorded_apk_sha256':r['apk_sha256'],'coverage':'exact-static-APK' if identities.get(key)==r['apk_sha256'] and key in identities else 'not-scanned','reason':'cohort contains only 32 pinned APKs'} for key,r in actual.items()]
 table(HERE/'coverage.csv',coverage)
 summary=[{'family':f,'policy':POLICY[f],'startup_affected_apps':sum(r['family']==f and r['startup_reference_count']>0 for r in rows),'referencing_apps':sum(r['family']==f and r['reference_count']>0 for r in rows),'all_reference_count':sum(r['reference_count'] for r in rows if r['family']==f),'manifest_gap_apps':[r['app'] for r in rows if r['family']==f and r['manifest_gap_count']]} for f in FAMILIES]
 table(HERE/'family-summary.csv',summary)
 dump(HERE/'results.json',{'apps':32,'families':8,'matrix_rows':len(rows),'coverage_rows':len(coverage),'training_run':'r16full A/B outcomes; no prospective score claimed','summary':summary,'runtime_failure':'unknown from static references; source contract gaps are narrower claims'})
 inputs=[Path(__file__),HERE/'rules.py',PRE/'scan_reachability.py',PRE/'v3/classes/cohort.json']
 dump(HERE/'freeze.json',{'frozen_at':datetime.datetime.now().astimezone().isoformat(),'training_observation':'r16 full, already inspected','inputs':[{'path':str(p),'sha256':sha(p)} for p in inputs],'outputs':[{'path':n,'sha256':sha(HERE/n)} for n in ['matrix.csv','matrix.json','coverage.csv','family-summary.csv']],'apks':cohort})
 print(json.dumps(load(HERE/'results.json'),ensure_ascii=False))
if __name__=='__main__':main()
