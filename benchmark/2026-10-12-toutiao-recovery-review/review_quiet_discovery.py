import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile


OLD_COMMIT = 'ee50b0cd6ce8892d7f527ee656ab21c866817f1f'
OLD_HELPER = 'benchmark/2026-10-12-child-readiness/candidate/route-b-owner.sh'
OWNER_SHA = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'


def git_bytes(repository, commit, relative):
    return subprocess.check_output(['git', '-C', str(repository), 'show', commit + ':' + relative])


def statline(pid, birth, state='S'):
    return f'{pid} (recorded-field-fixture) {state} 4421 ' + ' '.join(['0'] * 17) + f' {birth} 0\n'


def exercise(source, inherited_quiet=False):
    with tempfile.TemporaryDirectory(prefix='bms-quiet-discovery-') as folder:
        root = Path(folder)
        proc = root / 'proc'
        runtime = root / 'runtime'
        runtime.mkdir()
        (runtime / 'run.sh').write_text('fixture inode source\n')
        for pid in range(100, 109):
            directory = proc / str(pid)
            directory.mkdir(parents=True)
            uid = '20011206'
            if pid == 101:
                uid = '0'
            elif pid == 102:
                uid = '20011300'
            fields = [uid] * 4
            if pid == 103:
                fields[2] = '0'
            if pid != 108:
                (directory / 'status').write_text('Uid:\t' + '\t'.join(fields) + '\n')
            (directory / 'stat').write_text(statline(pid, 1000 + pid, 'Z' if pid == 107 else 'S'))
            (directory / 'exe').symlink_to('/system/bin/appspawn-x' if pid == 104
                                         else '/data/local/tmp/asx/appspawn-x')
        helper = root / 'helper.sh'
        helper.write_bytes(source)
        script = '''
set -u
od(){ printf x >> "$OD_COUNT"; command od "$@"; }
sha256sum(){ printf x >> "$SHA_COUNT"; case "$1" in */105/exe) printf '%064d  %s\n' 0 "$1";; *) printf '%s  %s\n' "$EXPECTED_SHA" "$1";; esac; }
stat(){ printf x >> "$STAT_COUNT"; case "$*" in *106/root*) echo 1:2;; *) echo 66352:423310;; esac; }
kill(){ echo SIGNAL_FORBIDDEN >> "$FORBIDDEN"; return 99; }
rb_signal(){ echo SIGNAL_FORBIDDEN >> "$FORBIDDEN"; return 99; }
. "$HELPER"
rb_owned_pids > "$OWNED"
discovery_rc=$?
printf 'DISCOVERY_RC=%s\n' "$discovery_rc"
printf 'DISCOVERY_OD=%s\n' "$(wc -c < "$OD_COUNT")"
printf 'DISCOVERY_SHA=%s\n' "$(wc -c < "$SHA_COUNT")"
printf 'DISCOVERY_STAT=%s\n' "$(wc -c < "$STAT_COUNT")"
rb_owned 101
printf 'TARGET_RC=%s\n' "$?"
printf 'TOTAL_OD=%s\n' "$(wc -c < "$OD_COUNT")"
cat "$OWNED"
'''
        counts = {name: root / name.lower() for name in ('OD_COUNT', 'SHA_COUNT', 'STAT_COUNT')}
        for path in counts.values():
            path.write_bytes(b'')
        environment = dict(__import__('os').environ, RB_PROC=str(proc), RB_RUNTIME=str(runtime),
                           RB_OWNER_UID='20011206', EXPECTED_SHA=OWNER_SHA, HELPER=str(helper),
                           OWNED=str(root / 'owned'), FORBIDDEN=str(root / 'forbidden'),
                           **{name: str(path) for name, path in counts.items()})
        environment.pop('RB_AUDIT_QUIET', None)
        if inherited_quiet:
            environment['RB_AUDIT_QUIET'] = '1'
        result = subprocess.run(['bash', '-c', script], capture_output=True, text=True,
                                env=environment, timeout=10)
        assert result.returncode == 0, result.stderr
        assert not (root / 'forbidden').exists()
        metrics = {}
        for line in result.stdout.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                metrics[key] = int(value.strip())
        metrics['owned'] = (root / 'owned').read_text().splitlines()
        metrics['stderr'] = result.stderr
        metrics['target_diagnostics_after_discovery'] = metrics['TOTAL_OD'] - metrics['DISCOVERY_OD']
        return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--helper-relative', required=True)
    args = parser.parse_args()
    old_source = git_bytes(args.repository, OLD_COMMIT, OLD_HELPER)
    new_source = git_bytes(args.repository, args.commit, args.helper_relative)
    before, after = exercise(old_source), exercise(new_source)
    inherited = exercise(new_source, inherited_quiet=True)
    checks = {
        'same_owned_set': before['owned'] == after['owned'] == ['100'],
        'same_discovery_return': before['DISCOVERY_RC'] == after['DISCOVERY_RC'],
        'same_identity_sha_calls': before['DISCOVERY_SHA'] == after['DISCOVERY_SHA'],
        'same_identity_stat_calls': before['DISCOVERY_STAT'] == after['DISCOVERY_STAT'],
        'zero_discovery_od': after['DISCOVERY_OD'] == 0,
        'target_failure_diagnostics_retained': after['TARGET_RC'] != 0
            and after['target_diagnostics_after_discovery'] == before['target_diagnostics_after_discovery'] == 6,
        'inherited_quiet_cannot_suppress_target': inherited['target_diagnostics_after_discovery'] == 6,
    }
    print(json.dumps({'commit': args.commit, 'helper': args.helper_relative,
                      'helper_sha256': hashlib.sha256(new_source).hexdigest(),
                      'before': before, 'after': after, 'inherited_quiet': inherited, 'checks': checks,
                      'board_calls': 0, 'real_proc_timing_claim': False}, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
