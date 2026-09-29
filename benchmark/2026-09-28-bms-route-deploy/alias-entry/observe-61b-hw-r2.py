"""61b HelloWorld smoke under the B5-r2 overlay on the post-restore generation (B4 #38 step ②).

Adapts observe.py (5ea, lane cx-t0) to serial 61b / lane oc-t4.
Single case: helloworld — ordinary (non-alias) entry, so it proves the
overlay did not break the normal launch path. Screenshot paths+hash
only; no image reading (outer review owns visual verdicts)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'batch'))
import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b5r2-overlay-hw-smoke-61b-20260928T2245'
if not all(c.isalnum() or c in '-_' for c in RUN):
    raise ValueError('invalid run id')
out = Path.home() / 'a2hlab/board' / RUN
out.mkdir(parents=True, exist_ok=False)
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()
identity = ("cat /proc/sys/kernel/random/boot_id; sha256sum /system/android/framework/oh-adapter-runtime.jar; "
            "sha256sum /proc/$(pgrep -f 'appspawn-x --socket-name AppSpawnX' | sort -n | head -1)/root/system/android/framework/oh-adapter-runtime.jar; ps -A -o PID,PPID,UID,NAME")
_, before = board.shell(identity); (out / 'identity-before.txt').write_text(before)
key, pkg = 'helloworld', 'com.example.helloworld'
d = out / key; d.mkdir(); remote = '/data/local/tmp/' + RUN + '/' + key
board.shell('mkdir -p ' + remote)
_, bundle = board.shell('bm dump -n ' + pkg); (d / 'bundle.txt').write_text(bundle)
parsed = b.parse_bundle(bundle, pkg); uid = parsed['uid']
rec = {'key': key, 'package': pkg, 'serial': SERIAL, 'boot_id': board.boot, 'bms': parsed, 'started_at': __import__('time').time()}
if not b.cold_stop(board, pkg, uid, d):
    raise RuntimeError('cold stop not proven')
original = board.shell

def launch_hook(command, required=True, timeout=60):
    if command.startswith('uitest uiInput click '):
        script = f'''hilog -r > {remote}/hilog-clear.txt 2>&1
hilog > {remote}/hilog.txt 2>&1 &
hilog_pid=$!
(
 n=0
 while [ "$n" -lt 160 ]; do
  read up unused < /proc/uptime
  echo "T $up"
  ps -A -o PID,PPID,UID,NAME | while read p pp u name; do
   if [ "$u" = "{uid}" ]; then
    echo "P $p $pp $u $name"
   fi
  done
  n=$((n+1))
  sleep 0.1
 done
) > {remote}/timeline.txt 2>&1 &
sampler_pid=$!
cat /proc/uptime > {remote}/click-before.txt
{command}
cat /proc/uptime > {remote}/click-after.txt
sleep 3
snapshot_display -f {remote}/t3.jpeg > {remote}/snapshot3.txt 2>&1
sleep 12
snapshot_display -f {remote}/final.jpeg > {remote}/snapshot-final.txt 2>&1
kill "$sampler_pid" "$hilog_pid" 2>/dev/null
wait "$sampler_pid" "$hilog_pid" 2>/dev/null
true'''
        return original(script, required=required, timeout=65)
    return original(command, required=required, timeout=timeout)

board.shell = launch_hook
try:
    b.desktop_launch(board, {'package': pkg, 'launch_activity': parsed['desktop_activity']}, remote, d, rec)
finally:
    board.shell = original
for name in ['hilog-clear.txt', 'hilog.txt', 'timeline.txt', 'click-before.txt', 'click-after.txt',
             't3.jpeg', 'final.jpeg', 'snapshot3.txt', 'snapshot-final.txt']:
    board.receive(remote + '/' + name, d / name)
_, ps = board.shell('ps -A -o PID,PPID,UID,NAME'); (d / 'processes-after.txt').write_text(ps)
target = [r for r in b.processes(ps) if r['uid'] == uid]
rec['pids_after'] = [r['pid'] for r in target]
rec['finished_at'] = __import__('time').time()
b.save(d / 'record.json', rec)
b.save(out / 'results.json', {'serial': SERIAL, 'boot_id': board.boot, 'trials': [rec]})
print('smoke', key, 'pids_after=', rec['pids_after'])
print(out, flush=True)
