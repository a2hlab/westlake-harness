#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--runtime-sha256', required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    if digest(source) != args.source_sha256:
        raise SystemExit('REFUSE source SHA drift')
    sys.dont_write_bytecode = True
    workspace = Path(os.environ['WORKSPACES']).resolve()
    namespace = {'__name__': 'independent_partialboot', '__file__': str(source)}
    exec(compile(source.read_text(), str(source), 'exec'), namespace)
    real_load = namespace['load']
    results = []
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent / '.artifacts') as temporary:
        root = Path(temporary)
        namespace['prepare'](SimpleNamespace(main=str(workspace / 'westlake-harness'), runtime=args.runtime.resolve(), runtime_sha256=args.runtime_sha256, hdc='/FORBIDDEN_DEVICE_TRANSPORT', out=root / 'package'))
        plan = json.loads((root / 'package/plan.disabled.json').read_text())
        plan['execution_enabled'] = True
        plan_path = root / 'enabled.json'
        plan_path.write_text(json.dumps(plan))
        plan_sha = digest(plan_path)
        holder = 'outer(codex) 999 2026-10-13T18:00:00+0800'
        real_subprocess_run = subprocess.run

        def held_only(argv, **kwargs):
            if argv[0] != 'bash' or argv[2:] != ['held', plan['serial']]:
                raise AssertionError('Unexpected external command: ' + repr(argv))
            return SimpleNamespace(returncode=0, stdout=holder + '\n', stderr='')

        try:
            subprocess.run = held_only
            for case in ('partial_boot_runtime187', 'foreign_source'):
                out = root / case
                out.mkdir()
                rows = []
                objects = {row['target']: dict(row['before']) for row in plan['preserved']}
                for number, row in enumerate(plan['members']):
                    backup = 'backup-%03d' % number
                    shutil.copyfile(namespace['resolve'](row['before']['source']), out / backup)
                    rows.append(dict(target=row['target'], before=row['before'], backup=backup, candidate_sha256=row['sha256']))
                    objects[row['target']] = dict(exists=True, sha256=row['sha256'], **row['after'])
                if case == 'foreign_source':
                    objects[plan['members'][0]['target']]['sha256'] = 'f' * 64
                (out / 'transaction.json').write_text(json.dumps(dict(plan_sha256=plan_sha, serial=plan['serial'], boot_id=plan['boot_id'], backups=rows)))
                boot = '11111111-2222-3333-4444-555555555555'
                auth = dict(approved_by='outer(codex)', plan_sha256=plan_sha, serial=plan['serial'], origin_boot_id=plan['boot_id'], boot_id=boot, expires_epoch=time.time() + 600, action='rollback', holder=holder, live_runtime_sha256='18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae', source_restore_only=True)
                auth_path = out / 'auth.json'
                auth_path.write_text(json.dumps(auth))
                calls = []

                class FakeDevice:
                    def __init__(self, *_):
                        pass

                    def command(self, name, argv):
                        calls.append(name)
                        return ''

                    def probe(self, target):
                        self.command('probe', [])
                        if target == namespace['RT'] or target in {row['target'] for row in plan['binds']}:
                            raise AssertionError('Ephemeral partial binds gated source rollback: ' + target)
                        return dict(objects[target])

                    def send(self, name, path, target):
                        self.command(name, [])
                        objects[target] = dict(exists=True, sha256=digest(path))

                    def shell(self, name, script):
                        self.command(name, [])
                        if name == 'boot':
                            return boot
                        if name == 'stage-metadata':
                            target = shlex.split(script)[-1]
                            owner = next(row for row in plan['members'] if target.startswith(row['target'] + '.successor-'))
                            objects[target].update(owner['after'])
                        if name == 'atomic-replace':
                            stage, target = shlex.split(script)[-2:]
                            objects[target] = objects.pop(stage)
                        return ''

                def load_with_fake_transport(reference, name):
                    module = real_load(reference, name)
                    if name == 'successor_core':
                        module.Device = FakeDevice
                    return module

                namespace['load'] = load_with_fake_transport
                previous_argv = sys.argv
                sys.argv = [str(source), 'run', '--plan', str(plan_path), '--action', 'rollback', '--out', str(out), '--execute', '--authorization', str(auth_path), '--authorization-sha256', digest(auth_path)]
                error = None
                try:
                    namespace['main']()
                except (ValueError, KeyError, OSError, AssertionError) as failure:
                    error = str(failure)
                finally:
                    sys.argv = previous_argv
                receipts = [json.loads(path.read_text()) for path in out.glob('source-rollback-*.json')]
                results.append(dict(case=case, actual_cli_parser=True, actual_validate=True, original_transaction_preflight=True, error=error, source_restored=all(objects[row['target']] == {key: value for key, value in row['before'].items() if key != 'source'} for row in plan['members']), stage_send_count=calls.count('atomic-stage'), success_receipts=receipts, device_calls=0))
        finally:
            subprocess.run = real_subprocess_run
    if digest(source) != args.source_sha256:
        raise SystemExit('REFUSE source changed during review')
    print(json.dumps({'source_sha256': args.source_sha256, 'external_boundary': 'Only local held and Device transport mocked; CLI, validate, original rollback_preflight and atomic_place executed.', 'results': results}, indent=2))


if __name__ == '__main__':
    main()
