#!/usr/bin/env python3
"""Scores already-frozen task85 predictions. Observations are loaded only here."""
import argparse,datetime,hashlib,json
from pathlib import Path
from scan85 import OUT
from rules85 import FAMILIES
from scan_io import load
from finalize_v3 import dump,csvwrite
FAMILY_MAP={'window-type':'window-type-flags','bindService':'in-app-bindservice','velocitytracker':'velocitytracker-jni','musl-reloc':'native-bionic-header','prefs-npe':'sharedpreferences-null'}

def ratio(rows,predicate):
    hits=sum(bool(predicate(r)) for r in rows)
    return {'hits':hits,'total':len(rows),'rate':hits/len(rows) if rows else None}

def score_rows(rows):
    exact=[r for r in rows if r['identity']=='exact' and r['classifiable']]
    held=[r for r in exact if r['partition']=='held-out' and r['observed_family'] in FAMILIES]
    seed=[r for r in exact if r['partition']=='seed' and r['observed_family'] in FAMILIES]
    hit=lambda r:r['observed_family'] in r['predicted_families']
    first=lambda r:r['observed_family']==r['first_new_family']
    return {'held_out_family':ratio(held,hit),'seed_family':ratio(seed,hit),
        'held_out_first_fatal':ratio([r for r in held if r['observation_role']=='fatal'],first),
        'seed_first_fatal':ratio([r for r in seed if r['observation_role']=='fatal'],first),
        'conditional_key_family':ratio([r for r in rows if r['observed_family'] in FAMILIES and r.get('predicted_families')],hit),
        'all_classified_first_fatal':ratio([r for r in exact if r['observation_role']=='fatal'],first),
        'classified_outside_new_families':sum(r['classifiable'] and r['observed_family'] not in FAMILIES for r in rows),
        'identity_unknown':sum(r['identity']!='exact' for r in rows),
        'unclassified':sum(not r['classifiable'] for r in rows),
        'nonfatal_or_unproven':sum(r['observation_role']!='fatal' for r in rows)}

def verify_freeze():
    freeze=load(OUT/'freeze.json')
    for item in freeze['inputs']+freeze['outputs']:
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Frozen file changed: '+item['path'])
    if hashlib.sha256((OUT/'provider-exports.json').read_bytes()).hexdigest()!=freeze['provider_manifest_sha256']:raise ValueError('Provider manifest changed')
    return freeze

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-freeze',action='store_true');args=parser.parse_args()
    receipt=verify_freeze();print(json.dumps({'verified':True,'frozen_at':receipt['frozen_at']}))
