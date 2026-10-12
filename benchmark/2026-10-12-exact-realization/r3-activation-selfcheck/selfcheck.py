#!/usr/bin/env python3
"""Independently pinned activation-history admission for read-only selfcheck.

No executor/lock/restore action is invoked. An expired historical admission is
checked as placement evidence, never treated as renewed execution authority.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent
FROZEN_SHA = {
    'realization.py': '15a6dc52ee250a9277886dad9f3eb780f7c2dc2a81d934c6fa0ae95ad5aafc14',
    'observations.py': 'e13396359c7edd4686708b4a761bb0ee26c5b3fd540873a5a9d4eacc9932d764',
    'restore.py': 'f19d1258e09ed6132f07e785462ebc67b400e6f1549a0826b843eadbffc0ee54',
    'selfcheck.py': 'a0333c67229c3523943c6182a772fe4a60d6b9a9f1ae36f8186a81e056ea99d3',
    'seal_checks.py': 'ff23281e9a918943c87dfd33e422350e5f00184e4ddd5ddeac290daa14e899f5',
    'sameboard.py': '93810743e3188de6cc6dd91893318eb52a2a6ce93ab61fc40179217114f3bf7e',
    'appendix.py': 'fa4312a6dd399041a1e04e04f52544ebf0061f1a9cfddfcbd9671f47237e39f0',
}
RESTORE_ADAPTERS = {FROZEN_SHA['restore.py'], 'af1ce6fc2f6b43568e8acec9f06cd63c92f48aa10c49c6b3a16c7c39258b2f05'}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def dependencies(root=FROZEN):
    for name, sha in FROZEN_SHA.items():
        need(digest(root / name) == sha, 'frozen dependency drift: ' + name)
    sys.path.insert(0, str(root))
    # Explicitly select pinned modules, rather than inheriting caller imports.
    observation = load(root / 'observations.py', 'observations')
    core = load(root / 'realization.py', 'realization')
    load(root / 'seal_checks.py', 'seal_checks')
    restore = load(root / 'restore.py', 'activation_frozen_restore')
    checker = load(root / 'selfcheck.py', 'activation_frozen_selfcheck')
    return core, observation, restore, checker


r, obs, restore, original_check = dependencies()


def select_frozen(proof_path):
    """Use the proof's independently pinned generator location, identical bytes.

    Frozen proofs encode generator/validator paths; selecting that verified
    directory preserves exact regeneration across worktrees without rewriting.
    """
    global r, obs, restore, original_check
    path = Path(proof_path).resolve()
    generator = obs.pin(obs.read_json(path)['generator'], path.parent)
    need(generator.name == 'realization.py', 'unexpected generator filename')
    r, obs, restore, original_check = dependencies(generator.parent)


def validate_proof_synthetic(proof, binding):
    identity = read(r.pin(proof['source_identity'], Path(proof['request']['path']).parent))
    docs = [identity, proof['parameter_evidence']]
    docs.extend(row['parameter_evidence'] for row in proof.get('source_window_normalization', []))
    for document in docs:
        need(type(document.get('synthetic', False)) is bool, 'proof synthetic flag invalid')
        need(not document.get('synthetic', False) or binding['synthetic'], 'synthetic proof evidence mislabeled as actual history')


def pin(ref, base):
    return obs.pin(ref, base)


def read(path):
    return obs.read_json(path)


def portable(path):
    root = obs.workspace_root(HERE)
    path = Path(path).resolve()
    try:
        return '$WORKSPACES/' + str(path.relative_to(root))
    except ValueError:
        return str(path)


def pinned(path):
    return {'path': portable(path), 'sha256': digest(path)}


def verify_appendix(binding, base, origin, final):
    prior = {row['target']: row['sha256'] for row in origin['files']}
    after = {row['target']: row['sha256'] for row in final['files']}
    need(final['parameters'] == origin['parameters'], 'final proof changes placement parameters')
    need(final['prepared_manifest_sha256'] == origin['prepared_manifest_sha256'], 'final proof changes frozen prepared manifest')
    need(all(after.get(target) == sha for target, sha in prior.items()), 'final proof changes an existing candidate target')
    if binding.get('appendix') is None:
        need(final['proof_sha256'] == origin['proof_sha256'], 'different final proof requires pinned appendix')
        return None
    path = pin(binding['appendix'], base)
    appendix = read(path)
    need(appendix.get('schema') == 'exact-final-seal-appendix/v1', 'appendix schema')
    need(appendix.get('status') == 'UNSIGNED_REQUIRES_OUTER_SIGNOFF' and appendix.get('signed_by') is None, 'unexpected appendix authority')
    need(appendix.get('generator_sha256') == FROZEN_SHA['appendix.py'], 'appendix generator drift')
    need(origin['source_identity']['kind'] == 'candidate-fingerprint' and final['source_identity']['kind'] == 'seal', 'appendix identity kinds')
    candidate_path = pin(appendix['candidate_realization'], path.parent)
    sealed_path = pin(appendix['sealed_realization'], path.parent)
    need(digest(candidate_path) == origin['proof_sha256'] and digest(sealed_path) == final['proof_sha256'], 'appendix proof binding mismatch')
    need(appendix['candidate_source_identity'] == origin['source_identity'], 'appendix candidate identity mismatch')
    need(appendix['source_seal'] == final['source_seal'], 'appendix real seal mismatch')
    need(appendix['complete_target_sha256'] == after, 'appendix complete file set mismatch')
    extra = {target: sha for target, sha in after.items() if target not in prior}
    need(appendix['additional_static_targets'] == extra, 'appendix static target mismatch')
    need(appendix['source_window_normalization'] == final['source_window_normalization'], 'appendix source window evidence mismatch')
    for row in final['files']:
        if row['target'] in extra:
            need(row.get('edits') == [] and row['sha256'] == row['template_sha256'], 'appendix extra is not an unchanged static file')
    return {'pin': binding['appendix'], 'additional_static_targets': extra, 'source_seal': final['source_seal'],
            'signature_status': 'UNSIGNED_REQUIRES_OUTER_SIGNOFF'}


def ast_function(path, name):
    nodes = [node for node in ast.parse(Path(path).read_text()).body if isinstance(node, ast.FunctionDef) and node.name == name]
    need(len(nodes) == 1, 'adapter function missing/duplicate: ' + name)
    return ast.dump(nodes[0], include_attributes=False)


def command_fields(command):
    need(isinstance(command, list) and all(isinstance(x, str) for x in command), 'parent command malformed')
    need(len(command) == 13 and command[2] == '--plan', 'parent executor argv shape')
    # --execute is a flag; all remaining named arguments each occur exactly once.
    need(command[4] == '--execute' and command[5] == '--authorization' and command[7] == '--authorization-sha256'
         and command[9] == '--out' and command[11] == '--action' and command[12] == 'apply', 'parent executor argv/action')
    return {'executor': command[1], 'plan': command[3], 'authorization': command[6],
            'authorization_sha256': command[8], 'out': command[10]}


def validate_history(binding, base, origin):
    """Validate actual parent success and all transaction members; no execution."""
    execution_path = pin(binding['execution_receipt'], base)
    execution = read(execution_path)
    need(execution.get('schema') == 'exact-restoration-receipt/v1', 'parent execution receipt schema')
    need(type(execution.get('executor_rc')) is int and execution['executor_rc'] == 0, 'parent executor did not succeed (executor_rc must be 0)')
    need(execution.get('action') == 'apply', 'parent action was not apply')
    need(execution.get('realization_sha256') == origin['proof_sha256'], 'parent origin realization mismatch')
    need(execution.get('source_identity') == origin['source_identity'] and execution.get('source_seal') == origin['source_seal'], 'parent source identity/seal mismatch')
    need(execution.get('seal_signed') is False and execution.get('ui_accepted') is False, 'parent placement claims unexpected acceptance')
    manifest_path = pin(binding['prepared_manifest'], base)
    package = manifest_path.parent
    plan, prepared = restore.checked_package(origin, package)
    need(digest(package / 'executor.py') == r.EXECUTOR_SHA, 'executor byte drift')
    disabled = read(origin['package'] / 'plan.json')
    old = {row['target']: row for row in disabled['members']}
    new = {row['target']: row for row in plan['members']}
    need(len(plan['members']) == len(old) == len(new) == 487 and set(old) == set(new), 'activation target set is not exact 487')
    allowed = {origin['parameters']['control_root'] + '/startup.env', origin['parameters']['control_root'] + '/startup.expected.sha256'}
    changes = []
    for target, row in new.items():
        need({k: v for k, v in row.items() if k != 'sha256'} == {k: v for k, v in old[target].items() if k != 'sha256'}, 'activation member source/preimage/metadata drift: ' + target)
        if row['sha256'] != old[target]['sha256']:
            need(target in allowed, 'activation changed unapproved target: ' + target)
            changes.append({'target': target, 'disabled_sha256': old[target]['sha256'], 'activated_sha256': row['sha256']})
    need({row['target'] for row in changes} == allowed, 'activation must change exactly startup.env and startup.expected.sha256')
    need({k: v for k, v in plan.items() if k not in {'members', 'execution_enabled'}} ==
         {k: v for k, v in disabled.items() if k not in {'members', 'execution_enabled'}}, 'activation plan context changed')
    need(plan['execution_enabled'] is True and disabled['execution_enabled'] is False, 'activation policy mismatch')
    adapter = pin(binding['restore_adapter'], base)
    need(digest(adapter) in RESTORE_ADAPTERS, 'unreviewed restore adapter')
    for function in ('prepare', 'checked_package'):
        need(ast_function(adapter, function) == ast_function(FROZEN / 'restore.py', function), 'r2 changed activation generation: ' + function)
    admission_path = pin(binding['admission'], base)
    admission = read(admission_path)
    need(admission.get('schema') == 'exact-realization-admission/v1' and admission.get('admitted') is True and admission.get('signed_by') == 'outer(claude)', 'historical admission role/status')
    for key, expected in {'generator_sha256': digest(adapter), 'realization_sha256': origin['proof_sha256'],
                          'source_identity_sha256': origin['source_identity']['sha256'],
                          'source_seal_sha256': origin['source_seal']['sha256'] if origin['source_seal'] else None,
                          'prepared_manifest_sha256': digest(manifest_path), 'plan_sha256': prepared['plan_sha256'],
                          'executor_sha256': r.EXECUTOR_SHA, 'serial': plan['serial'], 'boot_id': plan['boot_id'], 'action': 'apply'}.items():
        need(key in admission and admission[key] == expected, 'historical admission binding drift: ' + key)
    need(admission.get('target_sha256') == {target: row['sha256'] for target, row in new.items()}, 'admission full target SHA map differs')
    expiry = admission.get('expires_epoch')
    need(type(expiry) in (int, float) and math.isfinite(expiry), 'historical admission expiry absent/nonfinite')
    need(execution['plan_sha256'] == prepared['plan_sha256'], 'parent plan SHA differs')
    args = command_fields(execution.get('command'))
    cwd = r.resolve(binding.get('execution_cwd'), base).resolve()
    lock_path = pin(admission['lock_tool'], cwd)
    need(r.resolve(args['executor'], cwd).resolve() == (package / 'executor.py').resolve(), 'parent executor path differs')
    need(r.resolve(args['plan'], cwd).resolve() == (package / 'plan.json').resolve(), 'parent plan path differs')
    auth_path = pin({'path': str(r.resolve(args['authorization'], cwd)), 'sha256': args['authorization_sha256']}, base)
    authorization = read(auth_path)
    for key, expected in {'approved_by': 'outer(codex)', 'plan_sha256': prepared['plan_sha256'], 'serial': plan['serial'],
                          'boot_id': plan['boot_id'], 'derived_manifest_sha256': digest(manifest_path),
                          'actions': ['place-only', 'one-reboot', 'rollback-safe'], 'holder': admission.get('holder')}.items():
        need(authorization.get(key) == expected, 'historical executor authorization differs: ' + key)
    need(isinstance(admission.get('holder'), str) and admission['holder'], 'historical holder absent')
    need(authorization.get('origin_boot_id', plan['boot_id']) == plan['boot_id'], 'authorization origin boot differs')
    need(type(authorization.get('expires_epoch')) in (int, float) and math.isfinite(authorization['expires_epoch']), 'authorization expiry absent/nonfinite')
    tx_path = pin(binding['transaction'], base)
    need(r.resolve(args['out'], cwd).resolve() == tx_path.parent.resolve(), 'parent transaction output differs')
    need(tx_path.name == 'transaction.json', 'transaction receipt filename differs')
    tx = read(tx_path)
    for document in (execution, admission, authorization, tx):
        need(type(document.get('synthetic', False)) is bool, 'historical synthetic flag invalid')
        need(not document.get('synthetic', False) or binding['synthetic'], 'synthetic history mislabeled as actual')
    need(tx.get('plan_sha256') == prepared['plan_sha256'] and tx.get('serial') == plan['serial'] and tx.get('boot_id') == plan['boot_id'], 'transaction plan/serial/origin boot differs')
    backups = tx.get('backups')
    need(isinstance(backups, list) and len(backups) == 487, 'transaction backup set incomplete')
    refs = binding.get('member_receipts')
    need(isinstance(refs, list) and len(refs) == 487, 'placed receipt set incomplete')
    need({p.name for p in tx_path.parent.glob('placed-*.json')} == {f'placed-{n:03d}.json' for n in range(487)}, 'transaction placed receipt names differ')
    need(not list(tx_path.parent.glob('failed-*.json')) and not (tx_path.parent / 'rollback.json').exists(), 'failed/rolled-back transaction cannot establish successful activation')
    receipt_pins, backup_pins = [], []
    for n, member in enumerate(plan['members']):
        expected_backup = {'target': member['target'], 'before': member['before'],
                           'backup': f'backup-{n:03d}' if member['before']['exists'] else None,
                           'candidate_sha256': member['sha256']}
        need(backups[n] == expected_backup, 'transaction preimage/member mismatch: ' + str(n))
        if expected_backup['backup']:
            path = tx_path.parent / expected_backup['backup']
            need(path.is_file() and not path.is_symlink() and digest(path) == member['before']['sha256'], 'transaction backup bytes drift: ' + str(n))
            backup_pins.append(pinned(path))
        path = pin(refs[n], base)
        need(path.parent == tx_path.parent and path.name == f'placed-{n:03d}.json', 'placed receipt index/path differs')
        need(read(path) == {'target': member['target'], 'sha256': member['sha256']}, 'placed target/SHA mismatch: ' + str(n))
        receipt_pins.append(refs[n])
    placed_path = pin(binding['placed'], base)
    need(placed_path == tx_path.parent / 'placed.json', 'placed completion path differs')
    need(read(placed_path) == {'state': 'PLACED_ONLY', 'ui_accepted': False, 'seal_signed': False, 'reboots': 0}, 'transaction completion is not exact PLACED_ONLY')
    return {'plan': plan, 'changes': changes, 'prepared': prepared,
            'evidence': {'prepared_manifest': binding['prepared_manifest'], 'admission': binding['admission'],
                         'restore_adapter': binding['restore_adapter'], 'execution_receipt': binding['execution_receipt'],
                         'authorization': pinned(auth_path), 'lock_tool': pinned(lock_path), 'transaction': binding['transaction'], 'placed': binding['placed'],
                         'member_receipts': receipt_pins, 'backups': backup_pins, 'origin_boot_id': plan['boot_id'],
                         'admission_expired_now': expiry <= time.time(), 'historical_only': True,
                         'execution_authority_created': False, 'executor_rc': 0, 'placed_count': 487}}


def admit(binding_path, binding_sha, offline):
    base = Path(binding_path).resolve().parent
    path = pin({'path': str(binding_path), 'sha256': binding_sha}, base)
    binding = read(path)
    need(binding.get('schema') == 'exact-activation-selfcheck-binding/v1', 'activation binding schema')
    need(binding.get('checker_sha256') == digest(__file__), 'activation checker independent self pin')
    need(type(binding.get('synthetic')) is bool, 'binding must explicitly declare synthetic')
    need(offline or binding['synthetic'] is False, 'synthetic transaction recordings cannot yield live PASS')
    # Reject a failed actual parent early, before expensive reproduction or missing journals.
    parent = read(pin(binding['execution_receipt'], base))
    need(type(parent.get('executor_rc')) is int and parent['executor_rc'] == 0, 'parent executor did not succeed (executor_rc must be 0)')
    origin_path = pin(binding['origin_realization'], base)
    final_path = pin(binding['realization'], base)
    select_frozen(origin_path)
    origin = r.verify(origin_path)
    final = origin if final_path == origin_path else r.verify(final_path)
    need(origin.get('phase') == 'placement' and origin.get('purpose') != 'same-board-selfcheck', 'activation requires placement origin')
    appendix = verify_appendix(binding, base, origin, final)
    history = validate_history(binding, base, origin)
    for proof in (origin, final):
        validate_proof_synthetic(proof, binding)
    activated = copy.deepcopy(final)
    by_target = {row['target']: row for row in activated['files']}
    for change in history['changes']:
        need(by_target[change['target']]['sha256'] == change['disabled_sha256'], 'final proof startup template differs')
        by_target[change['target']]['sha256'] = change['activated_sha256']
    return activated, {'schema': 'exact-activation-readonly-admission/v1', 'binding': pinned(path),
                       'origin_realization': binding['origin_realization'], 'realization': binding['realization'],
                       'source_identity': final['source_identity'], 'source_seal': final['source_seal'],
                       'appendix': appendix, 'activation_changes': history['changes'],
                       'history': history['evidence'], 'synthetic': binding['synthetic'],
                       'execution_authority_created': False, 'device_write_operations': 0}


def compare(proof, history, observation, base, serial, current_boot, offline):
    need(proof['parameters']['serial'] == serial, 'requested serial differs from activated proof')
    result = original_check.compare(proof, observation, base, serial, current_boot, offline)
    result['schema'] = 'exact-activation-selfcheck/v1'
    result['activation'] = history
    result['historical_admission_is_not_reexecution_authority'] = True
    result['synthetic_transaction_recordings'] = history['synthetic']
    need(offline or history['synthetic'] is False, 'synthetic history cannot yield live PASS')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activation-binding', type=Path, required=True)
    parser.add_argument('--binding-sha256', required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--boot-id', required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--observed', type=Path, help='offline recordings, never live PASS')
    modes.add_argument('--hdc', help='explicit HDC executable for read-only collection by outer')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        need(not args.out.exists() and not args.out.is_symlink() and args.out.parent.is_dir(), 'fresh output in existing directory required')
        need(obs.BOOT.fullmatch(args.boot_id), 'independent current boot UUID required')
        proof, history = admit(args.activation_binding, args.binding_sha256, bool(args.observed))
        need(proof['parameters']['serial'] == args.serial, 'wrong serial')
        observed_path = args.observed if args.observed else original_check.collect_live(
            proof, args.serial, args.boot_id, args.hdc, args.out.parent / (args.out.name + '.evidence'))
        result = compare(proof, history, read(observed_path), Path(observed_path).parent,
                         args.serial, args.boot_id, bool(args.observed))
        with args.out.open('x') as stream:
            json.dump(result, stream, indent=2); stream.write('\n')
        print(result['status'])
        return 0 if result['passed'] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('REJECT ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
