"""#60: main-thread scene for the 13 near-white-blank apps (61b).

Flow per app: cold stop -> sandbox -> desktop launch (bms_batch) -> at t+20
if the process still lives, capture:
  1) dumpcatcher -p <pid> (all-thread stacks; fallback: hidumper)
  2) /proc/<pid>/task/*/wchan + stat (fallback when dumpcatcher refuses)
  3) last 50 hilog lines mentioning the pid
Classification by where the MAIN thread sits (waiting vsync / binder /
deadlock / java loop / choreographer-no-draw), raw lines kept verbatim.
"""
import json, sys, time, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b4-60-white13-61b-20260929T1245'
KEYS = ['fd-binaryeye', 'fd-mobile', 'localsend', 'noice', 'ooniprobe',
        'fd-etar', 'fd-fluffychat', 'fd-immich', 'fd-kitchenowl',
        'fd-minetest', 'fd-stk', 'burgerking', 'mindustry']
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

def pids_of(uid):
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    return {r['pid'] for r in b.processes(ps) if r['uid'] == uid}

def stack_capture(pid, d):
    """dumpcatcher first; fallback to /proc wchan+stat per thread."""
    files = {}
    rc, dc = board.shell('dumpcatcher -p %d' % pid, required=False, timeout=90)
    (d / 'dumpcatcher.txt').write_text(dc)
    files['dumpcatcher'] = 'dumpcatcher.txt'
    # per-thread wchan/stat regardless (cheap, always works)
    rc, wchan = board.shell(
        'for t in /proc/%d/task/*; do echo "== $(basename $t) $(cat $t/comm 2>/dev/null)"; '
        'echo "wchan: $(cat $t/wchan 2>/dev/null)"; '
        'echo "stat: $(cut -d\\  -f1-3 $t/stat 2>/dev/null)"; done' % pid, required=False, timeout=60)
    (d / 'wchan.txt').write_text(wchan)
    files['wchan'] = 'wchan.txt'
    return files

def hilog_tail_for(pid, d, limit=50):
    rc, txt = board.shell('hilog -x', required=False, timeout=60)
    lines = [ln for ln in txt.splitlines() if re.search(r'\b%d\b' % pid, ln)]
    keep = lines[-limit:]
    (d / ('hilog-pid-%d.txt' % pid)).write_text('\n'.join(keep))
    return len(keep)

def classify(d, pid):
    """Classify from dumpcatcher main-thread stack + wchan."""
    dc = ''
    p = d / 'dumpcatcher.txt'
    if p.is_file():
        dc = p.read_text(errors='replace')
    # main thread block in dumpcatcher output (first Tid == pid)
    main = dc
    m = re.search(r'Tid:\s*%d.*?(?=Tid:|\Z)' % pid, dc, re.S)
    if m:
        main = m.group(0)
    wchan = (d / 'wchan.txt').read_text(errors='replace') if (d / 'wchan.txt').is_file() else ''
    wm = re.search(r'== %d .*?\nwchan: (\S+)' % pid, wchan, re.S)
    main_wchan = wm.group(1) if wm else ''
    bucket, ev = 'unknown', ''
    rules = [
        ('wait-vsync', r'AChoreographer|vsync|VSync|DisplayEventReceiver'),
        ('wait-binder', r'IPCThreadState|binder|Binder|ioctl.*binder'),
        ('wait-input', r'InputChannel|looper.*input|epoll'),
        ('java-loop', r'nterp_|art::interpreter|J_invoke|Method.*invoke'),
        ('choreographer-no-draw', r'Choreographer|doFrame|FrameDisplayEventReceiver'),
        ('native-poll', r'epoll_wait|poll_sched|futex_wait'),
        ('futex-deadlock', r'futex.*OWNER|deadlock|mutex'),
    ]
    for name, rx in rules:
        m2 = re.search(rx, main)
        if m2:
            bucket = name
            for ln in main.splitlines():
                if re.search(rx, ln):
                    ev = ln.strip()[:240]; break
            break
    if bucket == 'unknown' and main_wchan:
        bucket = 'wchan:' + main_wchan
        ev = 'main wchan = ' + main_wchan
    if bucket == 'unknown' and dc:
        for ln in main.splitlines():
            if ln.startswith('#'):
                ev = ln.strip()[:240]; bucket = 'native-frame'
                break
    return {'bucket': bucket, 'main_wchan': main_wchan, 'evidence': ev}

results = []
for i, k in enumerate(KEYS):
    app = manifest[k]
    if not app.get('package'):
        app = dict(b.resolve_input(Path.home() / 'a2hlab/app-inputs', app))
    d = out / k
    d.mkdir()
    board.shell('mkdir -p ' + remote + '/' + k)
    rec = {'key': k, 'package': app['package'], 'started_at': time.time()}
    uid = uid_of(app['package'])
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
        rec['desktop_activity'] = b.parse_bundle(bd, app['package']).get('desktop_activity') or app.get('launch_activity')
    except Exception:
        rec['desktop_activity'] = app.get('launch_activity')
    app_l = dict(app, launch_activity=rec['desktop_activity'])
    t0 = time.time()
    board.shell('hilog -r >/dev/null 2>&1; true')
    for attempt in range(2):
        try:
            b.desktop_launch(board, app_l, remote + '/' + k, d, rec)
            rec['clicked'] = True
            break
        except Exception as e:
            rec['launch_error'] = repr(e)[:160]
            if attempt == 0:
                time.sleep(3)
                for stale in list(d.glob('settle-*.json')) + list(d.glob('icons--*.json')):
                    stale.unlink(missing_ok=True)
    time.sleep(max(0, 20.0 - (time.time() - t0)))
    pids = pids_of(uid)
    rec['pids_at_20s'] = sorted(pids)
    if pids:
        pid = min(pids)
        rec['probed_pid'] = pid
        rec['stack_files'] = stack_capture(pid, d)
        rec['hilog_tail_lines'] = hilog_tail_for(pid, d)
        rec['classify'] = classify(d, pid)
    rec['finished_at'] = time.time()
    results.append(rec)
    b.save(d / 'record.json', rec)
    b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'done': len(results), 'total': len(KEYS), 'trials': results})
    c = rec.get('classify') or {}
    print('%d/%d %s -> pids20=%s pid=%s bucket=%s wchan=%s' % (
        i+1, len(KEYS), k, bool(pids), rec.get('probed_pid'), c.get('bucket'), c.get('main_wchan')), flush=True)
print('DONE', len(results), flush=True)
