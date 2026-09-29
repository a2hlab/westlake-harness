"""#60 addendum: AbilityStage handshake evidence for fd-stk (bind-OK control).

Per outer #61 offline findings: 9 white-window apps attach+bind but never
receive ScheduleLaunchAbility; 8/9 later hit AppMS 'Add Ability Stage
TimeOut' (~30s after ScheduleLaunchApplication). This probe:
  1. launch fd-stk (bind-normal control) via desktop click
  2. at t+8 and t+30 capture: dumpcatcher main+all thread stacks
  3. continuous per-pid hilog window covering launch -> t+35, then scan for
     AppMS/AbilityMS AddAbilityStage request/response/timeout lines and
     ScheduleLaunchAbility markers
Control comparison: HelloWorld baseline has ScheduleLaunchAbility at ~66ms
after attach; if fd-stk never receives it and AppMS waits ~30s for the
AbilityStage-done reply, the handshake is the wall for bind-OK apps too.
"""
import json, sys, time, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b4-60-stk-handshake-61b-20260929T1445'
out = Path.home() / 'a2hlab/board' / RUN
out.mkdir(parents=True, exist_ok=False)
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()
manifest = {a['key']: a for a in json.load(open(ROOT / 'apps.json'))['apps']}
remote = '/data/local/tmp/' + RUN
board.shell('mkdir -p ' + remote)
app = manifest['fd-stk']

def uid_of(pkg):
    _, t = board.shell('bm dump -n ' + pkg)
    return b.parse_bundle(t, pkg)['uid']

def pids_of(uid):
    _, ps = board.shell('ps -A -o PID,PPID,UID,NAME')
    return {r['pid'] for r in b.processes(ps) if r['uid'] == uid}

uid = uid_of(app['package'])
d = out / 'fd-stk'
d.mkdir()
# remote per-key dir is REQUIRED before any uitest dumpLayout lands there
# (r5: DumpLayout failed 'No such file or directory' without it)
board.shell('mkdir -p ' + remote + '/fd-stk')
rec = {'key': 'fd-stk', 'package': app['package'], 'uid': uid, 'started_at': time.time()}
b.cold_stop(board, app['package'], uid, d)
b.prepare_sandbox(board, app['package'], uid, d)
_, bd = board.shell('bm dump -n ' + app['package'])
try:
    rec['desktop_activity'] = b.parse_bundle(bd, app['package']).get('desktop_activity') or app.get('launch_activity')
except Exception:
    rec['desktop_activity'] = app.get('launch_activity')
app_l = dict(app, launch_activity=rec['desktop_activity'])
# NO background hilog writer during launch: the continuous capture loads
# I/O and broke uitest dumpLayout in r1-r3; the proven pattern (white13_stack
# 13/13) is buffer-reset before launch + hilog -x dump at the end.
board.shell('hilog -r >/dev/null 2>&1; true')
# explicit unlock prelude: lock screen (SCBScreenLock10, focus 15) blocks
# dumpLayout and swallows clicks — wake, swipe up, Home, then verify desktop
for _ in range(3):
    board.shell('power-shell wakeup >/dev/null 2>&1; uitest uiInput swipe 600 1700 600 300 400; sleep 1; uitest uiInput keyEvent Home')
    import time as _t; _t.sleep(2)
    rc, wm = board.shell("hidumper -s WindowManagerService -a '-a'")
    import re as _re
    m = _re.search(r'^Focus window:\s*(\d+)', wm, _re.M)
    if m and m.group(1) == '11':
        rec['desktop_focus_verified'] = True
        break
else:
    rec['desktop_focus_verified'] = False

t0 = time.time()
for attempt in range(2):
    try:
        b.desktop_launch(board, app_l, remote + '/fd-stk', d, rec)
        rec['clicked'] = True
        break
    except Exception as e:
        rec['launch_error'] = repr(e)[:160]
        if attempt == 0:
            time.sleep(3)
            for stale in list(d.glob('settle-*.json')) + list(d.glob('icons--*.json')):
                stale.unlink(missing_ok=True)

def snap(tag):
    pids = pids_of(uid)
    if not pids:
        return {'pids': []}
    pid = min(pids)
    rc, dc = board.shell('dumpcatcher -p %d' % pid, required=False, timeout=90)
    (d / ('dumpcatcher-%s.txt' % tag)).write_text(dc)
    rc, wchan = board.shell(
        'for t in /proc/%d/task/*; do echo "== $(basename $t) $(cat $t/comm 2>/dev/null) wchan=$(cat $t/wchan 2>/dev/null)"; done' % pid,
        required=False, timeout=60)
    (d / ('wchan-%s.txt' % tag)).write_text(wchan)
    return {'pids': sorted(pids), 'probed_pid': pid}

time.sleep(max(0, 8.0 - (time.time() - t0)))
rec['t8'] = snap('t8')
time.sleep(max(0, 30.0 - (time.time() - t0)))
rec['t30'] = snap('t30')
time.sleep(max(0, 35.0 - (time.time() - t0)))
board.shell('hilog -x > ' + remote + '/stk-full-hilog.txt 2>&1; true')
board.receive(remote + '/stk-full-hilog.txt', d / 'stk-full-hilog.txt')

# offline-ish scan of the captured hilog for this pid
pid = rec['t30'].get('probed_pid') or rec['t8'].get('probed_pid')
hl = (d / 'stk-full-hilog.txt').read_text(errors='replace') if (d / 'stk-full-hilog.txt').is_file() else ''
pats = {
    'attachApplication': r'attachApplication',
    'ScheduleLaunchApplication': r'ScheduleLaunchApplication',
    'bindApplication': r'bindApplication|handleBindApplication',
    'ScheduleLaunchAbility': r'ScheduleLaunchAbility',
    'LaunchActivity': r'LaunchActivity',
    'AddAbilityStage_req': r'AddAbilityStage',
    'addAbilityStageDone': r'addAbilityStageDone|AbilityStageDone',
    'ams_timeout': r'Add Ability Stage TimeOut|Start Process Specified Ability TimeOut',
    'specified_ability': r'SpecifiedAbility|specified ability',
}
markers = {}
for name, rx in pats.items():
    hits = [ln.strip()[:240] for ln in hl.splitlines() if re.search(rx, ln)]
    markers[name] = {'count': len(hits), 'first': hits[:2], 'last': hits[-2:]}
if pid:
    pidlines = [ln.strip()[:240] for ln in hl.splitlines() if re.search(r'\b%d\b' % pid, ln)]
    markers['_pid_lines'] = len(pidlines)
    markers['_pid_ams'] = [ln for ln in pidlines if re.search(r'AddAbilityStage|TimeOut|ScheduleLaunch|AppMS|AbilityMS', ln)][:12]
rec['markers'] = markers
rec['finished_at'] = time.time()
b.save(d / 'record.json', rec)
b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'trials': [rec]})
print(json.dumps({k: (v['count'] if isinstance(v, dict) and 'count' in v else v) for k, v in markers.items() if not k.startswith('_')}, indent=1))
print('_pid_lines:', markers.get('_pid_lines'), '| pid_ams hits:', len(markers.get('_pid_ams') or []))
print('t8:', rec['t8'], '| t30:', rec['t30'])
print('DONE', flush=True)
