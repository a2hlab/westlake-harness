#!/usr/bin/env python3
"""32-APK static requirements, learned families from r15c, separate freeze."""
import argparse,concurrent.futures,datetime,gzip,hashlib,json,zipfile
from pathlib import Path
from rules90 import FAMILIES,POLICY,inspect_method
from rules85 import elf_info
from scan_reachability import scan
from scan_io import load
from update90 import HERE,ROOT,dump,table

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def analyze(app,out,provider_names):
 graph=scan({**app,'calls':[],'features':{}},out/'evidence',inspect_method)
 libraries=[]
 with zipfile.ZipFile(app['apk']) as z:
  selected=sorted(x for x in z.namelist() if x.startswith('lib/arm64-v8a/') and x.endswith('.so'))
  names={Path(x).name for x in selected}
  for entry in selected:
   data=z.read(entry);elf=elf_info(data)
   for needed in elf['needed']:
    libraries.append({'entry':entry,'library_sha256':hashlib.sha256(data).hexdigest(),'needed':needed,'app_provider':needed in names,'package_provider':needed in provider_names,'resolution':'app-definition-present-scope-unknown' if needed in names else 'package-definition-present-scope-unknown' if needed in provider_names else 'not-in-reviewed-package-system-scope-unknown','startup_reachable':'unknown','runtime_namespace':'unknown'})
 rows=[]
 for family in FAMILIES:
  calls=[c for c in graph['extra_calls'] if c['family']==family]
  dependencies=libraries if family=='app-native-loader' else []
  # Startup calls are bounded graph reachability, not execution guarantees.
  startup=any(c['startup_reachable']=='yes-static' for c in calls)
  rows.append({'app':app['key'],'apk_sha256':app['sha256'],'family':family,'policy':POLICY[family],'hit':bool(calls or dependencies),'startup_reachable':'yes-static' if startup else 'unknown','reference_count':len(calls),'dependency_edges':len(dependencies),'verdict':'conditional-runtime-requirement' if calls or dependencies else 'no-static-evidence','missing_implementation':'unknown','evidence':f'evidence/reachability-{app["key"]}.json.gz' if family!='app-native-loader' else f'evidence/native-{app["key"]}.json.gz'})
 dump(out/f'evidence/native-{app["key"]}.json',{'app':app,'dependencies':libraries,'scope':'Selected arm64 APK libraries only; runtime namespace, extracted path, inherited system libraries and execution remain unknown.'})
 for prefix in ['reachability','native']:
  p=out/f'evidence/{prefix}-{app["key"]}.json';Path(str(p)+'.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()
 return rows

def main(out):
 if (out/'freeze.json').exists():raise ValueError('Frozen output exists: use a new output directory')
 apps=load(HERE/'v3/classes/cohort.json')['apps']
 provider_root=ROOT/'westlake-generation-v3a-74d1d6d4-r8b'
 paths=sorted(p for folder in ['payload/android/lib64','payload/route'] for p in (provider_root/folder).glob('*.so') if p.is_file())
 names={p.name for p in paths}
 dump(out/'provider-inventory.json',{'generation':'v3a package; r15c runtime override not dynamically inspected','providers':[{'path':str(p),'sha256':sha(p)} for p in paths]})
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:groups=list(pool.map(lambda a:analyze(a,out,names),apps))
 rows=[r for group in groups for r in group];table(out/'matrix.csv',rows);dump(out/'matrix.json',rows)
 old={r['app']:r for r in load(HERE/'task90-r15c/predictions.json')};pred=[]
 for key,prior in old.items():
  hits=sorted([r for r in rows if r['app']==key and r['hit']],key=lambda r:(r['startup_reachable']!='yes-static',r['policy']!='stub_ok',r['family']))
  candidates=list(dict.fromkeys(prior['observed_wall_order']+[r['family'] for r in hits]+prior['prior_latent_static_order']))
  pred.append({**prior,'candidate_wall_order':candidates,'new_static_candidates':[r['family'] for r in hits],'new_static_startup':[r['family'] for r in hits if r['startup_reachable']=='yes-static'],'new_static_coverage':'exact-APK' if any(r['app']==key for r in rows) else 'outside-32-APK-scan','next_first_wall_candidate':prior['next_first_wall_candidate'],'prediction_basis':'r15c observed requirements plus outcome-informed static latent candidates; latent order is not execution order'})
 dump(out/'predictions.json',pred);table(out/'predictions.csv',pred)
 dump(out/'results.json',{'apps':len(apps),'families':len(FAMILIES),'matrix_rows':len(rows),'training_observation':'r15c full; not eligible as held-out test','scope':'Static conditional requirements, not runtime implementation failure','all_app_predictions':len(pred),'rules_sha256':sha(HERE/'rules90.py'),'graph_scanner_sha256':sha(HERE/'scan_reachability.py'),'cohort_sha256':sha(HERE/'v3/classes/cohort.json'),'counts':{f:{'hit':sum(r['family']==f and r['hit'] for r in rows),'startup':sum(r['family']==f and r['startup_reachable']=='yes-static' for r in rows)} for f in FAMILIES}})
 dump(out/'freeze.json',{'frozen_at':datetime.datetime.now().astimezone().isoformat(),'training_observation':'r15cfull; r16 sanity board findings already disclosed','outputs':[{'path':n,'sha256':sha(out/n)} for n in ['predictions.json','predictions.csv','matrix.json','matrix.csv']],'inputs':[{'path':str(p),'sha256':sha(p)} for p in [HERE/'rules90.py',Path(__file__),HERE/'scan_reachability.py',HERE/'v3/classes/cohort.json',HERE/'task90-r15c/predictions.json']], 'apks':apps})
 print(json.dumps(load(out/'results.json')))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=HERE/'task90-feedback-static');a=p.parse_args();main(a.out)
