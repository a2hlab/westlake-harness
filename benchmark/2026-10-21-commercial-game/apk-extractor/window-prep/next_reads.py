#!/usr/bin/env python3
"""Offline argv renderer: complete process maps and existing init declarations."""
import json
import shlex
from fresh_argv import SERIAL

BOOT = 'a1d869b4-69a2-40a4-937e-4860f5b54239'
READS = [
 ('boot-before', 'cat /proc/sys/kernel/random/boot_id', 15),
 ('processes-before', 'ps -A -o PID,PPID,UID,NAME', 15),
 ('all-process-maps', '''n=0; failed=0; for d in /proc/[0-9]*; do
 n=$((n+1)); if [ "$n" -gt 1024 ]; then echo LIMIT_EXCEEDED; exit 3; fi
 echo "BEGIN_PROC $d";
 cat "$d/stat"; r=$?; echo "STAT_BEFORE_RC=$r"; [ "$r" -eq 0 ] || failed=1
 cat "$d/maps"; r=$?; echo "MAPS_RC=$r"; [ "$r" -eq 0 ] || failed=1
 cat "$d/stat"; r=$?; echo "STAT_AFTER_RC=$r"; [ "$r" -eq 0 ] || failed=1
 echo "END_PROC $d"
 done; echo "PROC_COUNT=$n"; exit "$failed"''', 45),
 ('processes-after', 'ps -A -o PID,PPID,UID,NAME', 15),
 ('init-declarations', '''n=0; found=0; for root in /system/etc/init /vendor/etc/init /chipset/etc/init; do
 echo "INIT_ROOT $root"; if [ ! -d "$root" ]; then echo ROOT_ABSENT; continue; fi
 for f in "$root"/*.cfg; do
 [ -f "$f" ] || continue; n=$((n+1)); [ "$n" -le 400 ] || { echo LIMIT_EXCEEDED; exit 3; }
 grep -E 'installs|libinstalls|foundation|appspawn|westlake.*recover' "$f" >/dev/null; r=$?
 [ "$r" -le 1 ] || exit "$r"
 if [ "$r" -eq 0 ]; then found=$((found+1)); echo "BEGIN_CONFIG $f"; sha256sum "$f" || exit; cat "$f" || exit; echo "END_CONFIG $f"; fi
 done; done; echo "SCANNED=$n MATCHED=$found"; [ "$found" -gt 0 ]''', 30),
 ('init-mountinfo', 'cat /proc/1/mountinfo', 15),
 ('six-installer-aliases', 'sha256sum ' + ' '.join(d+'/'+n for d in ['/system/lib64','/system/lib64/platformsdk'] for n in ['libbms.z.so','libapk_installer.so','libinstalls.z.so']), 15),
 ('boot-after', 'cat /proc/sys/kernel/random/boot_id', 15),
]

def render():
    commands = []
    for tag, shell, seconds in READS:
        wrapped = 'sh -c ' + shlex.quote(shell) + '; r=$?; printf "\\n__REMOTE_RC=%s\\n" "$r"'
        commands.append(dict(id=tag, argv=['$HDC','-t',SERIAL,'shell',wrapped], timeout_seconds=seconds))
    return dict(schema='g12-next-readonly-argv/v1', executed=False, serial=SERIAL,
                expected_boot=BOOT, source='fresh-review.json; scripts/lab/board_state_snapshot.py:19',
                instructions=[
                    'Outer executes serially, saves untruncated raw stdout/stderr/argv/times and both rc; no retry on timeout/refusal.',
                    'Complete maps are intentionally captured regardless of process NAME; unreadable/exited/PID-reused entries are coverage gaps, not empty.',
                    'Parse stat starttime robustly after final close parenthesis; compare before/after and process-set changes. Lock-time repeat is required before replacement.',
                    'Config scan is limited to existing top-level cfg in repository-defined init roots. Missing declaration/import/profile remains unknown; read only exact paths discovered in config next.',
                    'Do not start a service to discover it. On-demand requires explicit declaration plus referenced SA profile, not absence of a NAME.',
                    'For each libinstalls maps hit, generate fresh_argv.py --pid OBSERVED_PID, then verify boot/birth/exe/dev/inode/process-root SHA.',
                    'No consumers + proven on-demand permits locked replacement without foundation stop. Live consumers require separately bound exact service action.',
                    'These reads do not establish complete current runtime or recovery; bind fresh generation inventory and recovery inputs separately.'
                ], commands=commands)
if __name__ == '__main__':
    print(json.dumps(render(),indent=2))
