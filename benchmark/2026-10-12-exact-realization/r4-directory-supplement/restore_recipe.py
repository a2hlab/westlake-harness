#!/usr/bin/env python3
"""Explicit composition of existing r2 restoration, history admission and directory completion."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
R2_SHA = '6a5b6bf5a1284304e14fa23def844db36b59c47b014faee1b981fe8bda3bd759'
BUILDER_SHA = '8f8b1553eff79d934383f62e014c5a5869d98f533f8fe8da972b1e1a67594367'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def path(value, base):
    value = value.replace('$WORKSPACES', os.environ.get('WORKSPACES', str(HERE.parents[3])))
    p = Path(value)
    return p if p.is_absolute() else base / p


def pin(ref, base):
    p = path(ref['path'], base)
    need(p.is_file() and digest(p) == ref['sha256'], 'input pin drift: ' + str(p))
    return p


def run(args):
    need(digest(args.directory_recipe) == args.recipe_sha256, 'recipe independent pin mismatch')
    data = json.loads(args.directory_recipe.read_text()); base = args.directory_recipe.resolve().parent
    need(data['schema'] == 'exact-directory-completed-restore/v1', 'recipe schema')
    need(data['mode'] in ('complete-existing-success', 'restore-then-complete'), 'recipe mode')
    need(data['signed_by'] is None, 'recipe is not a signature')
    need(not args.out.exists(), 'fresh recipe evidence directory required')
    core, supplement = data['core'], data['supplement']
    manifest_path = pin(supplement['manifest'], base)
    manifest = json.loads(manifest_path.read_text())
    origin = pin(core['realization'], base)
    need(core['realization']['sha256'] == manifest['origin_realization']['sha256'], 'core/directory origin differs')
    builder = HERE.parent / 'r3-activation-selfcheck/build_binding.py'
    need(digest(builder) == BUILDER_SHA, 'r3 builder drift')
    for field in ('prepared_manifest', 'admission', 'restore_adapter'):
        pin(core[field], base)
    # Preview is local only. It does not require or invent an authorization.
    if not args.execute:
        print(json.dumps({'status': 'OFFLINE_RECIPE_PREVIEW', 'mode': data['mode'], 'steps': ['existing r2 restore or completed history', 'r3 admit all487 receipts', 'authorized single empty directory apply/readback'], 'device_calls': 0, 'ready_to_reboot': False})); return 0
    authorization = pin(supplement['authorization'], base)
    cwd = path(core['execution_cwd'], base)
    txn = path(core['transaction_dir'], base)
    args.out.mkdir(parents=True)
    result = {'schema': 'directory-completed-restore-receipt/v1', 'recipe_sha256': args.recipe_sha256,
              'mode': data['mode'], 'executor_rc': None, 'complete': False, 'reboots': 0,
              'manual_app_start': False, 'old_attempt_modified': False}
    try:
        if data['mode'] == 'restore-then-complete':
            command = json.loads(pin(core['execution_command'], base).read_text())
            need(isinstance(command, list) and len(command) > 2 and all(isinstance(x, str) for x in command), 'core argv required')
            entry = path(command[1], cwd)
            need(entry.name == 'exact_realization.py' and digest(entry) == R2_SHA and '--execute' in command, 'only frozen r2 execution supported')
            need('--transaction-action' not in command or command[command.index('--transaction-action')+1] == 'apply', 'recipe cannot rollback core')
            need(path(command[command.index('--out')+1], cwd).resolve() == txn.resolve(), 'core output differs')
            need(path(command[command.index('--realization')+1], cwd).resolve() == origin.resolve(), 'core origin differs')
            # The fixed r2 adapter retains its own admission, lock and 2700s guards.
            proc = subprocess.run([sys.executable, str(entry), *command[2:]], cwd=cwd)
            result['core_rc'] = proc.returncode
            need(proc.returncode == 0, 'core restoration failed; directory step not run')
        binding = args.out / 'activation-binding.json'
        cmd = [sys.executable, str(builder), '--realization', str(origin), '--origin-realization', str(origin)]
        for key in ('prepared_manifest', 'admission', 'restore_adapter'):
            cmd += ['--' + key.replace('_', '-'), str(pin(core[key], base))]
        cmd += ['--execution-receipt', str(path(core['execution_receipt'], base)), '--transaction-dir', str(txn),
                '--execution-cwd', str(cwd), '--out', str(binding)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        (args.out / 'history.stdout').write_text(proc.stdout); (args.out / 'history.stderr').write_text(proc.stderr)
        need(proc.returncode == 0, 'full487 historical admission failed; directory step not run')
        result['history_binding_sha256'] = digest(binding)
        directory_out = args.out / 'directory-transaction'
        executor = HERE / 'directory_transaction.py'
        need(digest(executor) == manifest['executor_sha256'], 'directory executor pin drift')
        cmd = [sys.executable, str(executor), '--manifest', str(manifest_path), '--manifest-sha256', supplement['manifest']['sha256'],
               '--authorization', str(authorization), '--authorization-sha256', supplement['authorization']['sha256'],
               '--serial', manifest['serial'], '--boot-id', manifest['boot_id'], '--hdc', str(path(supplement['hdc'], base)),
               '--out', str(directory_out), '--action', 'apply', '--execute']
        proc = subprocess.run(cmd, capture_output=True, text=True)
        (args.out / 'directory.stdout').write_text(proc.stdout); (args.out / 'directory.stderr').write_text(proc.stderr)
        result['executor_rc'] = proc.returncode
        need(proc.returncode == 0, 'directory completion failed; restoration is incomplete')
        receipt = directory_out / 'applied.json'; applied = json.loads(receipt.read_text())
        need(type(applied['executor_rc']) is int and applied['executor_rc'] == 0 and applied['state'] in ('CREATED_VERIFIED', 'ALREADY_EQUAL') and applied['manifest_sha256'] == supplement['manifest']['sha256'], 'directory receipt not verified')
        result.update(complete=True, directory_receipt_sha256=digest(receipt), status='RESTORED_WITH_DIRECTORY_COMPLETION_NOT_UI_ACCEPTANCE')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result.update(error=str(exc), complete=False, status='INCOMPLETE_PRESERVE_EVIDENCE')
        return 1
    finally:
        (args.out / 'recipe-receipt.json').write_text(json.dumps(result, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory-recipe', type=Path, required=True)
    p.add_argument('--recipe-sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    try:
        return run(p.parse_args())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('REJECT ' + str(exc), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
