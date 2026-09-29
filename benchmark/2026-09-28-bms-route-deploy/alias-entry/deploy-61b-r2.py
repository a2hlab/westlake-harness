"""VM-only locked JAR overlay for 61b (B4 #38 r2): rebuild of the B5 alias merge on the post-restore baseline (06141543…). Adapts deploy.py (5ea):
- serial 61b0657200000000000000000324012c, lane oc-t4
- AppSpawnX PID discovered at runtime (5ea's 13161 is not portable)
- receipts under ~/a2hlab/board/b5-alias-deploy-61b-r2
Same pinned-baseline assert, same rollback (umount + hash verify)."""
from pathlib import Path
import json, sys
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parent / 'batch')); import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
out = Path.home() / "a2hlab" / "board" / "b5-alias-deploy-61b-r2"; out.parent.mkdir(parents=True, exist_ok=True); out.mkdir(exist_ok=False)
build = json.loads((root / 'build-result-r2.json').read_text())
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()

target = '/system/android/framework/oh-adapter-runtime.jar'
remote = '/data/local/tmp/b5-alias-r2-20260928-61b'
_, before = board.shell('sha256sum ' + target)
assert before.split()[0] == build['baseline_sha256'], '61b baseline differs from pinned: ' + before
board.receive(target, out / 'baseline.jar')
assert b.sha(out / 'baseline.jar') == build['baseline_sha256']
_, mounts = board.shell('cat /proc/self/mountinfo'); (out / 'mountinfo-before.txt').write_text(mounts)

# AppSpawnX main process (root, parent 1) — the process whose classloader serves app JARs.
rc, pids = board.shell("pgrep -f 'appspawn-x --socket-name AppSpawnX'")
assert rc == 0 and pids.strip(), pids
appspawn = sorted(int(p) for p in pids.split())[0]

board.shell('mkdir -p ' + remote); board.send(build['output'], remote + '/oh-adapter-runtime.jar')
_, check = board.shell('sha256sum ' + remote + '/oh-adapter-runtime.jar')
assert check.split()[0] == build['output_sha256'], check
board.shell('chmod 0644 ' + remote + '/oh-adapter-runtime.jar; chcon u:object_r:system_file:s0 ' +
            remote + '/oh-adapter-runtime.jar; mount --bind ' + remote + '/oh-adapter-runtime.jar ' + target)
_, after = board.shell('sha256sum ' + target + ' /proc/%d/root%s' % (appspawn, target))
lines = after.splitlines()
assert len(lines) == 2 and all(l.split()[0] == build['output_sha256'] for l in lines), after
rollback = 'umount ' + target + '; sha256sum ' + target
(out / 'rollback.txt').write_text(rollback + '\n')
receipt = {'serial': board.serial, 'boot_id': board.boot, 'appspawn_x_pid': appspawn,
           'before': before, 'after': after, 'build': build, 'rollback': rollback,
           'original_backup': str(out / 'baseline.jar'), 'vm_evidence': str(out)}
(root / 'deployment-61b-r2.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('61b overlay verified in shell and AppSpawnX(%d) root' % appspawn)
