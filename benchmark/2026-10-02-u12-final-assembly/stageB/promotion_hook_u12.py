"""U12 promotion copy of u10-1-t8-rerun/promotion_hook.py (outer authorized 2026-10-03).
Baseline parameters: signed U10.1T8; lit count comes from its signed key table and
must match certificate.u10_1_t8_lit_total (116), never a fabricated old U9 count.
Toutiao wall1/2 was exclusive to the earlier U10.1T8 promotion; outer explicitly
removed it for U12. All SHA, identities, fingerprints, activation smoke, fresh
same-board/window outer signatures and fail-closed restoration remain mandatory.
U12's reviewed transaction/verification hooks replace the old U9 wiring; they
verify all321 candidate assertions (318 baseline plus three new members).
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

H = Path(__file__).resolve().parent
R = H.parents[2]
sys.path.insert(0, str(R / 'scripts/lab'))
import generation_bundle as gb
import lab_paths
import u7_executor as u

W = lab_paths.workspaces()
M = lab_paths.harness()
BASE = W / 'westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
CANDIDATE = W / 'westlake-inputs/generations/u12-final-approved-2a3fac81-v1/bundle'
spec = importlib.util.spec_from_file_location('previous_transaction_hooks', H.parent / 'window_hook.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
previous.H = H
previous.CANDIDATE = CANDIDATE

# Keep VM CLI delegation in the same signed U12 configuration, like the Stage A runner.
original_vm = previous.vm
def configured_vm(command):
    if len(command) > 1 and str(command[1]) == str(Path(previous.__file__).resolve()):
        command = [command[0], Path(__file__).resolve(), *command[2:]]
    return original_vm(command)
previous.vm = configured_vm


def admission():
    composition = json.loads((H / 'composition.json').read_text())
    assert composition.get('execution_enabled') is True, 'promotion paused or not authorized'
    assert gb.sha(CANDIDATE / 'bundle.json') == composition['bundle_sha256'], 'bundle drift'
    assert gb.sha(CANDIDATE / 'native/package.json') == composition['native_manifest_sha256'], 'manifest drift'
    for surface in ('mac', 'vm'):
        proof = json.loads((H / ('gate-' + surface + '-pass.json')).read_text())
        assert proof['bundle_sha256'] == composition['bundle_sha256'], 'offline receipt bundle drift'
        assert proof['native_manifest_sha256'] == composition['native_manifest_sha256'], 'offline receipt manifest drift'
        assert proof['production_dry_run_exit_code'] == 0 and proof['gates_passed'] and proof['deployable'], 'offline gates are not all green'
        assert proof['frozen_composed_violations'] == 0, 'effective frozen DEX regression'
        assert proof['static'] == 'PASS' and proof['G1'] and proof['G2'], 'static/image regression'
        assert all(proof['native_findings'][gate]['rejected'] == 0 for gate in ('N1', 'N2')), 'native admission rejected'
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
    verdict = decision.get('stage_A_regression_verdict', {})
    expected_lit = sum(row['verdict'] == 'lit' for row in signed_base['keys'].values())
    if verdict.get('u10_1_t8_lit_total') != expected_lit or verdict.get('measured') != expected_lit:
        return 'all signed U10.1T8-lit keys must be measured'
    if verdict.get('same_or_lit_within_k_of_n') != expected_lit or verdict.get('confirmed_regressions') != 0:
        return 'Stage A k/n regression gate not passed'
    if decision.get('confirmed_regressions') != []:
        return 'outer confirmed a regression'
    return None


def verify_candidate(serial, root):
    previous.verify(serial, root, candidate=True)
    identity = json.loads((root / 'identity.json').read_text())
    expected = json.loads((H / 'composition.json').read_text())['candidate_boards'][serial]
    assert not identity['diff'] and not identity['absent'], 'candidate identity mismatch'
    assert identity['fingerprints'] == expected['fingerprints'], 'candidate fingerprint mismatch'
    assert identity['identity_assertions'] == expected['identity_assertions'] >= 318, '318 baseline identities must remain covered'
    # U12 adds three members: verify all321, never silently discard those new paths.
    identity['base_identity_assertions'] = 318
    (root / 'candidate-318.json').write_text(json.dumps(identity, indent=2) + '\n')


def stage_a_admission(decision_path):
    composition = json.loads((H / 'composition.json').read_text())
    baseline = json.loads((M / 'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json').read_text())
    decision = json.loads(decision_path.read_text()) if decision_path and decision_path.is_file() else None
    reason = retention_reason(decision, composition, baseline, {'passed': True})
    assert reason is None, 'Stage A prerequisite: ' + str(reason)
    assert decision.get('phase') == 'A', 'Stage A screenshot signoff required'
    assert decision.get('promotion_authorized') is True, 'separate Stage B outer authorization required'


def record_window(serial, root, plan_path, phase):
    plan = json.loads(plan_path.read_text())
    composition = json.loads((H / 'composition.json').read_text())
    assert plan['serial'] == serial and plan['phase'] == phase, 'plan serial/phase mismatch'
    assert plan['bundle_sha256'] == composition['bundle_sha256'], 'plan bundle drift'
    assert plan['package_manifest_sha256'] == composition['native_manifest_sha256'], 'plan manifest drift'
    root.mkdir(parents=True, exist_ok=True)
    receipt = root / 'window-input.json'
    assert not receipt.exists(), 'fresh window output required'
    receipt.write_text(json.dumps({'serial': serial, 'phase': plan['phase'],
        'bundle_sha256': composition['bundle_sha256'],
        'package_manifest_sha256': composition['native_manifest_sha256'],
        'expected_fingerprints': json.loads((H / 'expected-run.json').read_text())['boards'][serial]['fingerprints'],
        'assigned_shards': {shard['name']: Path(os.path.expanduser(os.path.expandvars(shard['keys_file']))).read_text().split() for shard in plan['shards']},
        'plan_sha256': gb.sha(plan_path), 'plan': plan}, indent=2) + '\n')


def finish_observation(serial, root, restored_spec):
    # No decision file can override Stage A's unconditional rollback.
    root.mkdir(parents=True, exist_ok=True)
    (root / 'retention.json').write_text(json.dumps({'retained': False, 'phase': 'A',
        'reason': 'observation window always restores signed U10.1T8'}, indent=2) + '\n')
    previous.finish(serial, root, restored_spec)
    (root / 'observation-restored.json').write_text(json.dumps({'passed': True, 'serial': serial,
        'identity_assertions': 318, 'recovery_smoke': 'PASS', 'final_U10_1_T8': 'PASS'}, indent=2) + '\n')


def finish(serial, root, restored_spec, decision_path, stage_a_path=None):
    composition = json.loads((H / 'composition.json').read_text())
    baseline = json.loads((M / 'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json').read_text())
    smoke_path = root / 'runner/smoke/smoke-result.json'
    smoke = json.loads(smoke_path.read_text()) if smoke_path.is_file() else None
    decision = json.loads(decision_path.read_text()) if decision_path.is_file() else None
    reason = 'Stage A prerequisite absent'
    if stage_a_path is not None:
        try:
            stage_a_admission(stage_a_path)
            assert smoke and smoke.get('passed') is True, 'fresh activation smoke did not pass'
            assert isinstance(decision, dict) and decision.get('signed_by') == 'outer(claude)', 'fresh outer screenshot review absent'
            assert decision.get('serial') == serial and decision.get('phase') == 'B', 'fresh same-board Stage B decision required'
            assert decision.get('window_root') == str(root), 'fresh window-bound decision required'
            assert decision.get('bundle_sha256') == composition['bundle_sha256'], 'fresh decision bundle mismatch'
            assert decision.get('native_manifest_sha256') == composition['native_manifest_sha256'], 'fresh decision manifest mismatch'
            assert decision.get('controls_t20_lit') == ['helloworld', 'zigzag'], 'fresh HW/ZZ t20 not signed bright'
            assert decision.get('confirmed_regressions') == [], 'fresh confirmed regression'
            reason = None
        except Exception as error:
            reason = str(error)
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
    # Existing stopped-parent rollback includes exact U10.1T8 identity checks and OrganicMaps cold_stop.
    previous.finish(serial, root, restored_spec)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', choices=sorted(lab_paths.boards('oh')), required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--restored-spec', type=Path)
    parser.add_argument('--decision', type=Path)
    parser.add_argument('--stage-a-decision', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--phase', choices=['A', 'B'], default='A')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply', action='store_true')
    group.add_argument('--finish', action='store_true')
    group.add_argument('--finish-observation', action='store_true')
    group.add_argument('--verify-candidate', action='store_true')
    group.add_argument('--verify-base', action='store_true')
    args = parser.parse_args()
    if args.apply:
        admission()  # No VM call or Board exists before admission succeeds.
        if args.phase == 'B':
            stage_a_admission(args.stage_a_decision)
        assert args.plan is not None
        record_window(args.serial, args.root, args.plan, args.phase)
        previous.verify(args.serial, args.root / 'baseline')
        previous.executor(args.serial, args.root)
        verify_candidate(args.serial, args.root / 'post-apply')
    elif args.verify_base:
        previous.verify(args.serial, args.root)
    elif args.verify_candidate:
        verify_candidate(args.serial, args.root)
    elif args.finish_observation:
        assert args.restored_spec is not None
        finish_observation(args.serial, args.root, args.restored_spec)
    else:
        assert args.restored_spec is not None and args.decision is not None
        finish(args.serial, args.root, args.restored_spec, args.decision, args.stage_a_decision)


if __name__ == '__main__':
    main()
