"""#51: t+5 / t+20 screenshots for the 16 alive-at-15s apps on 61b.

Per app: cold stop -> sandbox -> desktop launch -> at t+5 and t+20:
  focus-window check (id + pid must belong to the app's uid), non-black
  check (jpeg size != 36627 and > 40 KB), capture + sha256. fd-notes extra:
  if focused at t+5, type one line into the note field, then extra shot.
Results + focus records -> results.json. No image reading.
"""
import json, sys, time, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b4-51-noice-61b-20260929T1340'
BLACK_SIZE = 36627
KEYS = ['fd-notes', 'fd-filemanager', 'fd-binaryeye', 'anki', 'fd-mobile',
        'localsend', 'noice', 'ooniprobe', 'fd-etar', 'fd-fluffychat',
        'fd-immich', 'fd-kitchenowl', 'fd-minetest', 'fd-stk', 'burgerking',
        'mindustry']
if len(sys.argv) > 1 and sys.argv[1] == '--keys':
    KEYS = sys.argv[2].split(',')
out = Path.home() / 'a2hlab/board' / RUN
out.mkdir(parents=True, exist_ok=False)
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()
manifest = {a['key']: a for a in json.load(open(ROOT / 'apps.json'))['apps']}
remote = '/data/local/tmp/' + RUN
board.shell('mkdir -p ' + remote)

def uid_of(pkg):
    _, t = board.shell('bm dump -n ' + pkg)
    return b.parse_bundle(t, pkg)['uid']

def alive_pids(uid):
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    return {r['pid'] for r in b.processes(ps) if r['uid'] == uid}

def focus_info():
    """(focus_id, owner_pid) from WindowManagerService dump."""
    _, wm = board.shell("hidumper -s WindowManagerService -a '-a'")
    import re as _re
    m = _re.search(r'^Focus window:\s*(\d+)', wm, _re.M)
    if not m:
        return None, None, wm[-200:]
    wid = int(m.group(1))
    # Window rows: <name-with-spaces> DisplayId Pid WinId Type Mode Flag ZOrd
    # App window names contain spaces, so fixed columns break; anchor on the
    # 7-numeric run (displayId pid winId type mode flag zord).
    # app-window rows end with negative ZOrd (-1), so only anchor on
    # displayId pid winId type: " 0 11043 37 1001 "
    rx = _re.compile(r'\s(\d+)\s+(\d+)\s+%d\s+\d+\s' % wid)
    for line in wm.splitlines():
        m2 = rx.search(line)
        if m2:
            return wid, int(m2.group(2)), None
    return wid, None, None

def app_windows(uid_pids):
    """App window rows in the WMS main table whose pid is one of ours.
    Robust to truncated single-token window names (bms_batch.foreground
    parses the same way). Returns [(winid, pid), ...]."""
    import re as _re
    _, wm = board.shell("hidumper -s WindowManagerService -a '-a'")
    rows = []
    # Tail-anchored: NAME (may contain spaces!) then DisplayId Pid WinId Type
    # Mode Flag ZOrd(negative ok) Orientation, then the rect bracket.
    row_rx = _re.compile(
        r'^(?P<name>.+?)\s+(?P<disp>\d+)\s+(?P<pid>\d+)\s+(?P<wid>\d+)\s+'
        r'(?P<type>\d+)\s+(?P<mode>\d+)\s+(?P<flag>\d+)\s+(?P<zord>-?\d+)\s+'
        r'(?P<orient>\d+)\s+\[')
    for line in wm.splitlines():
        m = row_rx.match(line)
        if m:
            pid = int(m.group('pid'))
            if pid in uid_pids and not m.group('name').startswith('SCB'):
                rows.append((int(m.group('wid')), pid))
    focus = _re.search(r'^Focus window:\s*(\d+)', wm, _re.M)
    return rows, (int(focus.group(1)) if focus else None)

def wait_app_window(uid_pids, tries=3, delay=2.0):
    """Bounded wait for an app window row to appear (windows register late)."""
    probes = []
    for i in range(tries):
        rows, focus_id = app_windows(uid_pids)
        probes.append({'app_windows': rows, 'focus_window_id': focus_id})
        if rows:
            return probes, True
        if i < tries - 1:
            time.sleep(delay)
    return probes, False

def wait_focus(uid_pids, tries=3, delay=2.0):
    """Bounded focus wait: app windows register late; probe up to tries times.
    Returns (probes, belongs). probes keep the last raw row on parse failure."""
    probes = []
    for i in range(tries):
        wid, owner, raw = focus_info()
        belongs = owner in uid_pids if owner else False
        entry = {'window_id': wid, 'owner_pid': owner, 'belongs_to_app': belongs}
        if raw and not belongs:
            entry['raw'] = str(raw)[:200]
        probes.append(entry)
        if belongs:
            return probes, True
        if i < tries - 1:
            time.sleep(delay)
    return probes, False

def shot(board_remote_dir, k, tag, uid):
    name = f'{k}-{tag}.jpeg'  # caller appends gate level via rec
    board.shell(f'snapshot_display -f {remote}/{name}')
    local = out / k / name
    board.receive(f'{remote}/{name}', local)
    size = local.stat().st_size
    h = hashlib.sha256(local.read_bytes()).hexdigest()
    black = (size == BLACK_SIZE) or (size < 40000)
    return {'path': str(local), 'size': size, 'sha256': h, 'non_black': not black}

results = []
for i, k in enumerate(KEYS):
    app = manifest[k]
    if not app.get('package'):
        # apps.json has package=None for noice/x — resolve like collect_app
        app = dict(b.resolve_input(Path.home() / 'a2hlab/app-inputs', app))
    d = out / k
    d.mkdir()
    board.shell('mkdir -p ' + remote + '/' + k)
    rec = {'key': k, 'package': app['package'], 'started_at': time.time()}
    try:
        uid = uid_of(app['package'])
    except Exception as e:
        rec['error'] = 'bm dump: %r' % e
        results.append(rec); b.save(out / 'results.json', {'run': RUN, 'done': len(results), 'total': len(KEYS), 'trials': results})
        print('%d/%d %s -> bm-dump-error' % (i+1, len(KEYS), k), flush=True)
        continue
    rec['uid'] = uid
    try:
        b.cold_stop(board, app['package'], uid, d)
    except Exception as e:
        rec['cold_stop_error'] = repr(e)[:120]
    try:
        b.prepare_sandbox(board, app['package'], uid, d)
        rec['sandbox_prepared'] = True
    except Exception as e:
        rec['sandbox_prep_error'] = repr(e)[:120]
    _, bd = board.shell('bm dump -n ' + app['package'])
    try:
        parsed = b.parse_bundle(bd, app['package'])
        rec['desktop_activity'] = parsed.get('desktop_activity') or app.get('launch_activity')
    except Exception:
        rec['desktop_activity'] = app.get('launch_activity')
    app_l = dict(app, launch_activity=rec['desktop_activity'])
    t0 = time.time()
    for attempt in range(2):
        try:
            b.desktop_launch(board, app_l, remote + '/' + k, d, rec)
            rec['clicked'] = True
            break
        except Exception as e:
            rec['launch_error'] = repr(e)[:160]
            if attempt == 0:
                time.sleep(3)  # uitest dumpLayout transient rc=1: one retry
                # drop local dumps from the failed attempt: layout()'s
                # stale-evidence guard refuses to reuse settle-0.json etc.
                for stale in list(d.glob('settle-*.json')) + list(d.glob('icons--*.json')):
                    stale.unlink(missing_ok=True)
    # ---- t+5 ----
    time.sleep(max(0, 5.0 - (time.time() - t0)))
    pids = alive_pids(uid)
    rec['pids_at_5s'] = sorted(pids)
    probes, win_ok = wait_app_window(pids)
    rec['window_at_5s_probes'] = probes
    focus_id = (probes[-1] or {}).get('focus_window_id')
    # two-tier gate: strong = WMS row with our pid; weak = focus left the
    # desktop (11) while our process lives but WMS shows no parseable row
    # (those windows register with owner Pid:-1 outside the main table)
    weak_ok = (not win_ok) and focus_id not in (None, 11) and bool(pids)
    rec['gate_at_5s'] = 'strong' if win_ok else ('weak' if weak_ok else None)
    if win_ok or weak_ok:
        rec['shot_5s'] = shot(remote, k, 't5', uid)
        if k == 'fd-notes':
            board.shell('uitest uiInput inputText 800 700 "alive16 check line"')
            time.sleep(1)
            rec['fd_notes_typed'] = True
            rec['shot_after_type'] = shot(remote, k, 'after-type', uid)
    # ---- t+20 ----
    time.sleep(max(0, 20.0 - (time.time() - t0)))
    pids = alive_pids(uid)
    rec['pids_at_20s'] = sorted(pids)
    probes, win_ok = wait_app_window(pids)
    rec['window_at_20s_probes'] = probes
    focus_id = (probes[-1] or {}).get('focus_window_id')
    weak_ok = (not win_ok) and focus_id not in (None, 11) and bool(pids)
    rec['gate_at_20s'] = 'strong' if win_ok else ('weak' if weak_ok else None)
    if win_ok or weak_ok:
        rec['shot_20s'] = shot(remote, k, 't20', uid)
    rec['finished_at'] = time.time()
    results.append(rec)
    b.save(d / 'record.json', rec)
    b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'done': len(results), 'total': len(KEYS), 'trials': results})
    print('%d/%d %s -> pids5=%s gate5=%s shot5=%s | pids20=%s gate20=%s shot20=%s' % (
        i+1, len(KEYS), k, bool(rec.get('pids_at_5s')), rec.get('gate_at_5s'), bool(rec.get('shot_5s')),
        bool(rec.get('pids_at_20s')), rec.get('gate_at_20s'), bool(rec.get('shot_20s'))), flush=True)
print('DONE', len(results), flush=True)
