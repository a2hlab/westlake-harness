#!/usr/bin/env python3
"""Index complete records across interrupted attempts; never rewrite raw evidence."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths
sys.path.insert(0, str(lab_paths.harness() / 'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b

name = sys.argv[1]
assert name in ['5ea', '61b', '5cd']
matches = [s for s in lab_paths.boards('oh') if s.startswith(name)]
assert len(matches) == 1
serial = matches[0]
keys = set((HERE / ('keys-' + name + '.txt')).read_text().strip().split(','))
assert len(keys) == 22
cohort = {r['key']: r for r in json.loads((HERE / 'cohort-j3.json').read_text())['apps']}
jar_receipt = json.loads((HERE / name / 'jar-original.json').read_text())
attempts = sorted(p / serial for p in (HERE / 'runs').glob('u5-' + name + '*') if p.is_dir())
fingerprints = {(p / 'runtime-fingerprint.txt').read_bytes() for p in attempts}
assert len(fingerprints) == 1, 'attempt fingerprints differ'
assert hashlib.sha256(next(iter(fingerprints)).strip()).hexdigest()[:12] == '73ecf422dba2'
boot_images = {(p / 'boot-image-fingerprint.txt').read_bytes() for p in attempts}
assert len(boot_images) == 1, 'attempt boot images differ'
assert hashlib.sha256(next(iter(boot_images)).strip()).hexdigest()[:12] == '0876029078e2'
selected, interrupted = {}, []
for attempt in attempts:
    for record in attempt.glob('*/record.json'):
        d = json.loads(record.read_text())
        assert d['key'] in keys and d['serial'] == serial and d['boot_id'] == jar_receipt['boot_id']
        expected_apk = cohort[d['key']]['apk_sha256']
        if expected_apk is None:
            # J3's plan left noice/x unpinned; use its actual record, never a guess.
            candidates = list((lab_paths.harness() / 'benchmark/2026-09-30-j3-u3-sweep/runs').glob('j3-*/*/' + d['key'] + '/record.json'))
            digests = {json.loads(prior.read_text())['apk_sha256'] for prior in candidates}
            assert len(digests) == 1, (d['key'], digests)
            expected_apk = digests.pop()
            assert expected_apk
        assert d['apk_sha256'] == expected_apk
        if d['status'] in ['started', 'batch_interrupted'] or not d.get('finished_at'):
            interrupted.append(str(record.relative_to(HERE)))
            cleanup = HERE / '5ea/cleanup-uninstall/receipt.json'
            settled = json.loads(cleanup.read_text()) if cleanup.exists() else {}
            retained_timed_trial = (name == '5ea' and d['key'] == 'fd-organicmaps'
                and d.get('error') == 'target cleanup could not be verified; stop before next app'
                and settled.get('cleanup_verified') is True
                and settled.get('record') == str(record.relative_to(HERE))
                and settled.get('boot_id') == d['boot_id']
                and {s['scheduled_seconds'] for s in d.get('screenshots', []) if s.get('captured')} == {5, 20})
            if not retained_timed_trial:
                continue
        assert d['key'] not in selected, 'multiple complete trials require explicit selection'
        selected[d['key']] = (record, d)
assert set(selected) == keys, 'missing complete keys: ' + ','.join(sorted(keys - set(selected)))
out = HERE / 'final' / serial
out.mkdir(parents=True, exist_ok=False)
(out / 'runtime-fingerprint.txt').write_bytes(next(iter(fingerprints)))
if (attempts[0] / 'baseline.json').exists():
    shutil.copy2(attempts[0] / 'baseline.json', out / 'baseline.json')
for filename in ['boot-image-fingerprint.txt', 'frozen-check.json']:
    source = attempts[0] / filename
    if source.exists(): shutil.copy2(source, out / filename)
(HERE / 'evidence').mkdir(exist_ok=True)
index = []
for key, (record, d) in sorted(selected.items()):
    (out / key).symlink_to(os.path.relpath(record.parent, out), target_is_directory=True)
    captured = []
    for shot in d.get('screenshots', []):
        if not shot.get('captured'): continue
        image = Path(shot['path'])
        assert image.is_file() and hashlib.sha256(image.read_bytes()).hexdigest() == shot['sha256']
        captured.append({'path': str(image.relative_to(HERE)), 'sha256': shot['sha256']})
        if image.name == 't20.jpeg':
            dest = HERE / 'evidence' / 't20' / (key + '.jpeg')
            dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(image, dest)
    dest = HERE / 'evidence' / 'records' / key
    dest.mkdir(parents=True, exist_ok=False)
    for f in ['record.json', 'processes-t5.txt', 'processes-t20.txt']:
        source = record.parent / f
        if source.exists():
            if f.startswith('processes-'):
                (dest / (f + '.gz')).write_bytes(gzip.compress(source.read_bytes(), mtime=0))
            else:
                shutil.copy2(source, dest / f)
    index.append({'key': key, 'record': str(record.relative_to(HERE)),
                  'record_sha256': hashlib.sha256(record.read_bytes()).hexdigest(),
                  'status': d['status'], 'error': d.get('error'), 'captured': captured,
                  'visual_verdict': 'pending_outer_review'})
total = b.write_facts(out)
assert total is not None and 'keys=22 ' in total
shutil.copy2(out / 'facts.txt', HERE / 'evidence' / (name + '-facts.txt'))
(HERE / ('index-' + name + '.json')).write_text(json.dumps({
    'serial': serial, 'boot_id': jar_receipt['boot_id'], 'complete_keys': len(index),
    'selected': index, 'interrupted_records_retained': interrupted,
    'facts_generator': 'master bms_batch.write_facts (run_facts.facts)',
    'view': str(out.relative_to(HERE)), 'total': total}, indent=2) + '\n')
print(total)
