#!/usr/bin/env python3
"""Read-only exact-realization comparison; recorded observations never yield PASS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
import observations
import realization
import seal_checks

PATH = re.compile(r'/[A-Za-z0-9_./:+@-]+\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
BOOT = observations.BOOT


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_fresh(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def safe_target(path):
    need(isinstance(path, str) and PATH.fullmatch(path) and '..' not in path.split('/'),
         'unsafe realization target')
    return path


class ReadOnlyCollector:
    """Only explicit local HDC and compiler-selected read commands are used."""
    def __init__(self, hdc, serial, directory):
        tool = Path(hdc).expanduser().resolve()
        need(tool.is_file() and os.access(tool, os.X_OK), 'explicit local HDC is not executable')
        self.hdc, self.serial, self.directory = str(tool), serial, Path(directory)
        self.directory.mkdir(exist_ok=False)
        self.commands = []

    def read(self, kind, command):
        number = len(self.commands)
        prefix = self.directory / ('%03d-%s' % (number, kind))
        marker = '__EXACT_READ_RC_' + uuid.uuid4().hex + '__'
        wrapped = ('/system/bin/sh -c ' + shlex.quote(command) +
                   '; exact_rc=$?; printf "\\n' + marker + '%s\\n" "$exact_rc"')
        argv = [self.hdc, '-t', self.serial, 'shell', wrapped]
        row = {'kind': kind, 'command': command, 'argv': argv}
        try:
            result = subprocess.run(argv, capture_output=True, timeout=45)
            stdout, stderr, transport_rc = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, transport_rc = exc.stdout or b'', exc.stderr or b'', None
            row['error'] = 'transport timeout'
        except OSError as exc:
            stdout, stderr, transport_rc = b'', str(exc).encode(), None
            row['error'] = 'transport failed'
        match = re.search(b'\n' + marker.encode() + rb'([0-9]+)\r?\n?\Z', stdout)
        remote_rc = int(match[1]) if match else None
        raw = stdout[:match.start()] if match else stdout
        transport_path = prefix.with_suffix('.transport.stdout')
        stderr_path = prefix.with_suffix('.stderr')
        raw_path = prefix.with_suffix('.stdout')
        for path, data in ((transport_path, stdout), (stderr_path, stderr), (raw_path, raw)):
            with path.open('xb') as stream:
                stream.write(data)
        row.update(transport_rc=transport_rc, remote_rc=remote_rc,
                   stdout={'path': raw_path.name, 'sha256': digest(raw_path)},
                   transport_stdout={'path': transport_path.name, 'sha256': digest(transport_path)},
                   stderr={'path': stderr_path.name, 'sha256': digest(stderr_path)})
        dump_fresh(prefix.with_suffix('.json'), row)
        self.commands.append(row)
        need(transport_rc == 0 and remote_rc == 0, 'read transport/remote status failed: ' + kind)
        reading = {key: row[key] for key in ('command', 'transport_rc', 'remote_rc', 'stdout')}
        return raw, reading


def collect_live(proof, serial, current_boot, hdc, directory):
    collector = ReadOnlyCollector(hdc, serial, directory)
    readings = {}
    def read(kind, command):
        raw, readings[kind] = collector.read(kind, command)
        return raw
    common = observations.commands('placement')
    before = read('boot_before', common['boot_before']).decode().strip()
    need(before == current_boot, 'live boot differs from independent --boot-id')
    owner = read('host_owner', common['host_owner']).decode().strip()
    need(re.fullmatch(r'[0-9]+:[0-9]+', owner), 'live owner parse failed')
    uid, gid = (int(value) for value in owner.split(':'))
    read('host_hap', common['host_hap'])
    window = observations.parse_window(read('window_dump', observations.WINDOW_COMMAND))
    pid = window['host_pid']
    commands = observations.commands('running', pid)
    read('host_status', commands['host_status'])
    birth = observations.parse_birth(read('host_stat', commands['host_stat']), pid)
    read('host_cmdline', commands['host_cmdline'])  # Preserve NUL bytes verbatim.
    targets = [safe_target(row['target']) for row in proof['files']]
    need(len(targets) == len(set(targets)) and targets, 'empty/duplicate realization files')
    files = {}
    for start in range(0, len(targets), 24):
        batch = targets[start:start + 24]
        raw, _ = collector.read('files-%04d' % start, 'sha256sum ' + ' '.join(shlex.quote(p) for p in batch))
        found = {}
        for line in raw.decode().splitlines():
            match = re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)', line)
            need(match is not None and match[2] not in found, 'malformed/duplicate SHA readback')
            found[match[2]] = match[1]
        need(set(found) == set(batch), 'SHA readback target set differs')
        files.update(found)
    seal_observation = seal_checks.collect(seal_checks.requirements(proof), collector)
    for target, sha in seal_observation.get('files', {}).items():
        need(target not in files or files[target] == sha, 'APK changed during readback')
        files[target] = sha
    after = read('boot_after', commands['boot_after']).decode().strip()
    parameter = {'schema': observations.SCHEMA, 'serial': serial,
                 'boot_before': before, 'boot_after': after, 'host_uid': uid, 'host_gid': gid,
                 'host_pid': pid, 'host_birth': birth, 'window_id': window['window_id'],
                 'readings': readings, 'synthetic': False}
    parameter_path = collector.directory / 'parameter-observation.json'
    dump_fresh(parameter_path, parameter)
    observation = {'schema': 'exact-live-observation/v1', 'serial': serial,
                   'boot_before': before, 'boot_after': after, 'files': files,
                   'parameter_evidence': {'path': parameter_path.name, 'sha256': digest(parameter_path)},
                   'errors': [], 'synthetic': False, 'commands': collector.commands}
    observation.update({k: v for k, v in seal_observation.items() if k != 'files'})
    observation_path = collector.directory / 'observation.json'
    dump_fresh(observation_path, observation)
    return observation_path


def compare(proof, observation, base, serial, current_boot, offline):
    need(isinstance(observation, dict) and observation.get('schema') == 'exact-live-observation/v1',
         'wrong exact observation schema')
    need(type(observation.get('synthetic', False)) is bool, 'synthetic flag must be boolean')
    need(offline or observation.get('synthetic', False) is False, 'synthetic observation cannot yield live PASS')
    need(observation.get('serial') == serial, 'observation serial differs')
    need(observation.get('boot_before') == observation.get('boot_after') == current_boot,
         'observation boot stale or unstable against independent --boot-id')
    need(observation.get('errors') == [], 'observation read errors missing/nonempty')
    expected, dynamic = realization.running_files(proof, observation.get('parameter_evidence'), base, current_boot)
    need(isinstance(expected, dict) and expected, 'running realization files empty')
    requirements = seal_checks.requirements(proof)
    seal_checks.compare(requirements, observation)
    for package in requirements.get('packages', []):
        path, sha = package['apk_path'], package['apk_sha256']
        need(path not in expected or expected[path] == sha, 'package/file SHA conflict')
        expected[path] = sha
    actual = observation.get('files')
    need(isinstance(actual, dict), 'observation files missing')
    need(all(isinstance(value, str) and SHA.fullmatch(value) for value in actual.values()),
         'observation file SHA malformed')
    checks = [{'target': target, 'expected': expected.get(target), 'actual': actual.get(target),
               'equal': target in expected and target in actual and expected[target] == actual[target]}
              for target in sorted(set(expected) | set(actual))]
    matched = all(row['equal'] for row in checks)
    return {'schema': 'exact-realization-selfcheck/v1',
            'mode': 'offline-comparison' if offline else 'live-readonly',
            'status': ('OFFLINE_MATCH' if offline else 'PASS') if matched else 'FAIL',
            'passed': matched, 'serial': serial, 'current_boot': current_boot,
            'boot_before': observation['boot_before'], 'boot_after': observation['boot_after'],
            'source_coverage': 'seal-files-and-original-nonfile-checks' if requirements else 'candidate-file-fingerprint-only',
            'file_count': len(expected), 'checks': checks, 'dynamic_receipt': dynamic,
            'synthetic': observation.get('synthetic', False),
            'remote_write_operations': 0, 'lock_operations': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--realization', required=True, type=Path)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--boot-id', required=True)
    parser.add_argument('--observed', type=Path, help='offline recorded comparison, never live PASS')
    parser.add_argument('--hdc', help='explicit local HDC executable; required only for live readback')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    can_write = False
    try:
        need(not args.out.exists() and not args.out.is_symlink(), 'fresh receipt path required')
        need(args.out.parent.is_dir(), 'receipt parent directory must already exist')
        can_write = True
        need(BOOT.fullmatch(args.boot_id), 'independent --boot-id must be a UUID')
        proof = realization.verify(args.realization)
        need(proof['parameters']['serial'] == args.serial, 'requested serial differs from realization')
        need(args.observed is not None or args.hdc, 'live mode requires explicit --hdc')
        observation_path = (args.observed.resolve() if args.observed else
                            collect_live(proof, args.serial, args.boot_id, args.hdc,
                                         args.out.parent / (args.out.name + '.evidence')))
        observation = observations.read_json(observation_path)
        result = compare(proof, observation, observation_path.parent, args.serial, args.boot_id,
                         args.observed is not None)
        result['realization'] = {'path': str(args.realization.resolve()), 'sha256': digest(args.realization)}
        result['observation'] = {'path': str(observation_path.resolve()), 'sha256': digest(observation_path)}
        dump_fresh(args.out, result)
        print(result['status'])
        return 0 if result['passed'] else 1
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        result = {'schema': 'exact-realization-selfcheck/v1', 'status': 'REJECT', 'passed': False,
                  'mode': 'offline-comparison' if args.observed else 'live-readonly',
                  'reason': str(exc), 'remote_write_operations': 0, 'lock_operations': 0}
        if can_write and not args.out.exists() and not args.out.is_symlink():
            dump_fresh(args.out, result)
        print('REJECT ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
