"""#38 ②: redeploy the B5 alias JAR after the 21:12 reboot.

Differences from deploy-61b.py (#32): the pre-reboot baseline assertion no
longer holds — the partition file now reads 06141543… (neither the pinned
baseline 9161b507… nor B5 output 250958dc…; provenance unknown, recorded).
mount --bind does not touch the partition file, so the deploy is reversible
(umount restores 06141543…). We back the current file up first and assert on
the OUTPUT hash only, in shell and AppSpawnX /proc/<pid>/root.
"""
from pathlib import Path
import json, sys
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parent / 'batch')); import bms_batch as b

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
out = Path.home() / 'a2hlab/board/b5-alias-deploy-61b-r38'; out.mkdir(exist_ok=False)
build = json.loads((root / 'build-result.json').read_text())
board = b.Board(SERIAL, '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh',
                'mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh', LANE, out / 'commands')
board.ready()

target = '/system/android/framework/oh-adapter-runtime.jar'
remote = '/data/local/tmp/b5-alias-r38'
_, before = board.shell('sha256sum ' + target)
cur = before.split()[0]
print('current partition hash:', cur[:8], '(expected-unknown)')
assert cur not in (build['baseline_sha256'], build['output_sha256']), \
    'partition file unexpectedly matches a known hash: ' + cur
board.receive(target, out / 'pre-reboot-partition-06141543.jar')
assert b.sha(out / 'pre-reboot-partition-06141543.jar') == cur
_, mounts = board.shell('cat /proc/self/mountinfo'); (out / 'mountinfo-before.txt').write_text(mounts)
assert 'oh-adapter-runtime' not in mounts, 'a bind mount is already stacked'

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
rollback = 'umount ' + target + '; sha256sum ' + target + '   # restores partition hash ' + cur
(out / 'rollback.txt').write_text(rollback + '\n')
receipt = {'serial': board.serial, 'boot_id': board.boot, 'appspawn_x_pid': appspawn,
           'before_unknown_partition': cur, 'after': after, 'build': build, 'rollback': rollback,
           'partition_backup': str(out / 'pre-reboot-partition-06141543.jar'),
           'note': 'partition file at deploy time was neither pinned baseline nor B5 output; '
                   'provenance unknown, backed up, left for outer-loop adjudication'}
(root / 'deployment-61b-r38.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('B5 overlay verified in shell and AppSpawnX(%d) root; partition backup saved' % appspawn)
