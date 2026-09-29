#!/usr/bin/env python3
"""Validate complete per-key evidence, independently of the runner's success count."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'batch/apps.json').read_text())['apps']
report=json.loads((root/'results.json').read_text())
rows=report['apps']
assert len(rows)==66 and {r['key'] for r in rows}=={r['key'] for r in manifest}
assignment=json.loads((root/'batch-shards.json').read_text())['shards']
assert [len(s['keys']) for s in assignment]==[22,22,22]
assert [s['phase_counts']['controls'] for s in assignment]==[5,4,4]
serial_by_key={key:s['serial'] for s in assignment for key in s['keys']}
assert report['completed']==66
assert report['visual_verdict']=='pending_review'
for row in rows:
    assert row['serial']==serial_by_key[row['key']],row['key']
    assert row['status'] not in ('not_run','started','batch_interrupted'),row['key']
    assert row['review']=='pending_review'
    assert row['westlake_2026_09_27']['verdict'] in ('LIT','BLOCKED')
    assert row['attempts'],row['key']
    if row['record'].get('mode')=='capture_existing_exact_apk':
        prior=row['record']['prior_successful_install']
        receipts=[a for a in row['attempts'] if a['source']==prior['path'] and a['record_sha256']==prior['sha256']]
        assert len(receipts)==1,row['key']
        install=receipts[0]['record']['install']
        assert install['return_code']==0 and install['success_text'],row['key']
    for a in row['attempts']:
        rec=a['record'];assert rec['key']==row['key'] and rec['serial']==row['serial']
        assert rec.get('review')=='pending_review'
        for artifact in a['artifacts'].values():
            p=(root/artifact['path']).resolve();assert p.is_relative_to(root)
            assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==artifact['sha256'],str(p)
        for capture in rec.get('screenshots',[]):
            # Capture path is VM provenance; exporter archives the same basename.
            matches=[x for n,x in a['artifacts'].items() if n==Path(capture['path']).name]
            assert len(matches)==1,capture
            assert matches[0]['sha256']==capture['sha256']
print('66 keys, three shards, terminal outcomes, historical comparisons and all artifact hashes verified')
