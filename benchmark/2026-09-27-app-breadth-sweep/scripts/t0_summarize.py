"""Build reviewable T0 results from raw attempts and external signed image reviews."""
import collections
import hashlib
import json
from pathlib import Path
import t0_evidence as evidence
import t0_review as review

ROOT = Path(__file__).resolve().parents[3] / 'benchmark/2026-09-28-blocker-triage'
CONTROL_RUNS = {'5ea34a4500000000000000001123012c': 'cx10-controls-20260928-1648',
                '61b0657200000000000000000324012c': 'cx10-controls-bytes-20260928-1710'}


def build():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    reviews_file = ROOT / 'reviews.json'
    reviews = json.loads(reviews_file.read_text()) if reviews_file.exists() else []
    admissions = [review.load_admission(ROOT / 'runs' / run, serial, reviews)
                  for serial, run in CONTROL_RUNS.items()]
    eligible = [a['serial'] for a in admissions if a['eligible']]
    fingerprints = {}
    for serial, run in CONTROL_RUNS.items():
        p = ROOT / 'runs' / run / serial / 'wikipedia/device-identity.json'
        if p.exists():
            d = json.loads(p.read_text())
            fingerprints[serial] = (d.get('source_files'), d.get('source_host_hap_sha256'))
    attempts = []
    for path in sorted((ROOT / 'runs').glob('*/*/*/triage.json')):
        row = json.loads(path.read_text())
        if row.get('status') == 'completed' and (path.parent / 'stderr-evidence.txt').exists():
            row = evidence.interpret(path.parent)
        row['evidence_dir'] = str(path.parent.relative_to(ROOT))
        invalidation = path.parent.parent / 'invalidated.json'
        row['invalidated'] = json.loads(invalidation.read_text()) if invalidation.exists() else None
        identity = json.loads((path.parent / 'device-identity.json').read_text())
        row['base_valid'] = (identity.get('source_files'), identity.get('source_host_hap_sha256')) == fingerprints.get(row['serial'])
        if (path.parent.parent / 'admission.json').exists():
            audits = path.parent.parent / 'base-audit'
            before = json.loads((audits / 'before.json').read_text()) if (audits / 'before.json').exists() else {}
            after = json.loads((audits / 'after.json').read_text()) if (audits / 'after.json').exists() else {}
            row['base_valid'] = row['base_valid'] and review.hashes_match(before, after)
        attempts.append(row)
    selected = review.select_attempts(manifest['blocked'], attempts, eligible)
    stop = json.loads((ROOT / 'stop-record.json').read_text()) if (ROOT / 'stop-record.json').exists() else None
    return {'status': 'stopped-by-route-change' if stop else 'ready-for-review' if not selected['pending_keys'] and review.observations_complete(selected['effective'], manifest['blocked']) else 'in-progress',
            'stop_record': stop,
            'r2': 'partially', 'admissions': admissions, 'manifest': 'manifest.json',
            'effective_records': selected['effective'], 'attempts': selected['attempts'],
            'pending_keys': selected['pending_keys'],
            'histogram': dict(collections.Counter(r['candidate_blocker']['class'] for r in selected['effective'])),
            'observations_threshold_met': review.observations_complete(selected['effective'], manifest['blocked'])}


if __name__ == '__main__':
    result = build()
    (ROOT / 'current-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'effective': len(result['effective_records']), 'admissions': result['admissions']}, ensure_ascii=False))
