#!/usr/bin/env python3
"""Reusable bind-overlay sweep: deploy a generation as bind-mounts, verify every file against an
expected-run.json through the appspawn-x child view, run a bms_batch shard, then roll back and
reverify the runtime/boot fingerprints. Generalised from the U6 three-board sweep (cc-t3) so U7 (and
any later bind-composed candidate) can run it directly.

A "bind overlay" is a reversible deploy: `mount --bind <local> <dest>` over each resident file
(libart untouched), one `begetctl` restart of appspawn-x, and `umount` to roll back exact-byte. This
tool does NOT persist to /system (that is deploy_generation's job with a real generation package); it
is the on-board sweep harness only.

Phases (normal run): lock -> preflight -> backup baseline shas -> stage -> bind -> restart appspawn-x
-> verify EVERY expected-run.json file via /proc/<appspawn-root>/root<path> -> bms_batch shard ->
rollback (umount + verify RUNTIME/BOOT fingerprints back to the U-baseline) -> unlock.

  --self-test   off-board unit tests of the pure logic (no board, no hdc). Exit 0/1.
  --dry-run     validate args + print the full plan; touch NO board.
  --no-run      deploy + verify, skip the bms_batch sweep (e.g. a single-key smoke).
  --no-rollback leave the overlay in place (caller rolls back later).
  --rollback-only  only roll back an overlay left by --no-rollback (same --bind set and --out, whose
                deploy-receipt.json holds the baseline shas): umount + restart + verify fingerprints. Used as
                board_run's before_unlock (deploy = after_lock: --no-run --no-rollback, no --note-cmd).

Binds: --bind LOCAL:DEST (repeatable) for individual files (jars); --images-dir DIR expands every
*.art/*.oat/*.vdex in DIR over <arm64-dest>/<basename>. Both feed one bind set.

Transport: --hdc is the board hdc for overlay/verify/rollback (default the Mac DevEco hdc). The
bms_batch sweep is invoked with --bms-hdc-cmd (its own --hdc-cmd, which may be a VM forwarder), and
--manifest/--input-root/--keys/--lane/--out.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

DEVECO_HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
FW = '/system/android/framework'
ARM64 = FW + '/arm64'
SOCK = '/dev/unix/socket/AppSpawnX'
# the two fingerprint path-sets bms_batch uses (keep in sync with bms_batch.py FINGERPRINT_PATHS /
# BOOT_IMAGE_PATHS); RUNTIME excludes BCP jars + boot image on purpose (a jar-only fingerprint).
from installation_chain import PATHS as INSTALLATION_PATHS

FINGERPRINT_PATHS = ('/system/bin/appspawn-x /system/android/framework/oh-adapter-runtime.jar '
                     '/system/android/lib64/*.so /system/lib64/westlake/route-a/*/*.so '
                     + ' '.join(INSTALLATION_PATHS))
BOOT_IMAGE_PATHS = ('/system/android/framework/arm64/* ' + ' '.join(
    f'/system/android/framework/{j}.jar' for j in ('core-oj', 'core-libart', 'core-icu4j', 'okhttp',
    'bouncycastle', 'apache-xml', 'adapter-mainline-stubs', 'framework', 'oh-adapter-framework')))


# ----------------------------- pure, unit-testable helpers -----------------------------

def parse_binds(bind_args, images_dir=None, arm64_dest=ARM64):
    """(LOCAL, DEST) pairs from --bind LOCAL:DEST args and an optional --images-dir. Pure."""
    binds = []
    for spec in bind_args or []:
        # split on the LAST colon so a Windows-ish local path still works; DEST is absolute (/...)
        i = spec.rfind(':')
        if i <= 0 or not spec[i + 1:].startswith('/'):
            raise ValueError(f'--bind must be LOCAL:/abs/dest, got {spec!r}')
        binds.append((spec[:i], spec[i + 1:]))
    if images_dir:
        d = Path(images_dir)
        imgs = sorted(p for p in d.iterdir() if p.suffix in ('.art', '.oat', '.vdex'))
        for p in imgs:
            binds.append((str(p), f'{arm64_dest}/{p.name}'))
    return binds


def expected_map(expected_json):
    """{path: sha} across runtime_files + boot_files, and the sorted path list. Pure."""
    d = expected_json
    m = {}
    m.update(d.get('runtime_files', {}))
    m.update(d.get('boot_files', {}))
    return m, sorted(m)


def short_fingerprint(sha_lines):
    """Replicate bms_batch.runtime_fingerprint: sort the `sha256  path` lines, sha256 the join, [:12].
    Pure — takes the raw `sha256sum` stdout text."""
    lines = sorted(l.strip() for l in sha_lines.splitlines() if re.match(r'^[0-9a-f]{64}\s', l.strip()))
    return (hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:12], len(lines)) if lines else (None, 0)


def dest_set(binds):
    """Just the DEST paths (what gets bound / rolled back). Pure."""
    return [d for _, d in binds]


# ----------------------------- board ops (need --hdc) -----------------------------

def sh(hdc, serial, cmd, timeout=180):
    return subprocess.run([hdc, '-t', serial, 'shell', cmd], capture_output=True, text=True,
                          timeout=timeout).stdout.replace('\r', '')


def root_pid(hdc, serial):
    for ln in sh(hdc, serial, 'ps -ef | grep appspawn-x | grep -v grep').splitlines():
        f = ln.split()
        if len(f) >= 2 and f[0] == 'root':
            return f[1]
    return None


def parent_up(hdc, serial):
    return sh(hdc, serial, 'ps -ef | grep appspawn-x | grep -v grep | grep -c root').strip()


def appspawn_stop(hdc, serial):
    sh(hdc, serial, 'ps -ef | grep appspawn-x | grep -v grep | while read u pid rest; do '
                    '[ "$u" != root ] && kill "$pid" 2>/dev/null; done')
    time.sleep(1)
    sh(hdc, serial, 'begetctl stop_service appspawn-x')
    time.sleep(2)


def appspawn_start(hdc, serial):
    sh(hdc, serial, 'begetctl start_service appspawn-x')
    time.sleep(3)
    sh(hdc, serial, f'chown 0:6005 {SOCK} && chmod 0660 {SOCK} && chcon u:object_r:appspawn_socket:s0 {SOCK}')
    time.sleep(1)


def board_shas(hdc, serial, paths, via_pid=None):
    res = {}
    for i in range(0, len(paths), 60):
        chunk = paths[i:i + 60]
        targets = [f'/proc/{via_pid}/root{p}' for p in chunk] if via_pid else chunk
        for ln in sh(hdc, serial, 'sha256sum ' + ' '.join(targets)).splitlines():
            p = ln.split()
            if len(p) == 2:
                res[p[1].replace(f'/proc/{via_pid}/root', '') if via_pid else p[1]] = p[0]
    return res


def fingerprint(hdc, serial, paths):
    return short_fingerprint(sh(hdc, serial, f'sha256sum {paths} 2>/dev/null'))


def board_note(note_cmd, action, board_md, serial, lane, why=None):
    args = note_cmd.split() + [action, board_md, serial, lane]
    if why:
        args.append(why)
    return subprocess.run(args, capture_output=True, text=True)


def stage_file(send, shell, hashes, local, remote, digest, executable=False):
    """Checked staging primitive shared with the compound U7 executor."""
    import shlex
    send(local, remote)
    if hashes([remote]) != {remote: digest}:
        raise RuntimeError('staged SHA mismatch: ' + remote)
    mode = '0755' if executable else '0644'
    shell('chmod ' + mode + ' ' + shlex.quote(remote) +
          ' && chcon u:object_r:system_file:s0 ' + shlex.quote(remote))


def bind_file(shell, remote, target):
    """One bind only. The transaction owner controls stop/start and journaling."""
    import shlex
    return shell('mount --bind ' + shlex.quote(remote) + ' ' + shlex.quote(target))


def unbind_file(shell, target):
    import shlex
    return shell('umount ' + shlex.quote(target))


# ----------------------------- phases -----------------------------

def deploy_and_verify(a, binds, exp_map, exp_paths, out):
    hdc, serial = a.hdc, a.serial
    rec = {'serial': serial, 'binds': len(binds)}
    assert sh(hdc, serial, 'echo alive').strip() == 'alive', 'board not reachable'
    assert parent_up(hdc, serial) == '1', 'appspawn-x root parent != 1 before deploy'
    rec['boot_id'] = sh(hdc, serial, 'cat /proc/sys/kernel/random/boot_id').strip()
    dests = dest_set(binds)
    rec['baseline_shas'] = board_shas(hdc, serial, dests)
    # stage every local file next to a mirror tree under /data/local/tmp/sweep-new
    sh(hdc, serial, 'rm -rf /data/local/tmp/sweep-new && mkdir -p /data/local/tmp/sweep-new')
    staged = {}
    for i, (local, dest) in enumerate(binds):
        remote = f'/data/local/tmp/sweep-new/f{i}'
        subprocess.run([hdc, '-t', serial, 'file', 'send', local, remote], capture_output=True)
        staged[dest] = remote
    # verify staged bytes == expected (only for dests that appear in expected-run.json)
    st = board_shas(hdc, serial, list(staged.values()))
    bad = [d for d, r in staged.items() if d in exp_map and st.get(r) != exp_map[d]]
    assert not bad, 'staged sha != expected for: ' + ', '.join(bad)
    # overlay
    sh(hdc, serial, 'hilog -r')
    appspawn_stop(hdc, serial)
    for dest, remote in staged.items():
        bind_file(lambda cmd: sh(hdc, serial, cmd), remote, dest)
    appspawn_start(hdc, serial)
    up, pid = parent_up(hdc, serial), root_pid(hdc, serial)
    rec['appspawn_up'] = up
    rec['root_pid'] = pid
    assert up == '1' and pid, f'appspawn-x unhealthy after overlay (up={up} pid={pid})'
    # Every bound file is verified in the child view even without --expected: its own local sha256 is the want
    # (2026-10-01 #96: no --expected meant "DEPLOY OK: 0 files match" and nothing was checked).
    for local, dest in binds:
        if dest not in exp_map:
            exp_map[dest] = hashlib.sha256(Path(local).read_bytes()).hexdigest()
            exp_paths.append(dest)
    got = board_shas(hdc, serial, exp_paths, via_pid=pid)
    mism = [{'path': p, 'got': got.get(p), 'want': exp_map[p]} for p in exp_paths if got.get(p) != exp_map[p]]
    rec['verified'] = len(exp_paths)
    rec['mismatches'] = mism
    (Path(out) / 'deploy-receipt.json').write_text(json.dumps(rec, indent=2) + '\n')
    if mism:
        print(f'VERIFY FAIL: {len(mism)}/{len(exp_paths)} mismatch (see deploy-receipt.json)')
        for m in mism[:8]:
            print(f"  {m['path']}\n    got ={m['got']}\n    want={m['want']}")
        return False
    print(f'DEPLOY OK: {len(exp_paths)} files match expected-run.json via /proc/{pid}/root; appspawn-x up=1')
    return True


def run_sweep(a, out):
    # an empty --lock-cmd overrode bms_batch's own default and stopped every batch at once ("hdc, lock command and
    # lane required", U7 05:36); pass it only when set
    lock = ['--lock-cmd', a.lock_cmd] if a.lock_cmd else []
    cmd = [sys.executable, a.bms_batch, '--execute', '--serial', a.serial, '--lane', a.lane,
           '--hdc-cmd', a.bms_hdc_cmd, *lock, '--manifest', a.manifest,
           '--input-root', a.input_root, '--keys', a.keys, '--out', out, '--reinstall',
           '--hilog', '20', '--shots', '5,20', '--focus-check']
    print('SWEEP:', ' '.join(cmd))
    return subprocess.call(cmd)


def rollback(a, binds, out):
    hdc, serial = a.hdc, a.serial
    dests = dest_set(binds)
    rec_path = Path(out) / 'deploy-receipt.json'
    baseline = json.loads(rec_path.read_text()).get('baseline_shas', {}) if rec_path.exists() else {}
    appspawn_stop(hdc, serial)
    for d in dests:
        sh(hdc, serial, f'umount {d} 2>/dev/null')
    appspawn_start(hdc, serial)
    after = board_shas(hdc, serial, dests)
    bad = [d for d in dests if baseline and after.get(d) != baseline.get(d)]
    rt = fingerprint(hdc, serial, FINGERPRINT_PATHS)
    bi = fingerprint(hdc, serial, BOOT_IMAGE_PATHS)
    ok = not bad
    msg = {'restored_byte_identical': ok, 'still_wrong': bad,
           'RUNTIME': rt[0], 'BOOT': bi[0], 'residual': sh(hdc, serial, "grep -c sweep-new /proc/self/mountinfo").strip()}
    if a.rollback_runtime_fp:
        msg['RUNTIME_match'] = (rt[0] == a.rollback_runtime_fp)
        ok = ok and rt[0] == a.rollback_runtime_fp
    if a.rollback_boot_fp:
        msg['BOOT_match'] = (bi[0] == a.rollback_boot_fp)
        ok = ok and bi[0] == a.rollback_boot_fp
    (Path(out) / 'rollback-receipt.json').write_text(json.dumps(msg, indent=2) + '\n')
    print(f"ROLLBACK {'OK' if ok else 'INCOMPLETE'}: RUNTIME={rt[0]} BOOT={bi[0]} "
          f"byte_identical={not bad} residual_mounts={msg['residual']}")
    return ok


def plan(a, binds, exp_paths):
    print('=== sweep_bind_deploy DRY-RUN plan (no board touched) ===')
    print(f'serial={a.serial} lane={a.lane} hdc={a.hdc}')
    print(f'binds ({len(binds)}):')
    for local, dest in binds[:6]:
        print(f'  {local} -> {dest}')
    if len(binds) > 6:
        print(f'  ... +{len(binds) - 6} more')
    print(f'expected-run verify: {len(exp_paths)} files via /proc/<appspawn-root>/root (child view)')
    print(f'rollback fingerprints: RUNTIME={a.rollback_runtime_fp or "(byte-identity only)"} '
          f'BOOT={a.rollback_boot_fp or "(byte-identity only)"}')
    print(f'sweep: {"SKIPPED (--no-run)" if a.no_run else a.keys}')
    print(f'rollback: {"SKIPPED (--no-rollback)" if a.no_rollback else "umount all + verify"}')
    print('flow: lock -> preflight -> backup -> stage -> bind -> restart -> verify -> '
          f'{"" if a.no_run else "sweep -> "}{"" if a.no_rollback else "rollback -> "}unlock')


# ----------------------------- self-test (off board) -----------------------------

def self_test():
    import unittest

    class T(unittest.TestCase):
        def test_parse_binds_files(self):
            b = parse_binds(['/a/x.jar:/system/android/framework/x.jar',
                             '/p/y.jar:/system/android/framework/y.jar'])
            self.assertEqual(b, [('/a/x.jar', '/system/android/framework/x.jar'),
                                 ('/p/y.jar', '/system/android/framework/y.jar')])

        def test_parse_binds_rejects_relative_dest(self):
            with self.assertRaises(ValueError):
                parse_binds(['/a/x.jar:framework/x.jar'])

        def test_parse_binds_images_dir(self, ):
            import tempfile, os
            d = tempfile.mkdtemp()
            for n in ('boot.art', 'boot.oat', 'boot.vdex', 'note.txt'):
                open(os.path.join(d, n), 'w').close()
            b = parse_binds([], images_dir=d, arm64_dest='/A')
            got = sorted(dest for _, dest in b)
            self.assertEqual(got, ['/A/boot.art', '/A/boot.oat', '/A/boot.vdex'])  # .txt excluded

        def test_expected_map_merges(self):
            m, paths = expected_map({'runtime_files': {'/r': 'aa'}, 'boot_files': {'/b': 'bb'}})
            self.assertEqual(m, {'/r': 'aa', '/b': 'bb'})
            self.assertEqual(paths, ['/b', '/r'])

        def test_short_fingerprint_deterministic_and_order_independent(self):
            a = 'a' * 64 + '  /x\n' + 'b' * 64 + '  /y\n'
            b = 'b' * 64 + '  /y\n' + 'a' * 64 + '  /x\n'  # different order
            self.assertEqual(short_fingerprint(a), short_fingerprint(b))
            self.assertEqual(short_fingerprint(a)[1], 2)

        def test_short_fingerprint_ignores_error_lines(self):
            txt = 'sha256sum: /gone: No such file or directory\n' + 'c' * 64 + '  /z\n'
            self.assertEqual(short_fingerprint(txt)[1], 1)

        def test_short_fingerprint_empty(self):
            self.assertEqual(short_fingerprint('no valid lines'), (None, 0))

        def test_dest_set(self):
            self.assertEqual(dest_set([('/a', '/d1'), ('/b', '/d2')]), ['/d1', '/d2'])

    r = unittest.TextTestRunner(verbosity=2).run(unittest.TestLoader().loadTestsFromTestCase(T))
    return 0 if r.wasSuccessful() else 1


# ----------------------------- main -----------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--serial')
    ap.add_argument('--lane', default='cc-t3')
    ap.add_argument('--bind', action='append', default=[], help='LOCAL:/abs/dest (repeatable)')
    ap.add_argument('--images-dir', help='dir of *.art/*.oat/*.vdex -> bound over <arm64>/<name>')
    ap.add_argument('--arm64-dest', default=ARM64)
    ap.add_argument('--expected', help='expected-run.json (post-deploy per-file verify)')
    ap.add_argument('--manifest', help='bms_batch apps.json')
    ap.add_argument('--keys', help='comma-separated shard keys (or a file to read)')
    ap.add_argument('--input-root')
    ap.add_argument('--bms-batch', help='path to bms_batch.py (master copy)')
    ap.add_argument('--bms-hdc-cmd', default=DEVECO_HDC, help="bms_batch's --hdc-cmd (VM forwarder or hdc)")
    ap.add_argument('--lock-cmd', default='')
    ap.add_argument('--hdc', default=DEVECO_HDC, help='board hdc for overlay/verify/rollback')
    ap.add_argument('--board-md')
    ap.add_argument('--note-cmd', help='board_note.sh path (lock/unlock); omit to skip locking')
    ap.add_argument('--rollback-runtime-fp')
    ap.add_argument('--rollback-boot-fp')
    ap.add_argument('--out', default='.')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--no-run', action='store_true')
    ap.add_argument('--no-rollback', action='store_true')
    ap.add_argument('--rollback-only', action='store_true')
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()

    # --keys may be a file
    if a.keys and Path(a.keys).is_file():
        a.keys = Path(a.keys).read_text().strip()

    binds = parse_binds(a.bind, a.images_dir, a.arm64_dest)
    if not binds:
        print('no binds (need --bind and/or --images-dir)', file=sys.stderr)
        return 2
    exp_map, exp_paths = ({}, [])
    if a.expected:
        exp_map, exp_paths = expected_map(json.loads(Path(a.expected).read_text()))

    if a.dry_run:
        plan(a, binds, exp_paths)
        return 0

    if not a.serial:
        print('--serial required for a real run', file=sys.stderr)
        return 2
    Path(a.out).mkdir(parents=True, exist_ok=True)
    if a.rollback_only:
        # Without the deploy receipt (another --out) there are no baseline shas; the fingerprints then carry the check
        # (2026-10-01 #96: a plan pointed --out elsewhere, the refusal left the overlay mounted and the board locked).
        if not (Path(a.out) / 'deploy-receipt.json').exists() and not (a.rollback_runtime_fp and a.rollback_boot_fp):
            print(f'--rollback-only without {a.out}/deploy-receipt.json needs --rollback-runtime-fp and '
                  f'--rollback-boot-fp', file=sys.stderr)
            return 2
        return 0 if rollback(a, binds, a.out) else 1

    if a.note_cmd and a.board_md:
        r = board_note(a.note_cmd, 'lock', a.board_md, a.serial, a.lane,
                       'sweep_bind_deploy: bind overlay + expected-run verify + shard + rollback')
        if r.returncode not in (0,):
            print('lock failed/busy:', r.stdout, r.stderr, file=sys.stderr)
            return 5
    try:
        if not deploy_and_verify(a, binds, exp_map, exp_paths, a.out):
            print('verify failed -> rolling back, not running sweep')
            rollback(a, binds, a.out)
            return 1
        if not a.no_run:
            if not (a.bms_batch and a.manifest and a.keys and a.input_root):
                print('sweep needs --bms-batch --manifest --keys --input-root (or pass --no-run)', file=sys.stderr)
            else:
                run_sweep(a, a.out)
        ok = True
        if not a.no_rollback:
            ok = rollback(a, binds, a.out)
        return 0 if ok else 1
    finally:
        if a.note_cmd and a.board_md and not a.no_rollback:
            board_note(a.note_cmd, 'unlock', a.board_md, a.serial, a.lane)


if __name__ == '__main__':
    sys.exit(main())
