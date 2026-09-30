#!/usr/bin/env python3
"""Replay only the reviewed U3 JAR layers; native state is a readonly prerequisite."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
import uuid

import lab_paths
import check_frozen
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b

TARGET = '/system/android/framework/oh-adapter-runtime.jar'
N2_SHA = '51a78bde7075305758bd40b0af3169753dc4be343509e8a8e3d8909fb5d9df09'
LAYERS = [
    ('j2-0715c964', '0715c9645652742dbdececd35ad73fab70552c2245bf21be56c04fdc6d04488d'),
    ('j3-75c2068c', '75c2068ca9818ea8a61cd2d7e258ef70b36fb426c87036f2f8e2c472d47e6697'),
]
FZ1 = {
    '/system/lib64/libbms.z.so': '6aadb8b4ca9ad7d1dbaf6d99ca70f4603e3e7a2ec152fb60aee49137751afbf9',
    '/system/lib64/libapk_installer.so': '7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18',
}


class ReplayError(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise ReplayError(reason)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(workspaces, registry):
    package = workspaces / 'westlake-generation-n2-51a78bde/package.json'
    require(package.is_file(), f'missing N2 manifest: {package}')
    require(digest(package) == N2_SHA, f'N2 manifest SHA differs: {package}')
    pkg = json.loads(package.read_text())
    expected = dict(pkg['live_hashes'])
    base = expected.pop(TARGET)
    expected.update(pkg.get('prerequisites', {}))
    require(registry.is_file(), f'missing frozen registry: {registry}')
    entries = check_frozen.load(registry)
    problems = check_frozen.validate(entries)
    require(not problems, 'invalid frozen registry: ' + '; '.join(problems))
    fz1 = next((e for e in entries if e['id'] == 'FZ-001'), {})
    require(fz1.get('status', 'frozen') == 'frozen' and
            {r['path']: r['sha256'] for r in fz1.get('artifacts', [])} == FZ1,
            'FZ-001 identity changed or missing; this U3 profile requires a new reviewed recipe')
    expected.update(FZ1)
    files = []
    for name, sha in LAYERS:
        path = workspaces / 'vm-copies' / name / 'oh-adapter-runtime.jar'
        require(path.is_file(), f'missing {name} input: {path}')
        require(digest(path) == sha, f'{name} SHA differs: {path}')
        files.append(path)
    planned = dict(expected, **{TARGET: LAYERS[-1][1]})
    lines, bad = check_frozen.check_artifacts(check_frozen.active(entries), planned, 'U3 replay')
    require(not bad, 'frozen artifact conflict: ' + '; '.join(lines))
    return dict(expected=expected, base=base, files=files, package_sha256=N2_SHA,
                registry_sha256=digest(registry), frozen_checks=lines)


class Transport(b.Board):
    """Reuse proven HDC remote-status, lock and boot checks; take current whitelist."""
    def __init__(self, serial, hdc, lock, lane, out):
        require(serial in lab_paths.boards('oh'), 'serial is not a whitelisted OH board')
        self.serial, self.lane = serial, lane
        self.hdc, self.lock = shlex.split(hdc), shlex.split(lock)
        require(self.hdc and self.lock and lane, 'hdc, lock command and lane required')
        self.out, self.boot, self.index = Path(out), None, 0


def shell(board, cmd):
    return board.shell(cmd)[1]


def read_hashes(board, paths):
    text = shell(board, 'sha256sum ' + ' '.join(shlex.quote(p) for p in paths))
    found = {}
    for line in text.splitlines():
        parts = line.split()
        require(len(parts) == 2 and re.fullmatch(r'[0-9a-f]{64}', parts[0]),
                'unparseable sha256sum output: ' + line)
        require(parts[1] not in found, 'duplicate SHA path: ' + parts[1])
        found[parts[1]] = parts[0]
    require(set(found) == set(paths), 'missing or extra SHA paths: ' + str(set(paths) ^ set(found)))
    return found


def daemon(board):
    ps = shell(board, 'ps -A -o PID,PPID,UID,NAME')
    candidates = [p[0] for line in ps.splitlines() if len(p := line.split()) == 4
                  and p[0].isdigit() and p[1] == '1' and p[2] in ('0', 'root') and p[3] == 'appspawn-x']
    require(len(candidates) == 1, 'need exactly one root appspawn-x daemon with PPID 1; found ' + str(candidates))
    pid = candidates[0]
    exe = shell(board, f'readlink /proc/{pid}/exe').strip()
    require(exe.endswith('/appspawn-x'), 'unexpected appspawn-x executable: ' + exe)
    stat = shell(board, f'cat /proc/{pid}/stat').strip()
    fields = stat[stat.rfind(')') + 2:].split()
    require(len(fields) > 19 and fields[19].isdigit(), 'cannot read appspawn-x starttime')
    return pid, fields[19]


def guard(board, identity):
    require(daemon(board) == identity, 'appspawn-x PID/starttime changed; stop and recheck native state')


def native_check(board, recipe, pid):
    paths = list(recipe['expected'])
    for prefix in ['', f'/proc/{pid}/root']:
        found = read_hashes(board, [prefix + p for p in paths])
        bad = [p for p in paths if found[prefix + p] != recipe['expected'][p]]
        require(not bad, 'native/installer/prerequisite SHA mismatch in ' + (prefix or 'shell') + ': ' + ', '.join(bad))


def mount_roots(text):
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 7 and fields[4] == TARGET:
            require(fields[0].isdigit() and fields[1].isdigit(), 'invalid JAR mountinfo')
            rows.append((int(fields[0]), int(fields[1]), fields[3]))
    rows.sort()
    for prev, nxt in zip(rows, rows[1:]):
        require(nxt[1] == prev[0], 'JAR mount stack is not a parent chain')
    return [r[2] for r in rows]


def state(board, recipe, pid):
    left = mount_roots(shell(board, 'cat /proc/self/mountinfo'))
    right = mount_roots(shell(board, f'cat /proc/{pid}/mountinfo'))
    require(left == right, 'shell/appspawn-x JAR mount stacks differ')
    require(len(left) <= 2, 'unknown extra JAR overlays; leave them untouched')
    for i, root in enumerate(left):
        pat = r'/local/tmp/(?:replay-unified/[0-9a-f]{32}/)?' + re.escape(LAYERS[i][0]) + r'/oh-adapter-runtime\.jar'
        require(re.fullmatch(pat, root), 'unrecognized JAR overlay: ' + root)
        source = '/data' + root
        require(read_hashes(board, [source])[source] == LAYERS[i][1], 'existing overlay source changed: ' + source)
    wanted = LAYERS[len(left)-1][1] if left else recipe['base']
    paths = [TARGET, f'/proc/{pid}/root{TARGET}']
    require(all(x == wanted for x in read_hashes(board, paths).values()), 'JAR SHA or shell/appspawn-x root mismatch')
    return left


def replay(board, recipe, receipt):
    identity = daemon(board)
    pid = identity[0]
    native_check(board, recipe, pid)
    initial = state(board, recipe, pid)
    guard(board, identity)
    receipt.update(boot_id=board.boot, daemon_pid=pid, daemon_starttime=identity[1],
                   native_paths_per_root=len(recipe['expected']), initial_mounts=initial)
    if len(initial) == 2:
        receipt.update(status='already_unified', final_mounts=initial, jar_sha256=LAYERS[-1][1])
        return
    staging = '/data/local/tmp/replay-unified/' + uuid.uuid4().hex
    proposed = []
    try:
        # All needed inputs staged and read back before the first bind.
        for i in range(len(initial), 2):
            guard(board, identity)
            remote = staging + '/' + LAYERS[i][0] + '/oh-adapter-runtime.jar'
            shell(board, 'mkdir -p ' + shlex.quote(str(Path(remote).parent)))
            board.send(recipe['files'][i], remote)
            shell(board, 'chmod 644 ' + shlex.quote(remote))
            require(read_hashes(board, [remote])[remote] == LAYERS[i][1], 'staged JAR SHA mismatch: ' + remote)
            proposed.append(remote)
        for i, remote in enumerate(proposed):
            guard(board, identity)
            require(state(board, recipe, pid) == initial + [s.removeprefix('/data') for s in proposed[:i]],
                    'JAR stack changed before bind')
            shell(board, 'mount --bind ' + shlex.quote(remote) + ' ' + shlex.quote(TARGET))
            state(board, recipe, pid)  # Must propagate to daemon root too.
        guard(board, identity)
        native_check(board, recipe, pid)
        final = state(board, recipe, pid)
        require(len(final) == 2, 'missing J2/J3 layer after replay')
        receipt.update(status='replayed', final_mounts=final, jar_sha256=LAYERS[-1][1])
    except (Exception, KeyboardInterrupt):
        try:
            guard(board, identity)
            current = mount_roots(shell(board, 'cat /proc/self/mountinfo'))
            ours = [p.removeprefix('/data') for p in proposed]
            require(current[:len(initial)] == initial and current[len(initial):] == ours[:len(current)-len(initial)],
                    'foreign stack change; cannot unwind')
            for _ in range(len(current) - len(initial)):
                guard(board, identity)
                shell(board, 'umount ' + shlex.quote(TARGET))
            require(state(board, recipe, pid) == initial, 'rollback roots did not return to initial state')
            receipt['rollback'] = 'verified_original_mounts_and_jar_in_both_roots'
        except Exception as rollback:
            receipt['rollback'] = 'unverified: ' + str(rollback)
        raise
    finally:
        # Do not delete possibly-mounted sources after a transport failure.
        receipt['staging'] = staging


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('serial', nargs='?')
    p.add_argument('--check-inputs', action='store_true', help='local only; never constructs a device transport')
    p.add_argument('--out', type=Path)
    p.add_argument('--lane', default=os.environ.get('REPLAY_LANE', 'cx-bms'))
    p.add_argument('--hdc', default=os.environ.get('HDC', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'))
    a = p.parse_args(argv)
    result = dict(status='failed', serial=a.serial, device_validation='unverified', screenshots=None, alive=None)
    rc = 1
    try:
        if a.out:
            require(not (a.out / 'receipt.json').exists(), 'output already has a receipt; use a fresh directory')
        w = lab_paths.workspaces()
        recipe = inputs(w, lab_paths.harness() / 'knowledge/frozen/frozen.json')
        result.update(package_sha256=recipe['package_sha256'], registry_sha256=recipe['registry_sha256'], frozen_checks=recipe['frozen_checks'])
        if a.check_inputs:
            result.update(status='inputs_verified', native_paths_per_root=len(recipe['expected']))
        else:
            require(a.serial in lab_paths.boards('oh'), 'serial is not a whitelisted OH board')
            if a.out is None:
                a.out = Path(tempfile.mkdtemp(prefix='westlake-replay-'))
            a.out.mkdir(parents=True, exist_ok=True)
            board = Transport(a.serial, a.hdc, 'bash ' + shlex.quote(str(lab_paths.tools() / 'board_note.sh')), a.lane, a.out / 'commands')
            replay(board, recipe, result)
            result['device_validation'] = 'file_hashes_and_mounts_only; new child/UI not tested'
        rc = 0
    except (Exception, KeyboardInterrupt) as exc:
        result.update(status='failed', reason=str(exc) or type(exc).__name__)
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        # Refuse to overwrite a previous receipt even when argument checks failed.
        if not (a.out / 'receipt.json').exists():
            (a.out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
        result['evidence_directory'] = str(a.out)
    print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    return rc


if __name__ == '__main__':
    sys.exit(main())
