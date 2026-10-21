#!/usr/bin/env python3
"""G06 board_run after_lock/before_unlock hooks. No uninstall or runtime deployment."""
import argparse
import datetime
import hashlib
import json
import re
import shlex
import sys
import time
from pathlib import Path

SERIAL = '5ea34a4500000000000000001123012c'
PACKAGE = 'com.miHoYo.Yuanshen'
APK_SHA = 'abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
BATCH = 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
DATA_ROOTS = [f'/data/app/el{level}/100/{kind}/{PACKAGE}'
              for level, kinds in [(1, ['base', 'database']), (2, ['base', 'database', 'sharefiles', 'log']),
                                   (3, ['base', 'database']), (4, ['base', 'database'])] for kind in kinds]


class Refuse(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Refuse(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def packages(rc, text):
    require(rc == 0 and bool(text.strip()), 'package list transport/remote/empty failure')
    lines = text.splitlines()
    require(lines[0].strip() == 'ID: 100:', 'package list header')
    names = [x.strip() for x in lines[1:] if x.strip()]
    require(bool(names) and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', x) for x in names),
            'package list malformed')
    require(len(names) == len(set(names)), 'duplicate package rows')
    return sorted(names)


def power(text):
    state = re.findall(r'^Current State: (\w+)\s', text, re.M)
    pairs = re.findall(r'ScreenOffTime: Timeout=(\d+)ms\s+OverrideTimeout=(\d+)ms', text)
    require(len(state) == len(pairs) == 1, 'power read incomplete')
    return {'state': state[0], 'timeout': int(pairs[0][0]), 'override': int(pairs[0][1])}


def focus(text):
    ids = re.findall(r'^Focus window:\s*(\d+)\s*$', text, re.M)
    require(len(ids) == 1, 'WMS focus missing')
    rows = [x.split() for x in text.splitlines() if len(x.split()) >= 8 and x.split()[3] == ids[0]]
    require(len(rows) == 1, 'WMS focused row ambiguous')
    return rows[0][0]


def buffers(text, size_bytes):
    pairs = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.fullmatch(r'Log type (\w+) buffer size is (\S+)\s*', line.strip())
        require(m is not None, 'hilog size row malformed')
        require(re.fullmatch(r'\d+(?:\.\d+)?[KMG]?B?', m[2], re.I) is not None, 'hilog size token malformed')
        n = size_bytes(m[2])  # exact existing BMS conversion, not a prefix match
        require(type(n) is int and 0 < n <= (1 << 30), 'hilog size invalid')
        pairs.append((m[1], n))
    require(bool(pairs) and len(dict(pairs)) == len(pairs), 'hilog size read incomplete')
    require(all(t in {'app', 'core', 'init', 'kmsg', 'only_prerelease'} for t, _ in pairs), 'unknown hilog type')
    return dict(pairs)


def ps_rows(text):
    lines = text.splitlines()
    require(lines and lines[0].split() == ['PID', 'PPID', 'UID', 'NAME'], 'ps header/empty')
    result = []
    for line in lines[1:]:
        if not line.strip():
            continue
        f = line.split()
        require(len(f) == 4 and all(x.isdigit() for x in f[:3]), 'malformed ps row')
        result.append(dict(pid=int(f[0]), ppid=int(f[1]), uid=int(f[2]), name=f[3]))
    require(bool(result), 'empty ps table')
    return result


def validate_guard(context, held, boot, now):
    require(context['serial'] == SERIAL and held.strip() == context['holder'], 'full holder/serial changed')
    require(boot.strip() == context['boot_id'], 'boot changed')
    require(0 <= now - context['start_epoch'] < 1800, 'window expired/future start; retain lock')


def install_origin(rec, context, uid):
    require(rec.get('serial') == SERIAL and rec.get('boot_id') == context['boot_id'], 'install board/boot')
    require(rec.get('package') == PACKAGE and rec.get('apk_sha256') == APK_SHA, 'install package/APK identity')
    require(rec.get('input_sha256') == context['input_sha256'], 'metadata SHA differs')
    install = rec.get('install') or {}
    require(install.get('return_code') == 0 and install.get('success_text') is True and not install.get('skipped'),
            'new install not proven; do not stop an unowned target')
    require((rec.get('bms') or {}).get('uid') == uid and type(uid) is int and uid > 10000, 'installed UID differs')
    require(rec.get('finished_at', 0) >= context['start_epoch'], 'install record predates window')


def restore_target(board, bms, context, record, out):
    current = packages(*board.shell('bm dump -a'))
    require([x for x in current if x != PACKAGE] == context['packages'], 'foreign package set change')
    if PACKAGE not in current:
        require(not record or not (record.get('install') or {}).get('success_text'), 'installed package unexpectedly absent')
        require(not any(r['name'] == PACKAGE for r in ps_rows(board.shell('ps -A -o PID,PPID,UID,NAME')[1])),
                'package absent but consumer present')
        return {'installed': False, 'retained': False}
    require(record is not None, 'package present without this-window install receipt')
    bundle = board.shell('bm dump -n ' + PACKAGE)[1]
    parsed = bms.parse_bundle(bundle, PACKAGE)
    uid = parsed.get('uid')
    install_origin(record, context, uid)
    # The original BMS bundle readback was produced by this exact install; compare the full JSON object.
    def obj(t):
        require('{' in t, 'bundle JSON absent')
        return json.JSONDecoder().raw_decode(t[t.index('{'):])[0]
    require(obj(bundle) == obj((out / 'installed-bundle.txt').read_text()), 'installed bundle identity drift')
    ps_rows(board.shell('ps -A -o PID,PPID,UID,NAME')[1])
    require(bms.cold_stop(board, PACKAGE, uid, out, 'g06-restore'), 'cold_stop not verified')
    require(not any(r['uid'] == uid for r in ps_rows(board.shell('ps -A -o PID,PPID,UID,NAME')[1])),
            'target consumer remains')
    require(obj(board.shell('bm dump -n ' + PACKAGE)[1]) == obj(bundle), 'bundle changed during stop')
    return {'installed': True, 'retained': True, 'uid': uid, 'package': PACKAGE,
            'apk_sha256': APK_SHA, 'bundle_readback_sha256': hashlib.sha256(bundle.encode()).hexdigest(),
            'reason': 'outer-authorized continued debugging; no uninstall or directory deletion'}


def load_bms(repo):
    sys.path[:0] = [str(repo / 'scripts/lab'), str(repo / Path(BATCH).parent)]
    import bms_batch
    return bms_batch


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['before', 'restore'])
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    require(a.execute, 'device execution requires explicit --execute; offline lane never supplies it')
    cfg = json.loads(a.config.read_text())
    require(cfg.get('approved_by') == 'outer(codex)', 'unsigned G06 config')
    require(cfg['serial'] == SERIAL, 'wrong serial')
    require(Path(cfg['hook_path']).resolve() == Path(__file__).resolve() and sha(__file__) == cfg['hook_sha256'], 'hook source drift')
    repo, window = Path(cfg['repo']), Path(cfg['window'])
    for rel, expected in cfg['source_pins'].items():
        require(sha(repo / rel) == expected, 'source drift: ' + rel)
    bms = load_bms(repo)
    log = window / ('g06-' + a.action)
    log.mkdir(exist_ok=False, parents=True)
    context_file = window / 'g06-context.json'
    context = json.loads(context_file.read_text()) if a.action == 'restore' else None
    lock = repo / 'scripts/lab/board_note.sh'

    class GuardedBoard(bms.Board):
        def ready(self):
            super().ready()
            if context:
                rc, held = self.command(self.lock + ['held', SERIAL], 10)
                require(rc == 0, 'holder read failed')
                validate_guard(context, held, self.boot, time.time())

    board = GuardedBoard(SERIAL, cfg.get('hdc', 'hdc'), shlex.quote(str(lock)), cfg['lane'], log)
    board.ready()

    def exact_files():
        for kind, expected in cfg['fingerprints'].items():
            rc, text = board.shell('sha256sum ' + ' '.join(shlex.quote(x) for x in expected), timeout=120)
            got = {}
            for line in text.splitlines():
                m = re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)', line)
                require(m is not None, 'incomplete fingerprint row')
                require(m[2] not in got, 'duplicate fingerprint path')
                got[m[2]] = m[1]
            require(rc == 0 and got == expected, kind + ' exact fingerprint changed')

    if a.action == 'before':
        rc, held = board.command(board.lock + ['held', SERIAL], 10)
        parts = held.split()
        require(rc == 0 and len(parts) == 3 and parts[0] == cfg['lane'] and parts[1].isdigit(), 'holder malformed')
        start = datetime.datetime.fromisoformat(parts[2]).timestamp()
        context = dict(serial=SERIAL, holder=held.strip(), start_epoch=start, boot_id=board.boot,
                       input_sha256=cfg['input_sha256'])
        validate_guard(context, held, board.boot, time.time())
        require(time.time() - start < 120, 'after_lock admission too late')
        require(board.boot == cfg['expected_boot'], 'fresh boot drift: regenerate admission')
        exact_files()
        context['packages'] = packages(*board.shell('bm dump -a'))
        require(PACKAGE not in context['packages'], 'already installed: this first-install plan is not reusable')
        context['power'] = power(board.shell('power-shell dump -s')[1])
        require(context['power'] == {'state': 'SLEEP', 'timeout': 30000, 'override': 10000}, 'fresh power differs')
        context['focus'] = focus(board.shell("hidumper -s WindowManagerService -a '-a'")[1])
        require(context['focus'].startswith('SCBScreenLock'), 'fresh foreground differs')
        context['hilog_buffers'] = buffers(board.shell('hilog -g')[1], bms.size_bytes)
        context['hilog_private'] = board.shell('param get hilog.private.on')[1].strip()
        require(context['hilog_private'] in {'true', 'false'}, 'hilog privacy unknown')
        require(abs(int(board.shell('date +%s')[1].strip()) - time.time()) < 100, 'clock skew; no G06 clock repair')
        for d in DATA_ROOTS + ['/data/app/el1/bundle/public/' + PACKAGE]:
            board.shell(f'test ! -e {shlex.quote(d)} && test ! -L {shlex.quote(d)}')
        require(not any(r['name'] == PACKAGE for r in ps_rows(board.shell('ps -A -o PID,PPID,UID,NAME')[1])), 'preexisting target process')
        save(context_file, context)  # before any BMS install/preflight write
        save(log / 'result.json', {'status': 'BEFORE_BOUND', 'context_sha256': sha(context_file)})
        return

    require(context['power'] == {'state': 'SLEEP', 'timeout': 30000, 'override': 10000}, 'unsupported recovery preimage')
    require(context['focus'].startswith('SCBScreenLock'), 'unsupported original foreground')
    records = sorted((window / 'shards').glob('**/genshin/record.json'))
    require(len(records) <= 1, 'multiple launch/install records')
    rec = json.loads(records[0].read_text()) if records else None
    if records and (records[0].parent / 'bundle.txt').exists():
        (log / 'installed-bundle.txt').write_bytes((records[0].parent / 'bundle.txt').read_bytes())
    result = restore_target(board, bms, context, rec, log)
    # Read-only retained-directory inventory. Never rm/chown/chmod a retained package's data.
    retained = {}
    for d in DATA_ROOTS + ['/data/app/el1/bundle/public/' + PACKAGE]:
        rc, text = board.shell(f'if test -e {shlex.quote(d)}; then stat -c "%d:%i %u:%g %a %F" {shlex.quote(d)}; '
                               f'elif test -L {shlex.quote(d)}; then exit 2; else echo ABSENT; fi')
        require(rc == 0 and text.strip(), 'retention inventory incomplete')
        retained[d] = text.strip()
    result['retained_directory_inventory'] = retained
    exact_files()
    board.shell('uitest uiInput keyEvent Home')
    board.shell('power-shell timeout -o 10000')
    for typ, size in context['hilog_buffers'].items():
        board.shell('hilog -t ' + typ + ' -G ' + str(size))
    board.shell('hilog -p ' + ('on' if context['hilog_private'] == 'true' else 'off'))
    require(buffers(board.shell('hilog -g')[1], bms.size_bytes) == context['hilog_buffers'], 'hilog size not restored')
    require(board.shell('param get hilog.private.on')[1].strip() == context['hilog_private'], 'hilog privacy not restored')
    board.shell('power-shell suspend')
    require(power(board.shell('power-shell dump -s')[1]) == context['power'], 'power not restored')
    require(focus(board.shell("hidumper -s WindowManagerService -a '-a'")[1]).startswith('SCBScreenLock'), 'lockscreen not restored')
    board.ready()
    result.update(status='RESTORED_PACKAGE_RETAINED' if result['retained'] else 'RESTORED_NO_INSTALL',
                  visual_verdict='PENDING_REVIEW', elapsed=time.time()-context['start_epoch'])
    save(log / 'result.json', result)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('G06_REFUSE_KEEP_LOCK: ' + str(exc), file=sys.stderr)
        sys.exit(2)
