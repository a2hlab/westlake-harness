import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
SERIAL = '61b0657200000000000000000324012c'
OLD_BOOT = '2f4be4aa-e0ed-4208-8cfe-db5f1b31bee4'
MARKER = '__61B_RETURN_STATUS__'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def expand(value, workspaces):
    return Path(value.replace('$WORKSPACES', str(workspaces)))


class Recorder:
    def __init__(self, output):
        self.output = output
        self.records = []

    def run(self, command, required=True, timeout=120):
        stem = self.output / f'command-{len(self.records) + 1:04d}'
        try:
            result = subprocess.run(list(map(str, command)), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            result = subprocess.CompletedProcess(command, 124, error.stdout or b'', error.stderr or b'')
        except OSError as error:
            result = subprocess.CompletedProcess(command, 127, b'', str(error).encode())
        stdout, stderr = stem.with_suffix('.stdout'), stem.with_suffix('.stderr')
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        self.records.append(dict(command=list(map(str, command)), exit_code=result.returncode,
            stdout=stdout.name, stderr=stderr.name, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)))
        save(self.output / 'commands.json', self.records)
        if required and result.returncode:
            raise RuntimeError(f'Command refused rc={result.returncode}; see {stem.name}')
        return result


def shell(recorder, hdc, command, required=True):
    wrapped = 'sh -c ' + shlex.quote(command + '; code=$?; printf "\n' + MARKER + '=%d\n" "$code"; exit "$code"')
    result = recorder.run([hdc, '-t', SERIAL, 'shell', wrapped], required=False, timeout=60)
    text = result.stdout.decode(errors='backslashreplace')
    match = re.search(r'\n' + MARKER + r'=(\d+)\s*$', text)
    valid = result.returncode == 0 and match is not None and match.group(1) == '0'
    if required and not valid:
        raise RuntimeError('Readonly HDC response missing success/status marker')
    return text[:match.start()] if match else text, valid


def valid_boot(value):
    value = value.strip()
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value):
        raise RuntimeError('Missing or malformed boot_id')
    return value


def fault_files(inventory, start, end):
    selected = []
    for line in inventory.splitlines():
        epoch, separator, name = line.partition(' ')
        if not separator or not epoch.isdigit():
            raise RuntimeError('Malformed fault inventory; do not silently omit files')
        path = Path(name)
        if not name.startswith('/data/log/faultlog/') or '..' in path.parts:
            raise RuntimeError('Unsafe fault source path')
        if not path.name.startswith(('cppcrash', 'jscrash')):
            continue
        stamped = re.search(r'(20261003)[-_]?(\d{6})', path.name)
        filename_epoch = None
        if stamped:
            date = datetime.datetime.strptime(''.join(stamped.groups()), '%Y%m%d%H%M%S')
            filename_epoch = int(date.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp())
        if start <= int(epoch) <= end or filename_epoch is not None and start <= filename_epoch <= end:
            selected.append(dict(remote=name, mtime_epoch=int(epoch), filename_epoch=filename_epoch))
    return selected


def collect(recorder, hdc, binding, output):
    result = recorder.run([hdc, 'list', 'targets'])
    if SERIAL not in result.stdout.decode(errors='backslashreplace').split():
        raise RuntimeError('61b not present; no recovery or unlock')
    boot, _ = shell(recorder, hdc, 'cat /proc/sys/kernel/random/boot_id')
    boot = valid_boot(boot)
    uptime, _ = shell(recorder, hdc, 'cat /proc/uptime')
    if not re.fullmatch(r'\s*\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s*', uptime):
        raise RuntimeError('Missing or malformed uptime')
    inventory, available = shell(recorder, hdc,
        "find /data/log/faultlog -type f -exec stat -c '%Y %n' {} \\;", required=False)
    selected = fault_files(inventory, binding['incident_start_epoch'], binding['incident_end_epoch']) if available else []
    for number, item in enumerate(selected, 1):
        local = output / f'fault-{number:03d}-{Path(item["remote"]).name}'
        recorder.run([hdc, '-t', SERIAL, 'file', 'recv', item['remote'], local])
        if not local.is_file() or local.stat().st_size == 0:
            raise RuntimeError('Fault receive returned no file; keep lock')
        item.update(local=local.name, sha256=sha(local))
    hilog, hilog_available = shell(recorder, hdc, 'hilog -x', required=False)
    (output / 'hilog.txt').write_text(hilog)
    report = dict(serial=SERIAL, boot_id=boot, previous_boot_id=OLD_BOOT, new_boot=boot != OLD_BOOT,
        note='新 boot:候选的 bind 层可能已随重启消失' if boot != OLD_BOOT else 'Same boot: original rollback remains applicable',
        uptime=uptime.strip(), incident_interval=binding['incident_interval'], fault_inventory_available=available,
        selected_faults=selected, hilog_available=hilog_available and bool(hilog.strip()),
        missing_logs_are_not_proof_of_no_crash=True)
    save(output / 'readonly-evidence.json', report)
    return report


def verify_bindings(binding, workspaces):
    for item in binding['pinned_files']:
        path = expand(item['path'], workspaces)
        if not path.is_file() or sha(path) != item['sha256']:
            raise RuntimeError('Pinned recovery source drift: ' + item['path'])
    journal = json.loads(expand(binding['journal'], workspaces).read_text())
    if journal['status'] != 'active_verified' or journal['serial'] != SERIAL or journal['boot_id'] != OLD_BOOT:
        raise RuntimeError('Not the exact active_verified window2 61b journal')


def held(recorder, master, binding):
    result = recorder.run(['bash', master / 'scripts/lab/board_note.sh', 'held', SERIAL])
    fields = result.stdout.decode().split()
    if (len(fields) != 3 or fields[0] != 'cx-t0' or not fields[1].isdigit()
            or fields[2] != binding['held_since'] or result.stderr):
        raise RuntimeError('61b existing cx-t0 lock is absent or ambiguous; keep state')


def vm_prefix(workspaces):
    return ['orb', '-m', 'a2hlab', 'env', 'WORKSPACES=' + str(workspaces),
        'MAC_HOME=' + os.environ.get('MAC_HOME', str(Path.home())), 'LAB_HOME=' + os.environ.get('LAB_HOME', '$LAB_HOME')]


def recovery_command(binding, workspaces, output, new_boot):
    master = workspaces / 'westlake-harness'
    command = vm_prefix(workspaces) + ['bash', master / 'benchmark/2026-10-01-u7-executor/board61b/run-executor.sh',
        '--restore-baseline' if new_boot else '--rollback', '--serial', SERIAL, '--lane', 'cx-t0']
    journal = expand(binding['journal'], workspaces)
    if new_boot:
        command += ['--from-journal', journal, '--journal', output / 'replay-journal.json']
    else:
        command += ['--journal', journal]
    return command + ['--out', output / 'recovery.json']


def identity(output, binding):
    report = json.loads((output / 'identity.json').read_text())
    if (report.get('state') != 'U13' or report.get('identity_assertions') != 321 or report.get('unique_paths') != 319
            or report.get('diff') != {} or report.get('absent') != [] or report.get('fingerprints') != binding['fingerprints']):
        raise RuntimeError('321 assertion /319 path / fingerprint identity refused')
    view = json.loads((output / 'process-view.json').read_text())
    if (not isinstance(view.get('parent'), int) or not isinstance(view.get('child'), int)
            or view['parent'] <= 0 or view['child'] <= 0 or view['parent'] == view['child']
            or view.get('maps', {}).get('passed') is not True):
        raise RuntimeError('Fresh parent/child process-view refused')
    return report


def strict_smoke(output):
    report = json.loads((output / 'smoke-result.json').read_text())
    if report.get('passed') is not True or report.get('serial') != SERIAL:
        raise RuntimeError('Recovery smoke did not pass for61b')
    checks = report.get('checks', [])
    controls = {row.get('key') for row in checks if row.get('check') == 'controls' and row.get('ok') is True}
    if not checks or any(row.get('ok') is not True for row in checks) or controls != {'helloworld', 'zigzag'}:
        raise RuntimeError('HW/ZZ recovery controls missing or failed')


def recover(binding, workspaces, output, hdc, recorder):
    evidence = collect(recorder, hdc, binding, output)
    verify_bindings(binding, workspaces)
    master = workspaces / 'westlake-harness'
    held(recorder, master, binding)
    current, _ = shell(recorder, hdc, 'cat /proc/sys/kernel/random/boot_id')
    if valid_boot(current) != evidence['boot_id']:
        raise RuntimeError('Boot changed during evidence collection; keep lock')
    recorder.run(recovery_command(binding, workspaces, output, evidence['new_boot']), timeout=900)
    recovery = json.loads((output / 'recovery.json').read_text())
    if recovery.get('status') != ('baseline_restored' if evidence['new_boot'] else 'rolled_back'):
        raise RuntimeError('Executor restoration status refused')
    hook = expand(binding['hook'], workspaces)
    for name in ['restored', 'final']:
        destination = output / name
        recorder.run([sys.executable, hook, '--verify-base', '--serial', SERIAL, '--root', destination], timeout=600)
        checked = identity(destination, binding)
        if checked.get('boot_id') != evidence['boot_id']:
            raise RuntimeError('Boot changed during strict identity verification')
        if name == 'restored':
            smoke = output / 'recovery-smoke'
            recorder.run([sys.executable, master / 'scripts/lab/activation_smoke.py', '--serial', SERIAL,
                '--lane', 'cx-t0', '--spec', expand(binding['smoke_spec'], workspaces), '--out', smoke], timeout=900)
            strict_smoke(smoke)
    held(recorder, master, binding)
    current, _ = shell(recorder, hdc, 'cat /proc/sys/kernel/random/boot_id')
    if valid_boot(current) != evidence['boot_id']:
        raise RuntimeError('Boot changed before unlock')
    recorder.run(['bash', master / 'scripts/lab/board_note.sh', 'unlock',
        master / '.octos/boards/app-lighting.md', SERIAL, 'cx-t0'])
    released = recorder.run(['bash', master / 'scripts/lab/board_note.sh', 'held', SERIAL], required=False)
    if released.returncode != 1 or released.stdout or released.stderr:
        raise RuntimeError('Unlock result is not confirmed empty; report, do not retry')
    return dict(status='restored-verified-unlocked', serial=SERIAL, new_boot=evidence['new_boot'],
        identity_assertions=321, unique_paths=319, fingerprints=binding['fingerprints'], screenshot_verdict='outer review required')


def next_steps(workspaces):
    print('NEXT (not executed): fd-seal + antennapod 第6次补测由外环/cx-t0另开窗；截图签认仍归外环。')
    print('NEXT (only after ALL THREE UNLOCK): WORKSPACES="$HOME/orca/workspaces" bash '
        '"$WORKSPACES/westlake-harness/benchmark/2026-10-03-u15-u16-gate-batch/apply-all.sh" --outer-apply')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--outer-execute', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--hdc', default=os.environ.get('MAC_HDC', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'))
    args = parser.parse_args(argv)
    workspaces = Path(os.environ.get('WORKSPACES', str(HERE.parents[2]))).resolve()
    binding = json.loads((HERE / 'binding.json').read_text())
    if not args.outer_execute:
        print(json.dumps(dict(mode='disabled-preview', board_access=False, writes=0,
            binding=binding, restore_modes=['same boot: --rollback', 'new boot: --restore-baseline'],
            same_boot_command=list(map(str, recovery_command(binding, workspaces, Path('$ATTEMPT'), False))),
            new_boot_command=list(map(str, recovery_command(binding, workspaces, Path('$ATTEMPT'), True)))), indent=2))
        return 0
    os.environ['WORKSPACES'] = str(workspaces)
    os.environ['MAC_HOME'] = os.environ.get('MAC_HOME', str(Path.home()))
    if not os.environ.get('LAB_HOME'):
        parser.error('LAB_HOME is required by the original executor wrapper')
    output = args.out or HERE / '.artifacts' / ('return-' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(output)
    try:
        save(output / 'execution-inputs.json', dict(binding_sha256=sha(HERE / 'binding.json'),
            script_sha256=sha(HERE / 'return_61b.py'), pinned_files=binding['pinned_files']))
        verify_bindings(binding, workspaces)
        report = recover(binding, workspaces, output, args.hdc, recorder)
        save(output / 'result.json', report)
        print(json.dumps(report, indent=2))
        next_steps(workspaces)
        return 0
    except Exception as error:
        unlock_attempted = any('unlock' in row['command'] for row in recorder.records)
        save(output / 'result.json', dict(status='stopped-requires-outer-review', error=str(error),
            unlock_attempted=unlock_attempted, lock_state='unknown after unlock attempt' if unlock_attempted else 'not released by this script', serial=SERIAL))
        print('STOP: no further writes; ' + ('unlock attempted, inspect holder' if unlock_attempted else 'keep existing lock')
            + '; evidence=' + str(output), file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
