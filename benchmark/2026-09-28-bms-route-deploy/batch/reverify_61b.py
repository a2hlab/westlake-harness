"""#36 ④: fd-notes re-verify + fd-filemanager/fd-binaryeye supplement (61b).

fd-notes: desktop launch, 30 s liveness, type one line via uitest uiInput,
two screenshots. fd-filemanager / fd-binaryeye: desktop launch, 30 s,
screenshot + hilog. Paths+hashes only; no image reading (outer review).
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b4-36-reverify-61b-20260928T2235'
out = Path.home() / 'a2hlab/board' / RUN
out.mkdir(parents=True, exist_ok=False)
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()
manifest = {a['key']: a for a in json.load(open(ROOT / 'apps.json'))['apps']}
remote = '/data/local/tmp/' + RUN

def uid_of(pkg):
    _, t = board.shell('bm dump -n ' + pkg)
    return b.parse_bundle(t, pkg)['uid']

def alive(uid):
    # bms_batch semantics (L479-480): UID-only filter. The forked child keeps
    # the name 'appspawn-x' until it renames, so name filtering undercounts.
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    return [r['pid'] for r in b.processes(ps) if r['uid'] == uid]

results = []
for key, do_input in (('fd-notes', True), ('fd-filemanager', False), ('fd-binaryeye', False), ('firefox', False)):
    app = manifest[key]
    d = out / key; d.mkdir()
    board.shell('mkdir -p ' + remote + '/' + key)
    uid = uid_of(app['package'])
    rec = {'key': key, 'package': app['package'], 'uid': uid, 'started_at': time.time()}
    # bms_batch.py L470-471 parity: prefer the entry BMS actually shows on the
    # desktop over the manifest's static launch_activity (fossify installs
    # resolve to .Red while apps.json pins .Green; exact match then fails).
    _, bd = board.shell('bm dump -n ' + app['package'])
    parsed = b.parse_bundle(bd, app['package'])
    rec['desktop_activity'] = parsed.get('desktop_activity') or app.get('launch_activity')
    app = dict(app, launch_activity=rec['desktop_activity'])
    if not b.cold_stop(board, app['package'], uid, d):
        rec['error'] = 'cold stop not proven'; results.append(rec); continue
    # B1 sandbox prep — the batch runner does this per app; skipping it made
    # fd-binaryeye/firefox die within 3 s in run 2200 (original run: alive at
    # 16 s WITH prep). Same recipe, receipt written to the trial dir.
    try:
        b.prepare_sandbox(board, app['package'], uid, d)
        rec['sandbox_prepared'] = True
    except Exception as e:
        rec['sandbox_prep_error'] = repr(e)
    # hilog clear + background capture for the whole trial (pidfile kill:
    # pkill -f "hilog >" matches the carrying shell itself)
    board.shell('hilog -r >/dev/null 2>&1')
    board.shell('rm -f /data/local/tmp/hilog.pid; hilog > ' + remote + '/' + key + '-hilog.txt 2>&1 & echo $! > /data/local/tmp/hilog.pid; true')
    try:
        b.desktop_launch(board, app, remote + '/' + key, d, rec)
    except Exception as e:
        rec['launch_error'] = repr(e)
    time.sleep(3)
    mid = alive(uid); rec['pids_at_3s'] = mid
    time.sleep(27)  # total ~30 s before liveness verdict
    pids = alive(uid); rec['pids_at_30s'] = pids
    if do_input and pids:
        # verified syntax (uitest uiInput help on 61b): inputText <x> <y> <text>
        cx, cy = 540, 1000  # note area center, board 1200x1920
        board.shell("uitest uiInput inputText %d %d 'B4reverify'" % (cx, cy))
        time.sleep(1)
        rec['input_attempted'] = True
        rec['pids_after_input'] = alive(uid)
    # stop hilog background capture via pidfile (pkill -f "hilog >" matches
    # the carrying shell itself and kills the HDC channel)
    board.shell('kill $(cat /data/local/tmp/hilog.pid) 2>/dev/null; true')
    board.shell('hilog -x > ' + remote + '/' + key + '-hilog-tail.txt 2>&1; true')
    for tag in ('t3', 'final'):
        try:
            rec.setdefault('screenshots', []).append(
                b.capture(board, remote + '/' + key + '/' + tag + '.jpeg', d / (tag + '.jpeg')))
        except Exception as e:
            rec.setdefault('capture_errors', []).append('%s: %r' % (tag, e))
    board.receive(remote + '/' + key + '-hilog-tail.txt', d / 'hilog-tail.txt')
    try:
        board.receive(remote + '/' + key + '-hilog.txt', d / 'hilog.txt')
    except Exception:
        pass
    rec['finished_at'] = time.time()
    results.append(rec)
    b.save(d / 'record.json', rec)

b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'trials': results})
print(json.dumps([{k: r.get(k) for k in ('key', 'uid', 'pids_at_30s', 'pids_after_input', 'input_attempted', 'launch_error', 'error')} for r in results], indent=1))
