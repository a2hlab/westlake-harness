#!/usr/bin/env python3
"""B7 (#54): per-app first-cause probe on 5cd, run from the Mac with direct hdc.

SUPERSEDED by the unified bms_batch.py (#57: --reinstall/--hilog/--shots/--focus-check).
Kept only because the first-round runs (repro-*, fix1-*, noreg-*) were collected with it.

Per app, reusing the B4 batch primitives (same gates: lane lock, boot_id,
desktop focus before every click, exact BMS desktop icon, no `aa start`):
  [uninstall old] -> send + hash-check APK -> bm install -p (judged by output
  text) -> bm dump uid -> cold stop -> B1 prepare_sandbox -> faultlog listing
  -> hilog -r + background hilog -> desktop click -> screenshots t+5/t+20,
  pids t+3/t+15/t+20 -> hilog + new faultlogs pulled -> focus/window dump ->
  app-only cold stop (app stays installed for review).
No image reading; screenshots stay pending_review for the outer loop.
"""
import argparse
import json
import shlex
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent / '2026-09-28-bms-route-deploy' / 'batch'
sys.path.insert(0, str(BATCH))
import bms_batch as b  # noqa: E402

SERIAL = '5cd1e3dd00000000000000000923012c'
LANE = 'cc-t3'
HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
LOCK = str(Path.home() / 'orca/workspaces/westlake-inputs/tools/board_note.sh')
FAULTDIR = '/data/log/faultlog/faultlogger'
RUNTIME_FILES = [
    '/system/bin/appspawn-x',
    '/system/lib64/appspawn/libwestlake_android_child.z.so',
    '/system/android/lib64/liboh_android_runtime.so',
    '/system/android/lib64/liboh_adapter_bridge.so',
    '/system/android/lib64/libapp_native_loader.so',
    '/system/android/framework/oh-adapter-runtime.jar',
    '/system/android/framework/framework.jar',
]


def listing(board):
    _, text = board.shell('ls ' + FAULTDIR, required=False)
    return set(text.split())


def installed(board, package):
    rc, text = board.shell('bm dump -n ' + shlex.quote(package), required=False)
    try:
        return rc == 0 and b.parse_bundle(text, package)['queryable']
    except b.AppFailure:
        return False


def alive(board, uid):
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    return [r['pid'] for r in b.processes(ps) if r['uid'] == uid]


def install(board, app, remote, out, rec):
    if installed(board, app['package']):
        rc, text = board.shell('bm uninstall -n ' + shlex.quote(app['package']), required=False, timeout=120)
        (out / 'uninstall.txt').write_text(text)
        rec['uninstall'] = {'return_code': rc, 'output': text.strip()[-200:]}
    remote_apk = remote + '/original.apk'
    board.send(app['apk'], remote_apk)
    _, readback = board.shell('sha256sum ' + shlex.quote(remote_apk))
    if not readback.split() or readback.split()[0] != app['apk_sha256']:
        raise b.AppFailure('staged APK hash differs')
    rc, response = board.shell('bm install -p ' + shlex.quote(remote_apk), required=False, timeout=240)
    (out / 'install.txt').write_text(response)
    board.shell('rm -f ' + shlex.quote(remote_apk))
    ok = bool(b.re.search(r'\bsuccess(?:fully)?\b', response, b.re.I)) and 'failed' not in response.lower()
    rec['install'] = {'return_code': rc, 'success_text': ok, 'output': response.strip()[-200:]}
    if not ok or rc:
        raise b.AppFailure('install failed: ' + response.strip()[-160:])


def probe(board, app, out, remote, args):
    out.mkdir(parents=True, exist_ok=False)
    rec = {'key': app['key'], 'package': app['package'], 'apk_sha256': app['apk_sha256'],
           'serial': SERIAL, 'boot_id': board.boot, 'started_at': time.time(),
           'screenshots': [], 'review': 'pending_review'}
    board.shell('mkdir -p ' + shlex.quote(remote))
    try:
        if not args.no_install:
            install(board, app, remote, out, rec)
        rc, text = board.shell('bm dump -n ' + shlex.quote(app['package']), required=False)
        (out / 'bundle.txt').write_text(text)
        bundle = b.parse_bundle(text, app['package'])
        uid = bundle['uid']
        rec['uid'] = uid
        rec['desktop_activity'] = bundle.get('desktop_activity') or app.get('launch_activity')
        if not b.cold_stop(board, app['package'], uid, out):
            raise b.AppFailure('cold stop not proven')
        rec['sandbox'] = b.prepare_sandbox(board, app['package'], uid, out)
        before = listing(board)
        hl = remote + '/hilog.txt'
        board.shell('hilog -r >/dev/null 2>&1; rm -f ' + remote + '/hilog.pid; (hilog > ' + hl
                    + ' 2>&1 & echo $! > ' + remote + '/hilog.pid); true')
        b.desktop_launch(board, dict(app, launch_activity=rec['desktop_activity']), remote, out, rec)
        t0 = time.monotonic()
        rec['clicked_at'] = time.time()

        def at(sec):
            time.sleep(max(0, sec - (time.monotonic() - t0)))

        at(3)
        rec['pids_at_3s'] = alive(board, uid)
        at(5)
        rec['screenshots'].append(b.capture(board, remote + '/t5.jpeg', out / 't5.jpeg'))
        at(15)
        rec['pids_at_15s'] = alive(board, uid)
        at(args.final)
        pids = alive(board, uid)
        rec['pids_at_final'] = pids
        _, wm = board.shell("hidumper -s WindowManagerService -a '-a'")
        (out / 'windows.txt').write_text(wm)
        rec['foreground'] = b.foreground(wm, pids)
        rec['screenshots'].append(b.capture(board, remote + '/t%d.jpeg' % args.final, out / ('t%d.jpeg' % args.final)))
        board.shell('kill $(cat ' + remote + '/hilog.pid) 2>/dev/null; true')
        board.receive(hl, out / 'hilog.txt')
        new = sorted(listing(board) - before)
        rec['new_faultlogs'] = new
        for name in new:
            if '/' not in name:
                board.receive(FAULTDIR + '/' + name, out / name)
        rec['status'] = 'collected'
    except b.AppFailure as exc:
        rec.update(status='app_failed', error=str(exc))
    finally:
        try:
            board.shell('kill $(cat ' + remote + '/hilog.pid) 2>/dev/null; true', required=False)
            if rec.get('uid'):
                rec['cleanup_stopped'] = b.cold_stop(board, app['package'], rec['uid'], out, 'cleanup')
        finally:
            rec['finished_at'] = time.time()
            b.save(out / 'record.json', rec)
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--keys', required=True)
    p.add_argument('--run', required=True)
    p.add_argument('--inputs', required=True, help='dir with <key>/app-input.json + original APK')
    p.add_argument('--out', default=str(HERE / 'runs'))
    p.add_argument('--no-install', action='store_true', help='relaunch the already installed app')
    p.add_argument('--final', type=int, default=20)
    args = p.parse_args()
    out = Path(args.out) / args.run
    out.mkdir(parents=True, exist_ok=False)
    board = b.Board(SERIAL, HDC, LOCK, LANE, out / 'commands')
    board.ready()
    _, hashes = board.shell('sha256sum ' + ' '.join(RUNTIME_FILES))
    manifest = {a['key']: a for a in json.loads((BATCH / 'apps.json').read_text())['apps']}
    summary = {'run': args.run, 'serial': SERIAL, 'lane': LANE, 'boot_id': board.boot,
               'runtime_sha256': hashes, 'records': []}
    remote_root = '/data/local/tmp/b7-' + args.run
    for key in args.keys.split(','):
        if '=' in key:  # installed control app outside apps.json: key=package (relaunch only)
            key, package = key.split('=', 1)
            assert args.no_install, 'key=package entries are relaunch-only'
            app = {'key': key, 'package': package, 'apk_sha256': None}
        else:
            app = b.resolve_input(args.inputs, manifest[key])
        rec = probe(board, app, out / key, remote_root + '/' + key, args)
        summary['records'].append(rec)
        b.save(out / 'summary.json', summary)
        print('%s status=%s pids3=%s pids15=%s final=%s fg=%s faults=%s err=%s' % (
            key, rec.get('status'), rec.get('pids_at_3s'), rec.get('pids_at_15s'),
            rec.get('pids_at_final'), (rec.get('foreground') or {}).get('confirmed'),
            rec.get('new_faultlogs'), rec.get('error')), flush=True)
    board.shell('rm -rf ' + shlex.quote(remote_root), required=False)
    print('DONE', out)


if __name__ == '__main__':
    main()
