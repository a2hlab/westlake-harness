#!/usr/bin/env python3
"""Summarize published descriptive rows, retaining every measured profile delta."""
import collections,json
from pathlib import Path
import compare as c

def main():
    final=c.HERE/'final';result=json.loads((final/'results.json').read_text())
    if not result['complete']:raise ValueError('final sweep required')
    new_path=final/'run-identity/runtime-fingerprint.txt';new=c.pa.read_hashes(new_path.read_text())
    baseline=json.loads((c.OLD/'results.json').read_text());runtime=[]
    for source in baseline['runtime_audits']:
        label=Path(source).parent.name;p=c.OLD/'run-identity'/label/'runtime-fingerprint.txt';old=c.pa.read_hashes(p.read_text())
        runtime.append({'baseline_run':source,'baseline_source':str(p),'baseline_sha256':c.sha(p),'new_source':str(new_path),'new_sha256':c.sha(new_path),'identical_paths':len([k for k in set(old)&set(new) if old[k]==new[k]]),'changed':[{'path':k,'old':old[k],'new':new[k]} for k in sorted(set(old)&set(new)) if old[k]!=new[k]],'only_in_5ea':sorted(set(old)-set(new)),'only_in_61b':sorted(set(new)-set(old)),'limit':'Measured paths only, not package-wide or resident-map equivalence.'})
    c.dump(final/'runtime-comparison.json',runtime)
    rows=result['rows'];summary={'status':'machine evidence complete; outer image review pending','keys':len(rows),'identity_comparable_keys':sum(r['comparison_identity_verified'] for r in rows),'noncomparable_keys':[r['key'] for r in rows if not r['comparison_identity_verified']],'record_statuses':dict(collections.Counter(r['new_record_status'] for r in rows)),'counts':result['counts'],'installer_mechanisms':result['installer_mechanisms'],'permission_transitions':{p:dict(collections.Counter(r['old_'+p]+' -> '+r['new_'+p] for r in rows)) for p in c.PERMS},'profile_classification':result['profile_classification'],'same_profile_accuracy':None,'same_profile_denominator':0,'lighting_count':None,'lighting_status':'pending_outer_review','source_results_sha256':c.sha(final/'results.json'),'runtime_comparison_sha256':c.sha(final/'runtime-comparison.json'),'original_v3_receipt_sha256':result['frozen_receipt_sha256'],'device_operations':0,'git_commit':'outer submission required; git metadata read-only'}
    c.dump(c.HERE/'results.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
