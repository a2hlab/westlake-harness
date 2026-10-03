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
import lab_paths
sys.path.insert(0, str(lab_paths.harness() / "scripts/lab"))
import generation_bundle as gb
import u7_executor as u

W = lab_paths.workspaces()
M = lab_paths.harness()
spec = importlib.util.spec_from_file_location('u13_transaction_hooks', H.parent / '2026-10-03-u13-stage-a-plan/window_hook.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
spec = importlib.util.spec_from_file_location('u13_retention_criteria', H.parent / '2026-10-03-u13-stage-a-plan/promotion_hook_u13.py')
criteria = importlib.util.module_from_spec(spec)
spec.loader.exec_module(criteria)
CANDIDATE = None

def configure(folder):
    global H, CANDIDATE
    H = folder
    c = json.loads((H / 'composition.json').read_text())
    CANDIDATE = previous.path(c['package'])
    previous.H = H
    original_vm = previous.vm
    def configured_vm(command):
        if len(command) > 1 and str(command[1]) == str(Path(previous.__file__).resolve()):
            command = [command[0], H / 'runner.py', 'hook', *command[2:]]
        return original_vm(command)
    previous.vm = configured_vm

def signed_composition(composition):
    # Stage A was signed before approval metadata was armed. Prove that no other
    # bundle field changed; all actual device identities still bind the armed SHA.
    p = previous.path(composition['package'])
    armed = json.loads((p / 'bundle.json').read_text())
    assert gb.sha(p / 'bundle.json') == composition['bundle_sha256'], 'armed bundle drift'
    unarmed_path = previous.path(composition['unarmed_package']) / 'bundle.json'
    assert gb.sha(unarmed_path) == composition['approved_unarmed_bundle_sha256'], 'signed unarmed bundle drift'
    unarmed = json.loads(unarmed_path.read_text())
    assert armed['rollout_ready'] is True and unarmed['rollout_ready'] is False
    assert armed.get('rollout_blocker') == '', 'armed blocker not cleared'
    assert unarmed.get('rollout_blocker') == 'Real U10.1T8 rebind; fresh two-surface production and outer authorization pending'
    armed['rollout_ready'] = False
    armed['rollout_blocker'] = unarmed['rollout_blocker']
    assert armed == unarmed, 'arming changed payload or other bundle metadata'
    return dict(bundle_sha256=composition['approved_unarmed_bundle_sha256'],
                native_manifest_sha256=composition['native_manifest_sha256'])



def admission():
    composition = json.loads((H / 'composition.json').read_text())
    assert composition.get('execution_enabled') is True, 'promotion paused or not authorized'
    assert gb.sha(CANDIDATE / 'bundle.json') == composition['bundle_sha256'], 'bundle drift'
    assert gb.sha(CANDIDATE / 'native/package.json') == composition['native_manifest_sha256'], 'manifest drift'
    for surface in ('mac', 'vm'):
        proof = json.loads((H / ('gate-' + surface + '-pass.json')).read_text())
        assert proof['bundle_sha256'] == composition['bundle_sha256'], 'offline receipt bundle drift'
        assert proof['native_manifest_sha256'] == composition['native_manifest_sha256'], 'offline receipt manifest drift'
        assert proof['policy_binding'] == u.policy_binding(CANDIDATE), 'offline policy inputs changed after production proof'
        assert proof['production_dry_run_exit_code'] == 0 and proof['gates_passed'] and proof['deployable'], 'offline gates are not all green'
        assert proof['frozen_composed_violations'] == 0, 'effective frozen DEX regression'
        assert proof['static'] == 'PASS' and proof['G1'] and proof['G2'], 'static/image regression'
        assert all(proof['native_findings'][gate]['rejected'] == 0 for gate in ('N1', 'N2')), 'native admission rejected'
    assert composition['rollout_ready'] is True, 'outer package review pending'
    assert json.loads((CANDIDATE / 'bundle.json').read_text())['rollout_ready'] is True, 'bundle is not armed'


def retention_reason(decision, composition, signed_reference, smoke):
    binding = signed_composition(composition)
    return criteria.retention_reason(decision, binding, signed_reference, smoke,
        M / 'benchmark/2026-10-03-u13-stage-a-decision/selftest-u13-stage-a.json',
        M / ('benchmark/2026-10-03-u13-stage-a-decision/selftest-explanations-' + composition['decision_tag'] + '.json'))


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
    baseline = json.loads((M / 'benchmark/2026-10-03-u13-reference/sources.json').read_text())
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
        'expected_fingerprints': composition['candidate_boards'][serial]['fingerprints'],
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
    baseline = json.loads((M / 'benchmark/2026-10-03-u13-reference/sources.json').read_text())
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
            assert decision.get('smoke_sha256') == gb.sha(smoke_path), 'fresh smoke SHA mismatch'
            assert decision.get('identity_sha256') == gb.sha(root / 'post-apply/candidate-318.json'), 'fresh identity SHA mismatch'
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
            (root / 'retention.json').write_text(json.dumps({'retained': True, 'basis': str(decision_path), 'scope': 'complete outer-signed promotion', 'release': 'U13'}, indent=2) + '\n')
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
