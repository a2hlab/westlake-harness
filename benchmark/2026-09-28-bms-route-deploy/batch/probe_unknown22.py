"""#48: per-app hilog forensics for the 22 first_blocker=unknown keys (61b).

Per app (bms_batch primitives, same gates as the sweep):
  boot_id + desktop-focus check -> cold stop -> hilog -r -> desktop launch ->
  t+3 / t+15 liveness -> hilog -x to disk -> new faultlog pull.
First fatal line bucketing from the per-app hilog (FATAL EXCEPTION /
AndroidRuntime / UnsatisfiedLinkError / ClassNotFoundException / kill reason
/ native signal), raw line kept verbatim. No image reading.
"""
import json, sys, time, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b4-48-unknown22-61b-20260929T1015'
out = Path.home() / 'a2hlab/board' / RUN
out.mkdir(parents=True, exist_ok=False)
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()  # boot_id + lock lane + serial + (retry-once) focus checks live here
manifest = {a['key']: a for a in json.load(open(ROOT / 'apps.json'))['apps']}
KEYS = ['termux', 'ooniprobe', 'opencamera', 'fd-android', 'fd-etar', 'fd-feeder',
        'fd-fluffychat', 'fd-im-vector-app', 'fd-immich', 'fd-k9', 'fd-kitchenowl',
        'fd-libre', 'fd-minetest', 'fd-saber', 'fd-shatteredpixeldungeon', 'fd-tusky',
        'fd-tutanota', 'fd-wifianalyzer', 'fd-stk', 'burgerking', 'ppsspp', 'mindustry']
remote = '/data/local/tmp/' + RUN
board.shell('mkdir -p ' + remote)

def uid_of(pkg):
    _, t = board.shell('bm dump -n ' + pkg)
    return b.parse_bundle(t, pkg)['uid']

def alive(uid):
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    return [r['pid'] for r in b.processes(ps) if r['uid'] == uid]

results = []
for i, k in enumerate(KEYS):
    app = manifest[k]
    d = out / k
    d.mkdir(exist_ok=False)  # cold_stop writes processes-before.txt here
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
    if not b.cold_stop(board, app['package'], uid, d):
        rec['error'] = 'cold stop not proven'
    try:
        b.prepare_sandbox(board, app['package'], uid, d)
        rec['sandbox_prepared'] = True
    except Exception as e:
        rec['sandbox_prep_error'] = repr(e)[:120]
    # desktop activity override (apps.json static value drifts; e.g. fossify .Red)
    _, bd = board.shell('bm dump -n ' + app['package'])
    try:
        parsed = b.parse_bundle(bd, app['package'])
        rec['desktop_activity'] = parsed.get('desktop_activity') or app.get('launch_activity')
    except Exception:
        rec['desktop_activity'] = app.get('launch_activity')
    app_l = dict(app, launch_activity=rec['desktop_activity'])
    # clear hilog, capture in background via pidfile
    board.shell('hilog -r >/dev/null 2>&1; rm -f /data/local/tmp/hilog.pid; hilog > ' + remote + '/' + k + '-hilog.txt 2>&1 & echo $! > /data/local/tmp/hilog.pid; true')
    try:
        b.desktop_launch(board, app_l, remote + '/' + k, d, rec)
    except Exception as e:
        rec['launch_error'] = repr(e)[:160]
    time.sleep(3)
    rec['pids_at_3s'] = alive(uid)
    time.sleep(12)  # t+15
    rec['pids_at_15s'] = alive(uid)
    board.shell('kill $(cat /data/local/tmp/hilog.pid) 2>/dev/null; true')
    board.shell('hilog -x > ' + remote + '/' + k + '-hilog-flush.txt 2>&1; true')
    try:
        board.receive(remote + '/' + k + '-hilog.txt', d / 'hilog.txt')
    except Exception:
        pass
    rec['finished_at'] = time.time()
    results.append(rec)
    b.save(d / 'record.json', rec)
    b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'done': len(results), 'total': len(KEYS), 'trials': results})
    print('%d/%d %s -> pids3=%s pids15=%s err=%s' % (i+1, len(KEYS), k, rec['pids_at_3s'], rec['pids_at_15s'], rec.get('launch_error')), flush=True)
print('DONE', len(results), flush=True)
