"""Validate the offline handoff; this is explicitly not a board-success test."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
read = lambda name: json.loads((root/name).read_text())
meta = read('evidence/app-input.json')
inputs = read('evidence/input-verification.json')
plan = read('firefox-plan.json')
result = read('results.json')
assert inputs['apk_native_members'] == []
assert inputs['apk_sha256'] == meta['apk_sha256'] == result['original_apk_sha256']
assert inputs['sidecars_count'] == len(inputs['libraries']) == 18
assert sum(r['bytes'] for r in inputs['libraries']) == inputs['sidecars_bytes']
assert plan['execution'] == 'not-requested'
assert len(plan['apps'][0]['native_sidecars']) == 18
assert inputs['split_sha256'] == meta['splits']['config.arm64_v8a.apk']['sha256']
for r in inputs['libraries']:
    m = meta['native_libraries']['lib/arm64-v8a/'+r['name']]
    assert r['sha256'] == r['split_member_sha256'] == m['sha256']
    assert r['bytes'] == m['bytes'] and r['abi'] == 'arm64-v8a'
assert result['board']['status'] == 'pending'
assert all(result['board'][k] is None for k in ['screenshots_captured','alive_t5','alive_t20','lit'])
assert result['r2']['device_effect'] == 'unknown'
smali = (root/'evidence/B7BindFixes.smali').read_text()
assert 'lib/arm64-v8a' in smali and '->nativeLibraryDir:Ljava/lang/String;' in smali
assert 'B7BindFixes;->apply' in (root/'evidence/bind-callsite.txt').read_text()
assert result['installer']['owner'] == 'cx-t0'
print('Offline handoff verified: 18 libraries; board result remains unknown.')
