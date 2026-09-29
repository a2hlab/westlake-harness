#!/usr/bin/env python3
"""Offline plan or explicit OH6.1 BMS install -> desktop tap -> evidence collection.

Device execution is opt-in. Nothing here deploys R130/R155 or changes the ROM.
Desktop ID/bounds conventions derive from cts_entry_launch.py; cold process and
capture provenance derive from run-r151d.sh. See README for exact source spans.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

SERIALS = {'5ea34a4500000000000000001123012c',
           '5cd1e3dd00000000000000000923012c',
           '61b0657200000000000000000324012c'}
IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_.]*\Z')
ACTIVITY = re.compile(r'[A-Za-z_][A-Za-z0-9_.$]*\Z')
KEY = re.compile(r'[A-Za-z0-9_-]+\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
BOUNDS = re.compile(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]\Z')
ICON_PREFIX = 'AppIconCommonView_'
LAUNCHER = 'com.ohos.sceneboard'
BLACK_FRAME_BYTES = 36627
FAULT_ROOT = '/data/log/faultlog/faultlogger'
# Uniform board settings every batch starts from (see preflight). A reboot resets hilog to 256K with
# privacy masking on; at 256K an app's child-process lines are overwritten before collection (#71).
HILOG_MIN_BYTES = 16 << 20
SCREEN_OFF_MS = 86400000
CLOCK_TOLERANCE_S = 120


class AppFailure(RuntimeError):
    """A single app failed; its evidence can still be recorded."""


class BatchStop(RuntimeError):
    """Identity, lock or transport lost: no more device writes."""


class StaleEvidence(BatchStop):
    """Existing evidence belongs to an earlier attempt and must not be reused."""


class FocusMismatch(AppFailure):
    """Scheduled screenshot lacks target window ownership; retain the failed probe."""


class SandboxPreparationFailure(AppFailure):
    """The restore preparation command failed; desktop launch is forbidden."""


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_apps(path, phase='all', keys=None):
    apps = json.loads(Path(path).read_text())['apps']
    if len({a['key'] for a in apps}) != len(apps):
        raise ValueError('duplicate app key')
    ranks = {'controls': 0, 'blocked': 1, 'tail': 2}
    for a in apps:
        if not KEY.fullmatch(a['key']) or a['phase'] not in ranks:
            raise ValueError('invalid key or phase')
    apps.sort(key=lambda a: ranks[a['phase']])
    if keys:
        wanted = keys.split(',')
        if len(set(wanted)) != len(wanted) or set(wanted) - {a['key'] for a in apps}:
            raise ValueError('unknown or duplicate requested key')
        apps = [a for a in apps if a['key'] in wanted]
    if phase != 'all':
        apps = [a for a in apps if a['phase'] == phase]
    if not apps:
        raise ValueError('empty selection')
    return apps


def resolve_input(root, entry):
    directory = Path(root).expanduser() / entry['key']
    meta_path = directory / 'app-input.json'
    meta = json.loads(meta_path.read_text())
    app = meta['application']
    package = app['package']
    digest = meta['apk_sha256']
    ability = app.get('launch_activity') or entry.get('launch_activity')
    if not isinstance(package, str) or not isinstance(digest, str) or not IDENT.fullmatch(package) or not SHA.fullmatch(digest):
        raise AppFailure('invalid package or APK digest in app-input')
    if ability is not None and not isinstance(ability, str):
        raise AppFailure('invalid activity type')
    if ability and ability.startswith('.'):
        ability = package + ability
    if ability and not ACTIVITY.fullmatch(ability):
        raise AppFailure('invalid activity')
    for field, observed in [('package', package), ('apk_sha256', digest)]:
        if entry.get(field) and entry[field] != observed:
            raise AppFailure('pinned identity changed: ' + field)
    # Filename/layout-independent: select the original APK by its recorded bytes.
    candidates = list(directory.rglob('*.apk'))
    for field in ('apk', 'apk_path', 'source_apk'):
        value = meta.get(field)
        if isinstance(value, str):
            p = Path(value).expanduser()
            p = p if p.is_absolute() else directory / p
            if p.is_file() and p not in candidates:
                candidates.append(p)
    matches = [p for p in candidates if sha(p) == digest]
    if not matches:
        raise AppFailure('original APK with app-input hash not found')
    # Split APK requirements are evidence, not silently installed as a monolithic app.
    split_hint = bool(meta.get('splits') or app.get('splits') or 'with-splits' in str(app.get('kind', '')))
    return dict(entry, package=package, apk_sha256=digest, launch_activity=ability,
                apk=str(sorted(matches)[0].resolve()), input_sha256=sha(meta_path),
                split_hint=split_hint, apk_candidates=len(candidates))


def attributes(layout):
    stack = [layout]
    while stack:
        node = stack.pop()
        yield node.get('attributes') or {}
        stack.extend(node.get('children') or [])


def box(bounds):
    m = BOUNDS.fullmatch(str(bounds or ''))
    if not m:
        raise AppFailure('invalid UI bounds')
    x1, y1, x2, y2 = map(int, m.groups())
    if x2 <= x1 or y2 <= y1:
        raise AppFailure('empty UI bounds')
    return x1, y1, x2, y2


def panel(layout, known=None):
    choices = [known] if known else []
    for a in attributes(layout):
        try:
            b = box(a.get('bounds'))
        except AppFailure:
            continue
        w, h = b[2] - b[0], b[3] - b[1]
        if min(w, h) * 3 >= max(w, h):
            choices.append(b)
    return max(choices, key=lambda b: (b[2]-b[0])*(b[3]-b[1])) if choices else None


def select_icon(layout, package, ability=None):
    prefix = ICON_PREFIX + package + '.'
    exact = prefix + ability if ability else None
    matches = []
    def visit(node, launcher=False, visible=True):
        a = node.get('attributes') or {}
        if a.get('bundleName'):
            launcher = a['bundleName'] == LAUNCHER
        visible = visible and a.get('visible') not in (False, 'false') and a.get('enabled') not in (False, 'false')
        ids = [a.get('id', ''), a.get('key', '')]
        matched = exact in ids if exact else any(str(i).startswith(prefix) for i in ids)
        if launcher and matched:
            matches.append((a, visible))
        for c in node.get('children') or []:
            visit(c, launcher, visible)
    visit(layout)
    if not matches:
        return None
    if len(matches) != 1:
        raise AppFailure('ambiguous exact desktop icon')
    a, visible = matches[0]
    if not visible or not all(a.get(k) in (True, 'true') for k in ('visible', 'enabled', 'clickable')):
        raise AppFailure('desktop icon not actionable')
    b = box(a.get('bounds'))
    return {'id': a.get('id') or a.get('key'), 'bounds': a['bounds'],
            'center': [(b[0]+b[2])//2, (b[1]+b[3])//2]}


def parse_bundle(text, package):
    # bm may prefix JSON with a human-readable header.
    start = text.find('{')
    if start < 0:
        raise AppFailure('bm dump has no JSON record')
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError as exc:
        raise AppFailure('bm dump malformed JSON') from exc
    def walk(obj):
        if isinstance(obj, dict):
            yield obj
            for v in obj.values(): yield from walk(v)
        elif isinstance(obj, list):
            for v in obj: yield from walk(v)
    nodes = list(walk(data))
    if not any(n.get('name') == package or n.get('bundleName') == package for n in nodes):
        raise AppFailure('bm dump does not identify requested package')
    uids = {n['uid'] for n in nodes if type(n.get('uid')) is int and n['uid'] > 10000}
    # BMS projects Android aliases (e.g. Wikipedia DefaultIcon, Termux HomeActivity)
    # as the desktop mainAbility; the old direct-launch activity is not that icon.
    modules = data.get('hapModuleInfos') or []
    entry_name = data.get('entryModuleName')
    entries = [m for m in modules if isinstance(m, dict) and
               (not entry_name or m.get('name') == entry_name)]
    launcher = {m.get('mainAbility') or m.get('mainElementName') for m in entries}
    launcher.discard(None)
    launcher.discard('')
    if any(not isinstance(a, str) or not ACTIVITY.fullmatch(a) for a in launcher):
        raise AppFailure('invalid BMS desktop mainAbility')
    if len(launcher) > 1:
        raise AppFailure('ambiguous BMS desktop mainAbility')
    return {'queryable': True, 'uid': next(iter(uids)) if len(uids) == 1 else None,
            'uid_candidates': sorted(uids),
            'desktop_activity': next(iter(launcher)) if launcher else None}


def processes(text):
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 4 and all(x.isdigit() for x in fields[:3]):
            rows.append({'pid': int(fields[0]), 'ppid': int(fields[1]), 'uid': int(fields[2]), 'name': fields[3]})
    return rows


def focused_window(wm):
    focus = re.search(r'^Focus window:\s*(\d+)', wm, re.M)
    if not focus:
        return {'confirmed': False, 'reason': 'focus window missing'}
    wid = int(focus.group(1))
    # WMS names contain spaces; anchor on the full numeric column tail.
    row = re.compile(r'^.+?\s+\d+\s+(?P<pid>\d+)\s+(?P<wid>\d+)'
                     r'\s+\d+\s+\d+\s+\d+\s+-?\d+(?:\s|$)')
    owners = set()
    for line in wm.splitlines():
        m = row.match(line)
        if m and int(m['wid']) == wid:
            owners.add(int(m['pid']))
    if len(owners) != 1:
        return {'confirmed': False, 'window_id': wid, 'reason': 'focus row missing or ambiguous'}
    return {'window_id': wid, 'pid': owners.pop()}


def foreground(wm, pids):
    result = focused_window(wm)
    if 'pid' not in result:
        return result
    confirmed = result['pid'] in pids
    return dict(result, confirmed=confirmed,
                reason='focused PID belongs to observed target UID' if confirmed else 'focused PID is not target')


class Board:
    def __init__(self, serial, hdc_cmd, lock_cmd, lane, out):
        if serial not in SERIALS:
            raise BatchStop('serial not in campaign whitelist')
        self.serial, self.lane = serial, lane
        self.hdc = shlex.split(hdc_cmd)
        self.lock = shlex.split(lock_cmd)
        if not self.hdc or not self.lock or not lane:
            raise BatchStop('hdc, lock command and lane required')
        self.out = Path(out)
        self.boot = None
        self.index = 0

    def command(self, argv, timeout=60):
        self.index += 1
        prefix = self.out / f'command-{self.index:05d}'
        save(prefix.with_suffix('.json'), {'argv': argv, 'started': time.time()})
        try:
            p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        except (subprocess.TimeoutExpired, OSError) as exc:
            prefix.with_suffix('.error.txt').write_text(str(exc))
            raise BatchStop('transport timeout or unavailable command') from exc
        prefix.with_suffix('.stdout.txt').write_bytes(p.stdout)
        prefix.with_suffix('.stderr.txt').write_bytes(p.stderr)
        save(prefix.with_suffix('.json'), {'argv': argv, 'exit_code': p.returncode, 'finished': time.time()})
        return p.returncode, p.stdout.decode('utf-8', 'replace') + p.stderr.decode('utf-8', 'replace')

    def raw_shell(self, command, timeout=60):
        marker = '__BMS_REMOTE_RC_' + uuid.uuid4().hex + '__'
        wrapped = command + '; bms_rc=$?; printf "\\n' + marker + '%s\\n" "$bms_rc"'
        rc, text = self.command(self.hdc + ['-t', self.serial, 'shell', wrapped], timeout)
        m = re.search(re.escape(marker) + r'(\d+)\s*$', text)
        if rc or not m:
            raise BatchStop('HDC lost remote status marker')
        return int(m.group(1)), text[:m.start()].rstrip()

    def ready(self):
        rc, held = self.command(self.lock + ['held', self.serial], 10)
        # OrbStack 'mac' bridge transiently returns rc=0 with empty output.
        # Retry once after 2 s only for that empty-output case; a real
        # other-lane holder name stops immediately as before.
        if not rc and not held.split():
            time.sleep(2)
            rc, held = self.command(self.lock + ['held', self.serial], 10)
        if rc or not held.split() or held.split()[0] != self.lane:
            raise BatchStop('invoking lane does not hold board lock')
        rc, targets = self.command(self.hdc + ['list', 'targets'], 15)
        if not rc and not targets.split():
            time.sleep(2)
            rc, targets = self.command(self.hdc + ['list', 'targets'], 15)
        if rc or self.serial not in targets.split():
            raise BatchStop('assigned serial detached')
        rc, boot = self.raw_shell('cat /proc/sys/kernel/random/boot_id')
        if rc or not re.fullmatch(r'[0-9a-f-]{36}', boot.strip()):
            raise BatchStop('cannot read boot identity')
        if self.boot is not None and boot != self.boot:
            raise BatchStop('boot changed; stop batch')
        self.boot = boot

    def shell(self, command, required=True, timeout=60):
        self.ready()  # Guards reads too; no command can drift to another session/board.
        rc, text = self.raw_shell(command, timeout)
        if required and rc:
            raise AppFailure(f'remote command failed ({rc}): {command}: {text[-300:]}')
        return rc, text

    def send(self, local, remote):
        self.ready()
        rc, text = self.command(self.hdc + ['-t', self.serial, 'file', 'send', str(local), remote], 180)
        if rc:
            raise BatchStop('HDC file send failed: ' + text[-200:])

    def receive(self, remote, local):
        self.ready()
        local = Path(local)
        if local.exists():
            raise AppFailure('refuse stale local evidence: ' + str(local))
        rc, text = self.command(self.hdc + ['-t', self.serial, 'file', 'recv', remote, str(local)], 60)
        if rc or not local.is_file():
            raise BatchStop('HDC receive failed: ' + text[-200:])


def layout(board, remote, out, tag):
    target = remote + '/' + tag + '.json'
    board.shell('rm -f ' + shlex.quote(target))
    board.shell('uitest dumpLayout -p ' + shlex.quote(target), timeout=45)
    local = out / (tag + '.json')
    board.receive(target, local)
    try:
        return json.loads(local.read_text())
    except ValueError as exc:
        raise AppFailure('invalid layout dump') from exc



def launcher_focused(board, attempts=3):
    """#38 gate: refuse to click unless the desktop (sceneboard) holds focus.

    Bounded retry for the transient 'focus row missing' state observed right
    after bm uninstall/reinstall (run2258 termux: row missing once, present on
    manual re-check seconds later). Unknown-state retries wake+Home first;
    after `attempts` tries the gate still BatchStops — no weakening.
    """
    last = None
    for attempt in range(attempts):
        board.shell('power-shell wakeup')
        board.shell('uitest uiInput keyEvent Home')
        _, wm = board.shell("hidumper -s WindowManagerService -a '-a'")
        observation = focused_window(wm)
        pid = observation.get('pid')
        if pid is None:
            last = observation['reason'] + '; desktop state unknown'
            if attempt + 1 < attempts:
                time.sleep(2)
            continue
        _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
        name = next((r['name'] for r in processes(ps) if r['pid'] == pid), '')
        if name != 'com.ohos.sceneboard':
            raise BatchStop('launcher not focused (pid %d is %s); not clicking' % (pid, name or 'unknown'))
        return pid
    raise BatchStop(last)

def desktop_launch(board, app, remote, out, record, pages=10):
    board.shell('power-shell wakeup')
    record['launcher_focus_gate'] = launcher_focused(board)
    # No global timeout mutation: wake before each UI step and capture.
    board.shell('uitest uiInput keyEvent Home')
    screen = None
    for attempt in range(6):
        tree = layout(board, remote, out, 'settle-' + str(attempt))
        attrs = list(attributes(tree))
        ids = [str(a.get('id') or a.get('key') or '') for a in attrs]
        screen = panel(tree, screen)
        if any(i.startswith(ICON_PREFIX) for i in ids):
            break
        dismiss = [a for a in attrs if (a.get('id') or a.get('key')) == 'advanced_dialog_button_0']
        if any('UsbFunctionSwitchExtAbility' in i for i in ids) and len(dismiss) == 1:
            b = box(dismiss[0].get('bounds'))
            board.shell(f'uitest uiInput click {(b[0]+b[2])//2} {(b[1]+b[3])//2}')
        elif screen and ('ScreenLockRootComponent' in ids or attempt % 2):
            x1, y1, x2, y2 = screen
            board.shell(f'uitest uiInput swipe {(x1+x2)//2} {y2-(y2-y1)//10} {(x1+x2)//2} {y1+(y2-y1)//5}')
        else:
            board.shell('uitest uiInput keyEvent Home')
    else:
        raise AppFailure('desktop not reached')
    # Home can retain the current page: search both directions with bounded swipes.
    for direction in (-1, 1):
        for page in range(pages):
            tree = layout(board, remote, out, f'icons-{direction}-{page}')
            screen = panel(tree, screen)
            chosen = select_icon(tree, app['package'], app.get('launch_activity'))
            if chosen:
                record['selected_icon'] = chosen
                save(out / 'record.json', record)  # Intent durable before input.
                x, y = chosen['center']
                board.shell(f'uitest uiInput click {x} {y}')
                record['clicked'] = True
                record['click_monotonic'] = time.monotonic()
                record['clicked_at'] = time.time()
                # Every uitest call leaves the screen-off override at 10 s (5cd/5ea/61b:
                # "OverrideTimeout=10000ms"), so without this the lock screen covers the
                # app before a t+20 capture. The click is the last uitest call of a launch.
                board.shell('power-shell timeout -o 86400000', required=False)
                return
            if screen is None:
                raise AppFailure('cannot determine screen size for page search')
            x1, y1, x2, y2 = screen
            left, right, cy = x1+(x2-x1)//5, x2-(x2-x1)//5, (y1+y2)//2
            start, end = (right, left) if direction == -1 else (left, right)
            board.shell(f'uitest uiInput swipe {start} {cy} {end} {cy}')
    raise AppFailure('exact desktop icon absent across searched pages')


def capture(board, remote, local, before_snapshot=None):
    board.shell('rm -f ' + shlex.quote(remote))
    board.shell('power-shell wakeup')
    if before_snapshot is not None:
        before_snapshot()
    board.shell('snapshot_display -f ' + shlex.quote(remote), timeout=45)
    _, info = board.shell('stat -c "%s %Y" ' + shlex.quote(remote))
    _, remote_hash = board.shell('sha256sum ' + shlex.quote(remote))
    digest = remote_hash.split()[0] if remote_hash.split() else ''
    if not SHA.fullmatch(digest):
        raise AppFailure('invalid screenshot hash')
    board.receive(remote, local)
    data = local.read_bytes()
    if len(data) < 4 or data[:2] != b'\xff\xd8' or sha(local) != digest:
        raise AppFailure('screenshot malformed or receive hash mismatch')
    return {'path': str(local), 'sha256': digest, 'remote_stat': info,
            'bytes': len(data), 'known_black_frame': len(data) == BLACK_FRAME_BYTES,
            'captured_at': time.time(), 'visual_verdict': 'pending_review'}


def cold_stop(board, package, uid, out, tag='before'):
    board.shell('aa force-stop ' + shlex.quote(package))
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    (out / ('processes-'+tag+'.txt')).write_text(ps)
    rows = processes(ps)
    parents = [r['pid'] for r in rows if r['uid'] == 0 and r['ppid'] == 1 and r['name'] == 'appspawn-x']
    target = [r for r in rows if uid is not None and r['uid'] == uid]
    if target:
        if len(parents) != 1 or any(r['ppid'] != parents[0] or r['name'] != 'appspawn-x' for r in target):
            raise AppFailure('target still alive; cannot safely identify cold-stop child')
        for row in target:
            pid = row['pid']
            # Re-check kernel identity in the same command immediately before kill.
            board.shell(f'test "$(sed -n \'s/^Uid:[[:space:]]*\\([0-9]*\\).*/\\1/p\' /proc/{pid}/status)" = {uid} && '
                        f'test "$(sed -n \'s/^PPid:[[:space:]]*\\([0-9]*\\).*/\\1/p\' /proc/{pid}/status)" = {parents[0]} && kill -9 {pid}')
    for _ in range(10):
        _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
        if uid is not None and not any(r['uid'] == uid for r in processes(ps)):
            return True
        time.sleep(.2)
    return False


def prepare_sandbox(board, package, uid, out):
    """Run the accepted restore command body, changing only package and UID."""
    if not isinstance(package, str) or not IDENT.fullmatch(package) or '.' not in package:
        raise AppFailure('invalid sandbox package')
    if type(uid) is not int or uid < 20000000:
        raise AppFailure('invalid sandbox app UID')
    recipe = Path(__file__).with_name('prepare_sandbox.sh')
    command = 'set -e\nD() { sh -c "$1"; }\n' + recipe.read_text()
    command += '\nprepare_sandbox ' + shlex.quote(package) + ' ' + str(uid)
    command_path = Path(out)/'sandbox-command.sh'
    command_path.write_text(command + '\n')
    rc, output = board.shell(command, required=False)
    Path(out, 'sandbox-preparation.txt').write_text(output)
    receipt = {'package': package, 'uid': uid, 'recipe_sha256': sha(recipe), 'return_code': rc,
               'command_path': str(command_path), 'command_sha256': sha(command_path)}
    save(Path(out)/'sandbox-preparation.json', receipt)
    if rc:
        raise SandboxPreparationFailure(f'sandbox preparation failed ({rc}); command: {command_path}')
    return receipt


def bm_success(rc, text, action):
    """BMS can return rc=0 with an error; require its positive operation receipt."""
    return (rc == 0 and bool(re.search(r'\b' + action + r'\s+bundle\s+success(?:fully)?\b', text, re.I))
            and not re.search(r'\b(?:error|failed|failure)\b', text, re.I))


def uninstall_existing(board, app, out):
    rc, text = board.shell('bm dump -n ' + shlex.quote(app['package']), required=False)
    (out/'bundle-before-reinstall.txt').write_text(text)
    try:
        current = parse_bundle(text, app['package'])
        if rc:
            raise AppFailure('BMS pre-reinstall query failed')
    except AppFailure:
        # Only a named BMS absence response is absence; malformed JSON is not.
        if not re.search(r'failed to get (?:bundle )?information|bundle (?:does not exist|not found)|\b9568386\b', text, re.I):
            raise
        return {'attempted': False, 'reason': 'not installed', 'query_return_code': rc}
    if current['uid'] is None or not cold_stop(board, app['package'], current['uid'], out, 'uninstall'):
        raise AppFailure('cannot identify installed target for reinstall')
    rc, text = board.shell('bm uninstall -n ' + shlex.quote(app['package']), required=False, timeout=180)
    (out/'uninstall.txt').write_text(text)
    receipt = {'attempted': True, 'return_code': rc, 'success_text': bm_success(rc, text, 'uninstall'),
               'output': str(out/'uninstall.txt')}
    save(out/'uninstall.json', receipt)
    if not receipt['success_text']:
        raise AppFailure('uninstall failed; refusing reinstall')
    return receipt


def fault_files(board, out, tag):
    _, text = board.shell('find ' + FAULT_ROOT + ' -maxdepth 1 -type f -print')
    (out/('faults-'+tag+'.txt')).write_text(text)
    files = set()
    for path in text.splitlines():
        if not path.startswith(FAULT_ROOT + '/') or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', path[len(FAULT_ROOT)+1:]):
            raise AppFailure('invalid faultlog listing')
        files.add(path)
    return files


def finish_diagnostics(board, out, remote, before):
    target = remote + '/hilog.txt'
    rc, text = board.shell('hilog -x > ' + shlex.quote(target) + ' 2>&1', required=False, timeout=60)
    board.receive(target, out/'hilog.txt')
    result = {'return_code': rc, 'path': str(out/'hilog.txt'), 'sha256': sha(out/'hilog.txt'),
              'complete': False, 'faultlogs': [], 'attribution': 'new since prelaunch; not proof target caused each fault'}
    save(out/'diagnostics.json', result)
    if rc:
        raise AppFailure('hilog dump failed')
    after = fault_files(board, out, 'after')
    (out/'faultlogs').mkdir(exist_ok=True)
    for path in sorted(after - before):
        local = out/'faultlogs'/Path(path).name
        board.receive(path, local)
        result['faultlogs'].append({'remote': path, 'path': str(local), 'sha256': sha(local)})
        save(out/'diagnostics.json', result)
    result['complete'] = True
    save(out/'diagnostics.json', result)
    return result


def timed_collection(board, uid, out, remote, rec, wait_seconds, shots, focus_check, hilog_seconds, faults_before):
    start = rec['click_monotonic']
    selected = shots if shots is not None else [3.0, wait_seconds]
    # Keep legacy t3/final filenames even when --wait=3 requests two captures.
    schedule = [(offset, 'shot', ('t'+str(float(offset)).removesuffix('.0')) if shots is not None else ('t3' if i == 0 else 'final'))
                for i, offset in enumerate(selected)]
    if hilog_seconds is not None:
        schedule.append((hilog_seconds, 'hilog', 'hilog'))
    schedule.append((max(wait_seconds, max(selected)), 'observe', 'after'))
    for offset, event, tag in sorted(schedule, key=lambda x: x[0]):
        time.sleep(max(0, offset - (time.monotonic() - start)))
        if event == 'hilog':
            rec['diagnostics'] = finish_diagnostics(board, out, remote, faults_before)
            rec['diagnostics']['elapsed_seconds'] = time.monotonic() - start
        else:
            observation = {}
            def observe():
                _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
                (out/('processes-'+tag+'.txt')).write_text(ps)
                pids = [r['pid'] for r in processes(ps) if r['uid'] == uid]
                _, wm = board.shell("hidumper -s WindowManagerService -a '-a'")
                (out/('windows-'+tag+'.txt')).write_text(wm)
                observation.update(foreground(wm, pids), observed_pids=pids,
                                   checked_at=time.time(), elapsed_seconds=time.monotonic()-start)
            if event == 'shot':
                def check_focus():
                    observe()
                    if (focus_check or shots is not None) and not observation['confirmed']:
                        raise FocusMismatch(observation['reason'])
                try:
                    shot = capture(board, remote+'/'+tag+'.jpeg', out/(tag+'.jpeg'), before_snapshot=check_focus)
                    shot.update(captured=True, accepted=observation['confirmed'] and not shot['known_black_frame'])
                except FocusMismatch as exc:
                    shot = {'captured': False, 'accepted': False, 'known_black_frame': False,
                            'reason': str(exc), 'visual_verdict': 'pending_review'}
                shot.update(scheduled_seconds=offset, elapsed_seconds=time.monotonic()-start,
                            foreground=observation)
                rec['screenshots'].append(shot)
            else:
                observe()
                (out/'windows.txt').write_text((out/('windows-'+tag+'.txt')).read_text())
            rec['foreground'] = observation
            rec['observed_pids'] = observation['observed_pids']
        save(out/'record.json', rec)
    strict = focus_check or shots is not None
    valid = (all(x['accepted'] for x in rec['screenshots']) if strict else
             rec['foreground']['confirmed'] and not any(x['known_black_frame'] for x in rec['screenshots']))
    rec['status'] = 'captured' if valid else 'foreground_unconfirmed'
    if any(x['known_black_frame'] for x in rec['screenshots']):
        rec['status'] = 'capture_rejected'


def collect_app(board, entry, input_root, out, remote, wait_seconds=15, *,
                reinstall=False, hilog_seconds=None, shots=None, focus_check=False):
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise StaleEvidence('refuse stale app evidence: ' + str(out))
    rec = dict(key=entry['key'], phase=entry['phase'], serial=board.serial, boot_id=board.boot,
               package=entry.get('package'), apk_sha256=entry.get('apk_sha256'),
               status='started', launch_method='desktop', clicked=False,
               install=None, bms={'queryable': False}, screenshots=[], review='pending_review')
    faults_before = None
    try:
        app = resolve_input(input_root, entry)
        rec.update({k: v for k, v in app.items() if k != 'apk'})
        rec['input_apk'] = app['apk']
        save(out / 'record.json', rec)
        board.shell('mkdir -p ' + shlex.quote(remote))
        remote_apk = remote + '/original.apk'
        board.send(app['apk'], remote_apk)
        _, readback = board.shell('sha256sum ' + shlex.quote(remote_apk))
        if not readback.split() or readback.split()[0] != app['apk_sha256']:
            raise AppFailure('staged APK hash differs')
        if reinstall:
            rec['uninstall'] = uninstall_existing(board, app, out)
        rc, response = board.shell('bm install -p ' + shlex.quote(remote_apk), required=False, timeout=180)
        (out / 'install.txt').write_text(response)
        rec['install'] = {'return_code': rc, 'success_text': bm_success(rc, response, 'install'), 'output': str(out / 'install.txt')}
        save(out/'record.json', rec)
        board.shell('rm -f ' + shlex.quote(remote_apk))
        rc, response = board.shell('bm dump -n ' + shlex.quote(app['package']), required=False)
        (out / 'bundle.txt').write_text(response)
        rec['bms']['return_code'] = rc
        if rc == 0:
            rec['bms'].update(parse_bundle(response, app['package']))
        if not rec['install']['success_text'] or rec['install']['return_code'] or not rec['bms']['queryable']:
            raise AppFailure('install or BMS readback failed')
        uid = rec['bms']['uid']
        rec['cold_stop_verified'] = cold_stop(board, app['package'], uid, out)
        if not rec['cold_stop_verified']:
            raise AppFailure('cold start identity unconfirmed')
        rec['sandbox_preparation'] = prepare_sandbox(board, app['package'], uid, out)
        rec['desktop_activity'] = rec['bms'].get('desktop_activity') or app.get('launch_activity')
        desktop_app = dict(app, launch_activity=rec['desktop_activity'])
        if hilog_seconds is not None:
            faults_before = fault_files(board, out, 'before')
            _, text = board.shell('hilog -r')
            (out/'hilog-reset.txt').write_text(text)
        desktop_launch(board, desktop_app, remote, out, rec)
        timed_collection(board, uid, out, remote, rec, wait_seconds,
                         shots, focus_check, hilog_seconds, faults_before)
        # App-specific stop only. Keep installed app and evidence for the reviewer.
        rec['cleanup_stopped'] = cold_stop(board, app['package'], uid, out, 'cleanup')
        if not rec['cleanup_stopped']:
            raise BatchStop('target cleanup could not be verified; stop before next app')
    except (BatchStop, KeyboardInterrupt) as exc:
        rec.update(status='batch_interrupted', error=str(exc))
        raise BatchStop(str(exc) or 'interrupted') from exc
    except (AppFailure, OSError, ValueError, KeyError) as exc:
        rec.update(status='sandbox_prep_failed' if isinstance(exc, SandboxPreparationFailure) else 'app_failed', error=str(exc))
        if faults_before is not None and not (out/'diagnostics.json').exists():
            try:
                rec['diagnostics'] = finish_diagnostics(board, out, remote, faults_before)
            except BatchStop as diagnostic_exc:
                rec.update(status='batch_interrupted', diagnostic_error=str(diagnostic_exc))
                raise
            except (AppFailure, OSError) as diagnostic_exc:
                rec['diagnostic_error'] = str(diagnostic_exc)
        if (out/'uninstall.json').exists():
            rec['uninstall'] = json.loads((out/'uninstall.json').read_text())
        if rec['bms'].get('queryable') and rec['bms'].get('uid') is not None:
            try:
                rec['cleanup_stopped'] = cold_stop(board, rec['package'], rec['bms']['uid'], out, 'cleanup')
                if not rec['cleanup_stopped']:
                    raise BatchStop('failed app remains alive; stop before next app')
            except (AppFailure, BatchStop) as cleanup_exc:
                rec.update(status='batch_interrupted', cleanup_error=str(cleanup_exc))
                raise BatchStop(str(cleanup_exc)) from cleanup_exc
    finally:
        if 'diagnostics' not in rec and (out/'diagnostics.json').exists():
            rec['diagnostics'] = json.loads((out/'diagnostics.json').read_text())
        rec['finished_at'] = time.time()
        save(out / 'record.json', rec)
    return rec


def size_bytes(text):
    m = re.fullmatch(r'([\d.]+)\s*([KMG]?)B?', text.strip(), re.I)
    if not m:
        return None
    return int(float(m.group(1)) * {'': 1, 'K': 1 << 10, 'M': 1 << 20, 'G': 1 << 30}[m.group(2).upper()])


def preflight(board, out, host_epoch=None):
    """Set and read back hilog buffer, hilog privacy, screen-off timeout and board clock; refuse to run if unmet."""
    host_epoch = int(time.time() if host_epoch is None else host_epoch)
    result = {'host_epoch': host_epoch, 'problems': []}
    for name, command in (('hilog_size_set', 'hilog -G 16M'), ('hilog_private_set', 'hilog -p off'),
                          ('screen_off_set', f'power-shell timeout -o {SCREEN_OFF_MS}')):
        rc, text = board.shell(command, required=False)
        result[name] = {'command': command, 'return_code': rc, 'output': text[-300:]}
    if result['screen_off_set']['return_code']:
        result['problems'].append('power-shell timeout -o failed')

    def clock():
        _, text = board.shell('date +%s', required=False)
        return int(text.strip()) - host_epoch if text.strip().isdigit() else None
    skew = clock()
    if skew is None or abs(skew) > CLOCK_TOLERANCE_S:
        rc, text = board.shell(f'date -s @{host_epoch}', required=False)
        result['clock_set'] = {'skew_before_s': skew, 'return_code': rc, 'output': text[-200:]}
        skew = clock()
    result['clock_skew_s'] = skew
    if skew is None or abs(skew) > CLOCK_TOLERANCE_S:
        result['problems'].append(f'board clock off by {skew} s after date -s')

    _, sizes = board.shell('hilog -g', required=False)
    buffers = dict(re.findall(r'Log type (\w+) buffer size is (\S+)', sizes))
    result['hilog_buffers'] = buffers
    small = [k for k, v in buffers.items() if (size_bytes(v) or 0) < HILOG_MIN_BYTES]
    if not buffers or small:
        result['problems'].append('hilog buffer below 16M: ' + (', '.join(f'{k}={buffers[k]}' for k in small) or 'unreadable'))
    _, private = board.shell('param get hilog.private.on', required=False)
    result['hilog_private_on'] = private.strip()
    if private.strip() != 'false':
        result['problems'].append('hilog privacy masking still on: ' + private.strip()[:40])
    save(out/'preflight.json', result)
    if result['problems']:
        raise BatchStop('preflight not met: ' + '; '.join(result['problems']))
    return {k: result[k] for k in ('hilog_buffers', 'hilog_private_on', 'clock_skew_s')} | {
        'screen_off_ms': SCREEN_OFF_MS, 'path': str(out/'preflight.json')}


def write_facts(out):
    """facts.txt = scripts/lab/run_facts.py over this run; ACKs quote it instead of counting by hand."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'scripts'/'lab'))
        import run_facts
        rows = [run_facts.facts(d) for d in sorted(p for p in Path(out).iterdir() if (p/'record.json').is_file())]
    except Exception as exc:  # the facts are a report; a missing helper must not hide the run's own result
        (Path(out)/'facts.txt').write_text(f'facts unavailable: {exc}\n')
        return None
    cap, slots = sum(f['captured'] for f in rows), sum(f['slots'] for f in rows)
    a5, a20 = sum(1 for f in rows if f['alive_t5']), sum(1 for f in rows if f['alive_t20'])
    lines = [f"{f['key']:<20} shots {f['captured']}/{f['slots']}  alive t5={run_facts.mark(f['alive_t5'])} "
             f"t20={run_facts.mark(f['alive_t20'])}  child_hilog={run_facts.mark(f['child_hilog_lines'])}  {f['status']}"
             for f in rows]
    total = f'TOTAL keys={len(rows)} screenshots_captured={cap}/{slots} alive_t5={a5} alive_t20={a20}'
    (Path(out)/'facts.txt').write_text('\n'.join(lines + [total]) + '\n')
    return total


def run_batch(board, entries, input_root, out, run_id, wait_seconds, **options):
    records = []
    board.ready()
    settings = preflight(board, out)
    _, version = board.shell('param get const.ohos.fullname')
    if version.strip() not in ('OpenHarmony-6.1.0.31', 'OpenHarmony 6.1.0.31'):
        raise BatchStop('expected OH6.1.0.31; this is not the OH7/T006 route')
    _, baseline = board.shell('ls -ld /data/pr03-74e6-portable; ls -l /dev/unix/socket/AppSpawnX; '
                              'sha256sum /system/bin/appspawn-x /system/android/framework/oh-adapter-runtime.jar')
    save(out/'baseline.json', {'version': version, 'boot_id': board.boot, 'readback': baseline,
                              'baseline_acceptance': 'executor must have accepted task19; these are observations'})
    for i, entry in enumerate(entries):
        app_out = out/entry['key']
        try:
            record = collect_app(board, entry, input_root, app_out,
                                 f'/data/local/tmp/bms-batch-{run_id}/{entry["key"]}', wait_seconds, **options)
            record['preflight'] = settings
            save(app_out/'record.json', record)
            records.append(record)
        except BatchStop as exc:
            stale = isinstance(exc, StaleEvidence)
            if not stale and (app_out/'record.json').exists():
                records.append(json.loads((app_out/'record.json').read_text()))
            remaining = entries[i:] if stale else entries[i+1:]
            save(out/'summary.json', {'records':records,'not_run':[x['key'] for x in remaining],'batch_error':str(exc),'review':'pending_review'})
            write_facts(out)
            raise
        save(out/'summary.json', {'records':records,'not_run':[x['key'] for x in entries[i+1:]],'review':'pending_review'})
        print(f'{i+1}/{len(entries)} {entry["key"]}: {record["status"]}', flush=True)
    total = write_facts(out)
    if total:
        print(total + '  (facts.txt; quote it verbatim in ACKs)', flush=True)
    return records


def shot_offsets(text):
    try:
        values = [float(x) for x in text.split(',')]
    except ValueError as exc:
        raise argparse.ArgumentTypeError('shots must be comma-separated seconds') from exc
    if not values or len(values) > 32 or any(not math.isfinite(x) or not 0 < x <= 300 for x in values) or values != sorted(set(values)):
        raise argparse.ArgumentTypeError('shots must be 1..32 increasing unique offsets in (0, 300]')
    return values


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, default=Path(__file__).with_name('apps.json'))
    ap.add_argument('--phase', choices=['all','controls','blocked','tail'], default='all')
    ap.add_argument('--keys', help='comma-separated subset, original phase order retained')
    ap.add_argument('--input-root', default=str(Path.home()/'a2hlab/app-inputs'))
    ap.add_argument('--execute', action='store_true', help='perform device operations; absent = offline plan only')
    ap.add_argument('--serial', choices=sorted(SERIALS))
    ap.add_argument('--lane')
    ap.add_argument('--hdc-cmd', default='hdc', help='executable or quoted command prefix')
    ap.add_argument('--lock-cmd', default=str(Path.home()/'orca/workspaces/westlake-inputs/tools/board_note.sh'))
    ap.add_argument('--out', type=Path)
    ap.add_argument('--run-id', default=datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
    ap.add_argument('--wait', type=float, default=15)
    ap.add_argument('--reinstall', action='store_true', help='uninstall a confirmed installed target before installation')
    ap.add_argument('--hilog', nargs='?', const=True, type=float, metavar='SECONDS', help='reset before launch, dump after SECONDS (default: --wait) and pull new faultlogs')
    ap.add_argument('--shots', type=shot_offsets, metavar='5,20', help='click-relative screenshot offsets; implies strict per-shot focus check')
    ap.add_argument('--focus-check', action='store_true', help='require target focus for every screenshot')
    args = ap.parse_args(argv)
    if not math.isfinite(args.wait) or not 3 <= args.wait <= 300:
        ap.error('wait must be finite and in 3..300')
    hilog_seconds = args.wait if args.hilog is True else args.hilog
    if hilog_seconds is not None and (not math.isfinite(hilog_seconds) or not 0 < hilog_seconds <= 300):
        ap.error('hilog seconds must be finite and in (0, 300]')
    options = dict(reinstall=args.reinstall, hilog_seconds=hilog_seconds,
                   shots=args.shots, focus_check=args.focus_check)
    entries = load_apps(args.manifest,args.phase,args.keys)
    if not args.execute:
        print(json.dumps({'execution':'not-requested','count':len(entries),'apps':entries,'options':options},indent=2))
        return 0
    if not args.serial or not args.lane or not args.out or not KEY.fullmatch(args.run_id) or not 3 <= args.wait <= 300:
        ap.error('execution requires serial/lane/fresh out, safe run-id and wait 3..300')
    out=args.out.expanduser().resolve()/args.run_id/args.serial
    out.mkdir(parents=True,exist_ok=False)
    save(out/'plan.json',{'apps':entries,'run_id':args.run_id,'serial':args.serial,'options':options,'review':'pending_review'})
    try:
        board=Board(args.serial,args.hdc_cmd,args.lock_cmd,args.lane,out/'commands')
        records=run_batch(board,entries,args.input_root,out,args.run_id,args.wait,**options)
        return 0 if all(r['status']=='captured' for r in records) else 1
    except (BatchStop,KeyboardInterrupt) as exc:
        save(out/'batch-stop.json',{'error':str(exc),'review':'pending_review','device_result':'unverified'})
        if not (out/'summary.json').exists():
            save(out/'summary.json', {'records': [], 'not_run': [a['key'] for a in entries],
                                      'batch_error': str(exc), 'review': 'pending_review'})
        print('STOP: '+str(exc),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
