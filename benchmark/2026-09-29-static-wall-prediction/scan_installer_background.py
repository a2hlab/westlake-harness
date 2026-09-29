#!/usr/bin/env python3
"""Reuse pinned manifest/DEX caches; scan first, then separately calibrate on traces.

Run: python3 scan_installer_background.py --background-permission absent --out NEW_DIR
Test: python3 test_installer_background.py
Alias resolution is not itself a second Activity. Manifest hints stay candidates.
"""
import argparse,csv,gzip,hashlib,json
from pathlib import Path
from rules_installer_background import detect,FAMILY
HERE=Path(__file__).resolve().parent;BENCH=HERE.parent
BG=BENCH/'2026-09-30-background-start-prospective/evidence'
DEX=BENCH/'2026-09-30-v2-scanner-feedback/evidence'
TRUTH=BENCH/'2026-09-30-r17p-61b-comparison/final/results.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def scan(entry,permission):
    key=entry['key'];p=BG/(key+'.json');d=DEX/(key+'.json.gz');raw=BG/('manifest-'+key+'.txt')
    base={'key':key,'apk_sha256':entry['apk_sha256'],'family':FAMILY,'status':'unknown-input','static_risk':None,'manifest_risk':None,'strength':'unknown','inputs':{}}
    try:
        old=json.loads(p.read_text());base['inputs'][str(p)]=sha(p)
        if old['status']!='scanned' or old['apk_sha256']!=entry['apk_sha256']:raise ValueError('APK identity unavailable')
        if sha(raw)!=old['manifest_sha256']:raise ValueError('manifest hash mismatch')
        base['inputs'][str(raw)]=sha(raw)
        cache=json.load(gzip.open(d,'rt'));base['inputs'][str(d)]=sha(d)
        if cache['status']!='scanned' or cache['apk_sha256']!=entry['apk_sha256'] or cache['source_cache_sha256']!=sha(p):raise ValueError('DEX cache identity mismatch')
        base.update(detect(old['manifest'],old['activities'],cache['activity'],permission))
        base['manifest_source']=str(raw)
        base['cache_policy']='Reuse previously scanned exact base-APK identities; no new APK hashing or DEX disassembly; split/dynamic code unknown.'
    except (OSError,ValueError,KeyError) as e:base['error']=str(e)
    return base

def backtest(rows,truth):
    evidence={r['key']:r for r in truth['rows']}
    comparable={k for k,r in evidence.items() if r.get('comparison_identity_verified')}
    positive={k for k,r in evidence.items() if r.get('new_background_denials') and k in comparable}
    for row in rows:
        if row['key'] in comparable and row['apk_sha256']!=evidence[row['key']]['new_apk_sha256']:raise ValueError('trace APK mismatch: '+row['key'])
    def metric(selected):
        hits=sorted(selected&positive);misses=sorted(positive-selected);unconfirmed=sorted((selected&comparable)-positive)
        return {'positive_samples':len(positive),'hits':len(hits),'misses':len(misses),'recall':len(hits)/len(positive) if positive else None,'hit_keys':hits,'missed_keys':misses,'alerts':len(selected),'alerts_in_comparable_samples':len(selected&comparable),'additional_alerts_without_observed_denial':len(unconfirmed),'unconfirmed_keys':unconfirmed,'observed_support_fraction':len(hits)/len(selected&comparable) if selected&comparable else None}
    return {'analysis':'post-hoc calibration, not prospective accuracy','sample_scope':len(comparable),'excluded_keys':sorted(set(evidence)-comparable),'manifest_only':metric({r['key'] for r in rows if r['manifest_risk']}),'explicit_dex_only':metric({r['key'] for r in rows if r['strength']=='explicit-startup-target'}),'combined':metric({r['key'] for r in rows if r['static_risk']}),'negative_label_policy':'No observed denial is not a true negative: app may fail earlier or take another branch. Additional alerts are unconfirmed, not proven false positives.','lighting_accuracy':None,'metric_target':'Static requirement coverage on the absent-grant trace sample, not prospective accuracy or an active-wall claim for a granted installer'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=HERE/'installer-background-r17p');p.add_argument('--background-permission',choices=['absent','granted','unknown'],default='absent');p.add_argument('--trace',type=Path,default=TRUTH);a=p.parse_args()
    if a.out.exists():raise ValueError('use a fresh output directory')
    entries=json.loads((BENCH/'2026-09-30-v3c-r17j-prospective/freezes/v2/predictions.json').read_text())
    rows=[scan(e,a.background_permission) for e in entries]  # no trace input passed into detection
    a.out.mkdir(parents=True);write(a.out/'matrix.json',rows)
    fields=['key','apk_sha256','status','static_risk','manifest_risk','strength','launchers','launcher_aliases','manifest_hints','dex_witnesses','manifest_source','stub_ok','needs_real']
    with (a.out/'matrix.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows({k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict)) else r.get(k) for k in fields} for r in rows)
    truth=json.loads(a.trace.read_text());result=backtest(rows,truth);result.update(trace=str(a.trace),trace_sha256=sha(a.trace),matrix_sha256=sha(a.out/'matrix.json'),rule_sha256=sha(HERE/'rules_installer_background.py'),scanner_sha256=sha(Path(__file__)),installer_permission=a.background_permission)
    write(a.out/'results.json',result)
    print(json.dumps({k:result[k] for k in ['manifest_only','explicit_dex_only','combined']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
