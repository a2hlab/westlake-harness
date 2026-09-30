#!/usr/bin/env python3
"""Future authorized VM window only. Temporary JAR overlay; always restore owned layer.

Without --execute this checks local artifacts only. Native/boot/installer unchanged.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths

TARGET = '/system/android/framework/oh-adapter-runtime.jar'


def overlay(board, jar, digest, base, daemon, receipt, run_batch):
    """This transaction never removes pre-existing layers. Tested with a FakeBoard."""
    def check_hash(path, expected):
        value = board.shell('sha256sum ' + shlex.quote(path))[1].split()[0]
        if value != expected:
            raise RuntimeError('SHA mismatch: ' + path)

    def mounts():
        text = board.shell('cat /proc/self/mountinfo')[1]
        return [line for line in text.splitlines() if line.split()[4] == TARGET]

    root_path = f'/proc/{daemon}/root{TARGET}'
    board.ready()
    check_hash(TARGET, base); check_hash(root_path, base)
    before = mounts()
    remote = '/data/local/tmp/u4-probe-' + uuid.uuid4().hex + '/runtime.jar'
    receipt.update(boot_id=board.boot, before_mounts=before, remote=remote, rollback='not_needed')
    board.shell('mkdir -p ' + shlex.quote(str(Path(remote).parent)))
    board.send(jar, remote)
    check_hash(remote, digest)
    attempted = False
    owned = None
    try:
        attempted = True
        board.shell('mount --bind ' + shlex.quote(remote) + ' ' + TARGET)
        added = [line for line in mounts() if line not in before]
        if len(added) != 1:
            raise RuntimeError('cannot identify exactly one new mount')
        owned = added[0]
        receipt['owned_mount'] = owned
        check_hash(TARGET, digest); check_hash(root_path, digest)
        run_batch()
    finally:
        if attempted:
            receipt['rollback'] = 'unverified'
            current = mounts()  # Board.ready refuses a boot/lock/connection change.
            if owned is None:
                # Only accept the single uniquely staged mount after an ambiguous transport result.
                added = [line for line in current if line not in before]
                roots = [line for line in added if line.split()[3] == remote.removeprefix('/data')]
                if len(added) == 1 and len(roots) == 1:
                    owned = roots[0]
            if owned is None:
                if current == before:
                    check_hash(TARGET, base); check_hash(root_path, base)
                    receipt['rollback'] = 'verified_no_mount'
                else:
                    raise RuntimeError('unknown mount; no unmount attempted')
            else:
                if not current or current[-1] != owned:
                    raise RuntimeError('top mount changed; no unmount attempted')
                board.shell('umount ' + TARGET)
                if mounts() != before:
                    raise RuntimeError('prior mount stack not restored')
                check_hash(TARGET, base); check_hash(root_path, base)
                receipt['rollback'] = 'verified'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--variant', choices=['A-observe', 'B-app-theme'], required=True)
    ap.add_argument('--serial', required=True)
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    if args.serial not in lab_paths.boards('oh'):
        ap.error('not a registered OH serial')
    receipt = json.loads((HERE / 'build-receipt.json').read_text())
    artifact = receipt['variants'][args.variant]
    # Artifacts stay outside git; relocatable path, not the recorded author's absolute build path.
    jar = ROOT / 'bms/src/.work/u4-probes' / args.variant / 'oh-adapter-runtime.jar'
    if hashlib.sha256(jar.read_bytes()).hexdigest() != artifact['sha256']:
        raise RuntimeError('local diagnostic JAR differs from build receipt')
    if not args.execute:
        print(json.dumps({'device_io': False, 'local_jar_verified': True, 'sha256': artifact['sha256']}))
        return
    if not __import__('shutil').which('mac'):
        ap.error('--execute must run inside a2hlab after outer schedules a board window')
    master = lab_paths.harness()
    sys.path.insert(0, str(master / 'benchmark/2026-09-28-bms-route-deploy/batch'))
    import bms_batch as b
    out = HERE.parent / 'runs' / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    board = b.Board(args.serial, str(lab_paths.tools() / 'hdc_mac.sh'),
                    'mac ' + shlex.quote(str(lab_paths.tools() / 'board_note.sh')), 'cx-t0', out / 'overlay-commands')
    board.ready()
    pids = board.shell('pidof appspawn-x')[1].split()
    if len(pids) != 1 or not pids[0].isdigit():
        raise RuntimeError('exactly one appspawn-x daemon required')
    keys = 'vlc,termux' if args.variant == 'A-observe' else 'vlc'
    record = {'variant': args.variant, 'serial': args.serial, 'candidate_sha256': artifact['sha256']}
    def batch():
        subprocess.run([sys.executable, str(master / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),
                        '--manifest', str(HERE.parent / 'cohort.json'), '--execute', '--serial', args.serial,
                        '--lane', 'cx-t0', '--hdc-cmd', str(lab_paths.tools() / 'hdc_mac.sh'),
                        '--lock-cmd', 'mac ' + shlex.quote(str(lab_paths.tools() / 'board_note.sh')),
                        '--keys', keys, '--reinstall', '--hilog', '20', '--shots', '5,20', '--focus-check',
                        '--out', str(out), '--run-id', 'apps-' + args.serial], check=True, timeout=420)
    try:
        overlay(board, jar, artifact['sha256'], receipt['base_sha256'], pids[0], record, batch)
    finally:
        (out / 'overlay-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
