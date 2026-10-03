import argparse
from contextlib import contextmanager
import datetime
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

from core import GATE_TARGETS, digest, encoded, prepared_bytes

HERE = Path(__file__).resolve().parent


def target_path(repo, relative):
    path = repo / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or path.is_symlink() or not path.resolve().is_relative_to(repo.resolve()):
        raise ValueError('Unsafe target path')
    return path


def current_bytes(path):
    return path.read_bytes() if path.exists() else None


def held_empty(result):
    if result.returncode != 1 or result.stdout != b'' or result.stderr != b'':
        raise RuntimeError('Board held or ambiguous held command result')


def check_held(repo, serials, output):
    records = []
    for serial in serials:
        command = ['bash', str(repo / 'scripts/lab/board_note.sh'), 'held', serial]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        records.append(dict(command=command, exit_code=result.returncode,
            stdout=result.stdout.decode(errors='backslashreplace'), stderr=result.stderr.decode(errors='backslashreplace')))
        (output / 'held.json').write_bytes(encoded(records))
        held_empty(result)


@contextmanager
def maintenance_mutexes(serials):
    root = Path(os.environ.get('BOARD_LOCK_DIR', str(Path.home() / '.octos/board-locks')))
    handles = []
    try:
        for serial in sorted(serials):
            path = root / (serial + '.lock')
            if not path.is_file() or path.is_symlink():
                raise RuntimeError('Missing/unsafe existing board mutex: ' + str(path))
            handle = path.open('rb')
            handles.append(handle)
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError('Board mutex busy: ' + serial) from error
        yield
    finally:
        for handle in reversed(handles):
            handle.close()


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.gate-batch-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
            os.fchmod(output.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def verify_prerequisites(repo, plan):
    for item in plan['prerequisites']:
        path = target_path(repo, item['path'])
        if not path.is_file() or digest(path.read_bytes()) != item['sha256']:
            raise RuntimeError('Tool/approval prerequisite SHA mismatch: ' + item['path'])


def verify_new_evidence(repo, plan):
    for item in plan.get('new_evidence_prerequisites', []):
        path = target_path(repo, item['path'])
        if not path.is_file() or digest(path.read_bytes()) != item['sha256']:
            raise RuntimeError('Land referenced evidence before applying gates: ' + item['path'])


def verify_local(here, plan):
    for item in plan.get('local_prerequisites', []):
        if digest((here / item['path']).read_bytes()) != item['sha256']:
            raise RuntimeError('Local application helper drift')


def simulate(repo, here, stages):
    virtual = {}
    expected = []
    for stage in stages:
        for change in stage['changes']:
            relative = change['target']
            path = target_path(repo, relative)
            before = virtual[relative] if relative in virtual else current_bytes(path)
            after = prepared_bytes(change, before, here)
            virtual[relative] = after
            expected.append(dict(stage=stage['name'], target=relative, before_sha256=digest(before) if before is not None else None,
                after_sha256=digest(after)))
    return expected


def validators(repo, commands, output):
    records = []
    for index, command in enumerate(commands, 1):
        result = subprocess.run(command, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        raw = output / f'validator-{index}.txt'
        raw.write_bytes(result.stdout)
        sys.stdout.buffer.write(result.stdout)
        sys.stdout.buffer.flush()
        records.append(dict(command=command, exit_code=result.returncode, raw=raw.name, raw_sha256=digest(result.stdout)))
        (output / 'validators.json').write_bytes(encoded(records))
        if result.returncode != 0:
            raise RuntimeError('Post-write validator refused: ' + command[1])
    return records


def original_policy_check(change):
    if change['kind'] != 'derive-static-policy':
        return
    ws = Path(os.environ.get('WORKSPACES', str(HERE.parents[2])))
    original = change['original_policy']
    path = Path(original['path'].replace('$WORKSPACES', str(ws)))
    if digest(path.read_bytes()) != original['sha256']:
        raise RuntimeError('Authorized original static policy drift')


def restore(repo, output, journal, write=atomic_write):
    prepared = []
    for record in journal['originals'].values():
        static_targets = {'benchmark/2026-10-03-u15-u16-gate-batch/.artifacts/applied-static/static-policy-' + version + '-approved.json' for version in ['u15', 'u16']}
        if record['target'] not in GATE_TARGETS | static_targets:
            raise RuntimeError('Rollback target not in this gate batch')
        path = target_path(repo, record['target'])
        current = current_bytes(path)
        current_sha = digest(current) if current is not None else None
        if current_sha not in record['allowed_postimages'] + [record['sha256']]:
            raise RuntimeError('Rollback refuses external target drift: ' + record['target'])
        data = None
        if record['sha256'] is not None:
            if Path(record['backup']).name != record['backup']:
                raise RuntimeError('Unsafe rollback backup path')
            data = (output / record['backup']).read_bytes()
            if digest(data) != record['sha256']:
                raise RuntimeError('Rollback backup SHA mismatch')
        prepared.append((record, path, data))
    for record, path, data in reversed(prepared):
        if record['sha256'] is None:
            if path.exists():
                path.unlink()
        else:
            write(path, data, record['mode'])
    journal['status'] = 'rolled-back'
    (output / 'journal.json').write_bytes(encoded(journal))


def transaction(repo, here, plan, stages, output, held, validate, write=atomic_write):
    simulate(repo, here, stages)
    journal = dict(status='running', originals={}, completed=[], changes=[])
    (output / 'journal.json').write_bytes(encoded(journal))
    try:
        for stage in stages:
            stage_out = output / stage['name']
            stage_out.mkdir()
            held(repo, plan['serials'], stage_out)
            verify_local(here, plan)
            if 'prerequisites' in plan:
                verify_prerequisites(repo, plan)
                verify_new_evidence(repo, plan)
            pending = []
            for change in stage['changes']:
                original_policy_check(change)
                path = target_path(repo, change['target'])
                before = current_bytes(path)
                after = prepared_bytes(change, before, here)
                pending.append((change, path, before, after))
            for change, path, before, after in pending:
                relative = change['target']
                mode = stat.S_IMODE(path.stat().st_mode) if before is not None else 0o644
                if relative not in journal['originals']:
                    backup = 'backup-' + str(len(journal['originals'])) + '.bin'
                    if before is not None:
                        (output / backup).write_bytes(before)
                    journal['originals'][relative] = dict(target=relative, sha256=digest(before) if before is not None else None,
                        backup=backup if before is not None else None, mode=mode, allowed_postimages=[])
                journal['originals'][relative]['allowed_postimages'].append(digest(after))
                (output / 'journal.json').write_bytes(encoded(journal))
                if current_bytes(path) != before:
                    raise RuntimeError('Target changed immediately before write')
                write(path, after, mode)
                if digest(path.read_bytes()) != change['after_sha256']:
                    raise RuntimeError('Target changed after write')
                journal['changes'].append(dict(stage=stage['name'], target=relative, after_sha256=digest(after)))
                (output / 'journal.json').write_bytes(encoded(journal))
            validate(repo, plan['selftests'], stage_out)
            verify_local(here, plan)
            if 'prerequisites' in plan:
                verify_prerequisites(repo, plan)
                verify_new_evidence(repo, plan)
            held(repo, plan['serials'], stage_out)
            journal['completed'].append(stage['name'])
            (output / 'journal.json').write_bytes(encoded(journal))
        journal['status'] = 'applied'
        (output / 'journal.json').write_bytes(encoded(journal))
        return journal
    except BaseException as error:
        journal['error'] = str(error)
        try:
            restore(repo, output, journal)
        except BaseException as rollback_error:
            journal['status'] = 'rollback-refused'
            journal['rollback_error'] = str(rollback_error)
            (output / 'journal.json').write_bytes(encoded(journal))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(os.environ.get('WORKSPACES', str(HERE.parents[2]))) / 'westlake-harness')
    parser.add_argument('--expected-plan-sha', required=True)
    parser.add_argument('--outer-apply', action='store_true')
    parser.add_argument('--stage', choices=['all', 'native-u15', 'native-u16', 'image-u16', 'static-policy'], default='all')
    parser.add_argument('--rollback', type=Path)
    args = parser.parse_args()
    plan_file = HERE / 'change-plan.json'
    if digest(plan_file.read_bytes()) != args.expected_plan_sha:
        raise RuntimeError('Signed changeset plan identity drift')
    plan = json.loads(plan_file.read_text())
    verify_local(HERE, plan)
    repo = args.repo.resolve()
    verify_prerequisites(repo, plan)
    stages = [stage for stage in plan['stages'] if args.stage == 'all' or stage['name'] == args.stage]
    if not args.outer_apply:
        if args.rollback:
            raise RuntimeError('Rollback requires explicit outer flag')
        print(json.dumps(dict(mode='read-only-preview', writes=0, board_access=False,
            changes=simulate(repo, HERE, stages)), indent=2))
        return
    timestamp = datetime.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S')
    output = HERE / '.artifacts' / f'apply-{timestamp}-{os.getpid()}'
    output.mkdir(parents=True, exist_ok=False)
    verify_new_evidence(repo, plan)
    check_held(repo, plan['serials'], output)
    with maintenance_mutexes(plan['serials']):
        check_held(repo, plan['serials'], output)
        verify_prerequisites(repo, plan)
        if args.rollback:
            previous = args.rollback.resolve()
            journal = json.loads((previous / 'journal.json').read_text())
            if (previous / 'plan-sha.txt').read_text().strip() != args.expected_plan_sha or journal['status'] != 'applied':
                raise RuntimeError('Rollback receipt is not this applied plan')
            restore(repo, previous, journal)
            validators(repo, plan['selftests'], output)
        else:
            (output / 'plan-sha.txt').write_text(args.expected_plan_sha + '\n')
            transaction(repo, HERE, plan, stages, output, check_held, validators)
        print('OUTER_APPLY_RECEIPT=' + str(output))


if __name__ == '__main__':
    main()
