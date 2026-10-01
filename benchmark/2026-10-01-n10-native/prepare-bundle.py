"""Keep U7's exact image/JAR group while overlaying the N10 native batch."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import generation_bundle as bundle
import u7_executor as executor

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = REPO.parent / 'westlake-generation-u7-executor-example'
native = REPO.parent / 'westlake-generation-n10-63b6f8d4'
out = REPO.parent / ('westlake-generation-n10-u7-' + sha(native / 'package.json')[:8])
assert not out.exists()
subprocess.run(['/bin/cp', '-Rc', str(base), str(out)], check=True)
shutil.rmtree(out / 'native')
subprocess.run(['/bin/cp', '-Rc', str(native), str(out / 'native')], check=True)
data = json.loads((out / 'bundle.json').read_text())
data['native']['manifest']['sha256'] = sha(native / 'package.json')
expected = json.loads((HERE / 'evidence/u7-complete-expected.json').read_text())['runtime_files']
for name in ['runtime', 'boot']:
    row = data['reference'][name]
    p = out / row['source']
    original = bundle.read_fingerprint(p)
    p.write_text('\n'.join(expected[k] + '  ' + k for k in sorted(original)) + '\n')
    row['sha256'] = sha(p)
data['rollout_ready'] = False
(out / 'bundle.json').write_text(json.dumps(data, indent=2) + '\n')
plan = executor.prepare(out, REPO.parent / 'westlake-generation-n4-order-216b68fb')
baseline = plan['baseline']
assert executor.fingerprints(baseline, plan['reference_paths']) == {
    'runtime': {'sha256_12': '68b7fb016253', 'files': 119},
    'boot': {'sha256_12': '8fe2e5fd7d65', 'files': 36}}
assert all(plan['expected'][x['target']] == x['sha256'] for x in data['boot_group']['members'] + [data['runtime_jar']])
changed = {p: {'before': baseline.get(p), 'after': digest} for p, digest in plan['expected'].items() if baseline.get(p) != digest}
assert all('/framework/' not in p for p in changed), 'N10 must change no U7 Java/image bytes'
summary = {'schema_version': 1, 'package': out.name,
           'bundle_sha256': sha(out / 'bundle.json'), 'native_manifest_sha256': sha(native / 'package.json'),
           'structural_plan_valid': True, 'device_io': False,
           'baseline_fingerprints': executor.fingerprints(baseline, plan['reference_paths']),
           'target_fingerprints': executor.fingerprints(plan['expected'], plan['reference_paths']),
           'expected_identity_count': len(plan['expected']), 'changes': changed,
           'image_and_runtime_jar_unchanged': True,
           'build_receipt_status': plan['build_receipt']['status'],
           'rollout_ready': False, 'native_gate': 'pending exact candidate exceptions'}
(HERE / 'bundle-plan.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({k:v for k,v in summary.items() if k != 'changes'}, indent=2))
