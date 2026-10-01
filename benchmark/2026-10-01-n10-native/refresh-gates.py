"""Recompute exact candidate gates and a proposal, never an approval."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import native_predeploy

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
package = read(HERE / 'package.json')
native = REPO.parent / package['package']
composed = REPO.parent / read(HERE / 'bundle-plan.json')['package']
binding = read(HERE / 'source-binding.json')
binding['sources'] = {str(p.relative_to(REPO)): sha(p)
    for folder in ['src', 'bionic', 'flutter'] for p in sorted((HERE / folder).rglob('*')) if p.is_file()}
binding['sources'].update({str(p.relative_to(REPO)): sha(p) for p in sorted(HERE.glob('*.py'))})
binding['sources'][str((HERE / 'build-bionic.sh').relative_to(REPO))] = sha(HERE / 'build-bionic.sh')
binding['changes_from_n8'] = package['changes_from_n8']
binding['receipts'] = {name: sha(HERE / name) for name in binding['receipts']}
for dest in [HERE, native / 'native-checks', composed / 'native/native-checks']:
    save(dest / 'source-binding.json', binding)
reader = os.environ.get('NATIVE_READELF', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf')
report = native_predeploy.check_package(native, native / 'native-checks/native-gates.json', readelf=reader)
save(HERE / 'native-gate.json', report)
if report['errors']:
    raise RuntimeError(report['errors'])
old = read(REPO / 'benchmark/2026-10-01-n8-native/native-gate.json')

def canonical(value):
    # Only scanner IDs/dispositions and recorded source coordinates are omitted.
    # Library paths, function names, expressions and source text remain significant.
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items() if k not in {'issue_id', 'disposition', 'line'}}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    return value

comparison = {}
rows = []
for gate, result in report['gates'].items():
    keys = lambda findings: {json.dumps(canonical(f), sort_keys=True) for f in findings}
    current, previous = keys(result['findings']), keys(old['gates'][gate]['findings'])
    comparison[gate] = {'candidate': len(result['findings']),
        'n8': len(old['gates'][gate]['findings']),
        'new_semantic_findings': len(current - previous),
        'removed_semantic_findings': len(previous - current),
        'new_examples': [json.loads(v) for v in sorted(current - previous)[:3]]}
    for finding in result['findings']:
        rows.append({'gate': gate, 'package_manifest_sha256': report['package_manifest_sha256'],
            'inputs_sha256': report['inputs_sha256'], 'issue_id': finding['issue_id'],
            'reason': 'Same bounded finding as N8; its one-window grant expired and is NOT inherited. '
                'Retained JNI ordering/namespace bounded-scanner uncertainty requires owner maps, '
                'no unknown sessionId and HW/ZZ controls; no finding is asserted harmless.',
            'removal_condition': 'Complete owner/initialization/closure proof or verified fix. '
                'Any package/sidecar/finding drift needs new review. One <=30 minute N10 window only.',
            'evidence': [str((HERE / n).relative_to(REPO)) for n in ['native-gate.json', 'gate-comparison.json']],
            'approval_status': 'proposed'})
save(HERE / 'gate-comparison.json', comparison)
save(HERE / 'exception-proposal.json', {'schema_version': 1, 'status': 'proposal-not-authorized', 'exceptions': rows})
print(json.dumps({'status': report['status'], 'rejected': {k:v['rejected'] for k,v in report['gates'].items()},
    'comparison': comparison, 'proposal_count': len(rows)}, indent=2))
