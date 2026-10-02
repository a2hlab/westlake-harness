"""Proposed promotion hooks: fail closed before apply, retain only outer-signed full results.

Corrected effective T8 passes the frozen-DEX audit. Exact open/provenance review and outer authorization remain required.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

H = Path(__file__).resolve().parent
R = H.parents[1]
sys.path.insert(0, str(R / 'scripts/lab'))
import generation_bundle as gb
import lab_paths
import u7_executor as u

W = lab_paths.workspaces()
M = lab_paths.harness()
BASE = W / 'westlake-generation-u9-j10g-238ffc14'
CANDIDATE = W / 'westlake-inputs/generations/u10.1-t8-effective-j5ae3dd29-s2f365a75-v2/bundle'
spec = importlib.util.spec_from_file_location('previous_transaction_hooks', R / 'benchmark/2026-10-02-u10-1-bundle/window_hook.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
previous.H = H
previous.CANDIDATE = CANDIDATE


def admission():
    composition = json.loads((H / 'composition.json').read_text())
    assert gb.sha(CANDIDATE / 'bundle.json') == composition['bundle_sha256'], 'bundle drift'
    assert gb.sha(CANDIDATE / 'native/package.json') == composition['native_manifest_sha256'], 'manifest drift'
    assert json.loads((H / 'evidence/effective-stubs-diff.json').read_text())['frozen_behavior_gate'] == 'PASS', 'FZ-007/FZ-008 effective DEX regression'
    assert json.loads((H / 'results.json').read_text())['all_required_gates_passed'] is True, 'offline gates are not all green'
    assert composition['rollout_ready'] is True, 'outer package review pending'
    assert json.loads((CANDIDATE / 'bundle.json').read_text())['rollout_ready'] is True, 'bundle is not armed'


def retention_reason(decision, composition, signed_base, smoke):
    """Return a refusal reason, never infer lit from facts or live processes."""
    if not smoke or smoke.get('passed') is not True:
        return 'activation smoke did not pass'
    if not isinstance(decision, dict) or decision.get('signed_by') != 'outer(claude)':
        return 'outer screenshot signoff absent'
    if decision.get('bundle_sha256') != composition['bundle_sha256']:
        return 'signoff belongs to another bundle'
    if decision.get('native_manifest_sha256') != composition['native_manifest_sha256']:
        return 'signoff manifest mismatch'
    keys = decision.get('keys', {})
    if set(keys) != set(signed_base['keys']) or len(keys) != 166:
        return 'full 166-key signoff incomplete; unknown cannot promote'
    if any(row.get('verdict') in (None, 'unknown', 'inconclusive') for row in keys.values()):
        return 'unknown or inconclusive key remains'
    for key, base in signed_base['keys'].items():
        if base['verdict'] == 'lit' and keys[key].get('verdict') != 'lit':
            return 'signed U9-lit regression: ' + key
    if keys.get('toutiao', {}).get('verdict') != 'lit':
        return 'Toutiao t20 not signed bright'
    if decision.get('controls_t20_lit') != ['helloworld', 'zigzag']:
        return 'HW/ZZ screenshot signoff absent'
    if decision.get('confirmed_regressions') != []:
        return 'outer confirmed a regression'
    return None


def verify_candidate(serial, root):
    if sys.platform == 'darwin':
        return previous.vm(['python3', str(Path(__file__).resolve()), '--verify-candidate', '--serial', serial, '--root', str(root)])
    row = json.loads((H / 'expected-run.json').read_text())['boards'][serial]
    io = u.DeviceIO(serial, 'cx-t0', root / 'device')
    got, absent = io.snapshot(sorted(row['expected']))
    diff = {p: {'expected': value, 'actual': got.get(p)} for p, value in row['expected'].items() if got.get(p) != value}
    refs = gb.validate(CANDIDATE)[0]['reference']
    paths = {k: sorted(gb.read_fingerprint(CANDIDATE / value['source'])) for k, value in refs.items()}
    paths['runtime'] = sorted(set(paths['runtime']) | (set(row['expected']) - set(u.prepare(CANDIDATE, BASE / 'native')['expected'])))
    # Service aliases already in the runtime set remain included exactly once.
    service = json.loads((R / 'benchmark/2026-10-01-installation-chain-identity/current-u9.json').read_text())['boards'][serial]['services']
    paths['runtime'] = sorted(set(paths['runtime']) | set(service))
    fingerprints = u.fingerprints(got, paths) if not absent else None
    root.mkdir(parents=True, exist_ok=True)
    (root / 'candidate-318.json').write_text(json.dumps({'identity_assertions': 318, 'unique_paths': len(got), 'diff': diff, 'absent': absent, 'fingerprints': fingerprints, 'boot_id': io.boot}, indent=2) + '\n')
    assert not diff and not absent and fingerprints == row['fingerprints']


def finish(serial, root, restored_spec, decision_path):
    composition = json.loads((H / 'composition.json').read_text())
    baseline = json.loads((R / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json').read_text())
    smoke_path = root / 'runner/smoke/smoke-result.json'
    smoke = json.loads(smoke_path.read_text()) if smoke_path.is_file() else None
    decision = json.loads(decision_path.read_text()) if decision_path.is_file() else None
    reason = retention_reason(decision, composition, baseline, smoke)
    if reason is None:
        try:
            admission()
            verify_candidate(serial, root / 'retained-final')
        except Exception as error:
            reason = 'retention identity/admission refused: ' + str(error)
        else:
            (root / 'retention.json').write_text(json.dumps({'retained': True, 'basis': str(decision_path), 'scope': 'complete outer-signed promotion'}, indent=2) + '\n')
            return
    (root / 'retention.json').write_text(json.dumps({'retained': False, 'reason': reason}, indent=2) + '\n')
    # Existing stopped-parent rollback includes exact U9 identity checks and OrganicMaps cold_stop.
    previous.finish(serial, root, restored_spec)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', choices=sorted(lab_paths.boards('oh')), required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--restored-spec', type=Path)
    parser.add_argument('--decision', type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply', action='store_true')
    group.add_argument('--finish', action='store_true')
    group.add_argument('--verify-candidate', action='store_true')
    args = parser.parse_args()
    if args.apply:
        admission()  # No VM call or Board exists before admission succeeds.
        previous.apply(args.serial, args.root)
        verify_candidate(args.serial, args.root / 'post-apply')
    elif args.verify_candidate:
        verify_candidate(args.serial, args.root)
    else:
        assert args.restored_spec is not None and args.decision is not None
        finish(args.serial, args.root, args.restored_spec, args.decision)


if __name__ == '__main__':
    main()
