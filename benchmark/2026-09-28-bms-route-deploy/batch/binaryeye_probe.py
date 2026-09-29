"""#69-1: fd-binaryeye stuck-at-spawn first cause (61b).

Launch via desktop click (bms_batch), then INSIDE the window capture:
  /proc/<pid>/cmdline, comm, stack, wchan, maps + dumpcatcher at t+15/t+30,
  plus hilog -x. The child's NAME stays 'appspawn-x' (never re-execs),
  so pid discovery is by UID.
"""
import json, sys, time, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b4-69-binaryeye-probe-20260929T1520'
out = Path.home() / 'a2hlab/board' / RUN
out.mkdir(parents=True, exist_ok=False)
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()
manifest = {a['key']: a for a in json.load(open(ROOT / 'apps.json'))['apps']}
remote = '/data/local/tmp/' + RUN
board.shell('mkdir -p ' + remote + '/fd-binaryeye')
app = manifest['fd-binaryeye']
if not app.get('package'):
    app = dict(b.resolve_input(Path.home() / 'a2hlab/app-inputs', app))
d = out / 'fd-binaryeye'
d.mkdir()
_, t = board.shell('bm dump -n ' + app['package'])
uid = b.parse_bundle(t, app['package'])['uid']
rec = {'key': 'fd-binaryeye', 'package': app['package'], 'uid': uid}
b.cold_stop(board, app['package'], uid, d)
b.prepare_sandbox(board, app['package'], uid, d)
_, bd = board.shell('bm dump -n ' + app['package'])
app_l = dict(app, launch_activity=b.parse_bundle(bd, app['package']).get('desktop_activity') or app.get('launch_activity'))
board.shell('hilog -r >/dev/null 2>&1; true')

def pids_of(uid):
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    return {r['pid'] for r in b.processes(ps) if r['uid'] == uid}

def probe(tag):
    ps = pids_of(uid)
    if not ps:
        return {'pids': []}
    pid = min(ps)
    for f in ('cmdline', 'comm', 'wchan', 'stack'):
        rc, txt = board.shell('cat /proc/%d/%s 2>/dev/null' % (pid, f), required=False, timeout=30)
        (d / ('%s-%s.txt' % (tag, f))).write_text(txt or '')
    rc, maps = board.shell('cat /proc/%d/maps 2>/dev/null' % pid, required=False, timeout=30)
    (d / ('%s-maps.txt' % tag)).write_text(maps or '')
    rc, dc = board.shell('dumpcatcher -p %d' % pid, required=False, timeout=90)
    (d / ('%s-dumpcatcher.txt' % tag)).write_text(dc or '')
    _, ps2 = board.shell('ps -A -o PID,PPID,UID,NAME')
    (d / ('%s-processes.txt' % tag)).write_text(ps2)
    return {'pids': sorted(ps), 'probed_pid': pid}

t0 = time.time()
try:
    b.desktop_launch(board, app_l, remote + '/fd-binaryeye', d, rec)
    rec['clicked'] = True
except Exception as e:
    rec['launch_error'] = repr(e)[:200]
time.sleep(max(0, 15.0 - (time.time() - t0)))
rec['t15'] = probe('t15')
time.sleep(max(0, 30.0 - (time.time() - t0)))
rec['t30'] = probe('t30')
board.shell('hilog -x > ' + remote + '/be-hilog.txt 2>&1; true')
board.receive(remote + '/be-hilog.txt', d / 'be-hilog.txt')
b.save(d / 'record.json', rec)
print('t15:', rec['t15'], '| t30:', rec['t30'], flush=True)
print('DONE', flush=True)
