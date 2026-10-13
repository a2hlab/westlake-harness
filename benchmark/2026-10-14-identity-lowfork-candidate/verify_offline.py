"""Execute original/candidate metadata shells only against local fixtures."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import presence_reader_lowfork as candidate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROOF = ROOT.parent / 'westlake-harness-t0/benchmark/2026-10-14-final61b-next-binding/actual-running-086db6c7/identity128/identity/candidate-proof.json'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Base:
    pass


def run_reader(factory, files, directories, fixture, *, drift=False, stat_failure=False):
    inventory = {**files, **directories}
    commands, outputs, trace = [], [], fixture / 'trace.txt'
    trace.write_text('')
    cases = []
    for path, meta in inventory.items():
        fields = [str(meta[k]) for k in ['mode', 'uid', 'gid', 'label']]
        if drift:
            fields[1] = str(int(fields[1]) + 1)
        cases.append(shlex.quote(str(fixture) + path) + ') printf \'%s\\n\' ' +
                     shlex.quote(path + '|' + '|'.join(fields)) + ';;')
    stat = 'stat() { case "$3" in ' + ' '.join(cases) + ' *) return 17;; esac; }; '
    if stat_failure:
        stat = 'stat() { return 19; }; '
    # The real local shell performs each type/symlink test; retain its ordered
    # predicate trace separately. Only UID/GID/SELinux stat text is fixture data.
    guard = 'test() { printf \'%s|%s|%s\\n\' "$1" "${2-}" "${3-}" >> ' + shlex.quote(str(trace)) + '; builtin test "$@"; }; '

    class Local(factory(Base)):
        def _presence_read(self, name, command):
            commands.append(command)
            # Paths contain no whitespace/quotes; substitution affects only
            # the explicit inventory list, not the algorithm or guard code.
            local = command.replace('/system/', str(fixture) + '/system/').replace('/data/', str(fixture) + '/data/')
            proc = subprocess.run(['bash'], input=stat + guard + local,
                                  text=True, capture_output=True, timeout=60)
            if proc.returncode or proc.stderr:
                raise ValueError('presence transport/remote/permission failure')
            outputs.append(proc.stdout)
            return proc.stdout.strip()

    try:
        Local().verify_metadata(files, directories)
        outcome = 'accepted'
    except ValueError as exc:
        outcome = str(exc)
    return {'outcome': outcome, 'calls': len(commands), 'outputs': outputs,
            'trace': trace.read_text().replace(str(fixture), '$FIXTURE'),
            'command_sha256s': [hashlib.sha256(x.encode()).hexdigest() for x in commands]}


def main():
    proof = json.loads(PROOF.read_text())
    real_files, real_dirs = proof['presence_metadata'], proof['directory_metadata']
    rows = []
    with tempfile.TemporaryDirectory(prefix='identity-offline-') as tmp:
        fixture = Path(tmp).resolve()
        for p in real_dirs:
            (fixture / p.lstrip('/')).mkdir(parents=True, exist_ok=True)
        for p in real_files:
            q = fixture / p.lstrip('/'); q.parent.mkdir(parents=True, exist_ok=True); q.touch()
        meta = dict(mode='644', uid=0, gid=0, label='u:object_r:system_file:s0')
        testroot = fixture / 'data/offline-case'; testroot.mkdir()
        (testroot / 'file').touch(); (testroot / 'target-dir').mkdir()
        (testroot / 'target-dir/file').touch()
        (testroot / 'ancestor-link').symlink_to(testroot / 'target-dir', target_is_directory=True)
        (testroot / 'leaf-link').symlink_to(testroot / 'file')
        cases = [
            ('all_actual_507_files_5_directories', real_files, real_dirs, {}),
            ('duplicate_separator_dot', {'/data/offline-case//./file': meta}, {}, {}),
            ('ancestor_symlink', {'/data/offline-case/ancestor-link/file': meta}, {}, {}),
            ('leaf_symlink', {'/data/offline-case/leaf-link': meta}, {}, {}),
            ('missing', {'/data/offline-case/missing': meta}, {}, {}),
            ('wrong_type', {'/data/offline-case/target-dir': meta}, {}, {}),
            ('metadata_drift', {'/data/offline-case/file': meta}, {}, {'drift': True}),
            ('stat_error', {'/data/offline-case/file': meta}, {}, {'stat_failure': True}),
            ('root_rejected', {'/': meta}, {}, {}),
            ('dotdot_rejected', {'/data/offline-case/../file': meta}, {}, {}),
            ('unsafe_character_rejected', {'/data/offline-case/a b': meta}, {}, {}),
            ('trailing_slash_directory', {}, {'/data/offline-case/target-dir///': meta}, {}),
        ]
        for name, files, dirs, options in cases:
            old = run_reader(candidate.original.with_presence, files, dirs, fixture, **options)
            new = run_reader(candidate.with_presence, files, dirs, fixture, **options)
            assert {k: old[k] for k in ['outcome', 'calls', 'outputs', 'trace']} == {k: new[k] for k in ['outcome', 'calls', 'outputs', 'trace']}, name
            should_accept = name in {'all_actual_507_files_5_directories', 'duplicate_separator_dot', 'trailing_slash_directory'}
            assert (new['outcome'] == 'accepted') == should_accept, (name, new['outcome'])
            rows.append({'case': name, 'outcome': new['outcome'], 'calls': new['calls'],
                         'ordered_guard_trace_sha256': hashlib.sha256(new['trace'].encode()).hexdigest(),
                         'original_command_sha256s': old['command_sha256s'],
                         'candidate_command_sha256s': new['command_sha256s']})

    # Independently compare the parent calculation for all actual ancestors,
    # plus separator/root edge cases, using the local reference dirname.
    paths = set(real_files) | set(real_dirs) | {'/', '//', '///', '/a', '/a/', '/a//', '/a//b', '/a/./b', '/a//b///', '/data/.'}
    for path in list(paths):
        q = Path(path)
        while str(q) != '/' and q.parent != q:
            paths.add(str(q)); q = q.parent
    script = 'set -eu\n'
    for path in sorted(paths):
        script += 'walk=' + shlex.quote(path) + '\n' + candidate.PARENT_STEP + '\nprintf "%s\\n" "$walk"\n'
    got = subprocess.run(['bash'], input=script, capture_output=True, text=True, check=True).stdout.splitlines()
    expected = [subprocess.run(['dirname', p], text=True, capture_output=True, check=True).stdout.strip() for p in sorted(paths)]
    assert got == expected
    report = {'status': 'OFFLINE_EQUIVALENCE_PASS_DEVICE_UNMEASURED', 'device_calls': 0,
              'running_files_changed': False, 'performance_claim': None,
              'proof_sha256': digest(PROOF), 'original_sha256': candidate.ORIGINAL_SHA256,
              'candidate_sha256': digest(HERE / 'presence_reader_lowfork.py'),
              'test_sha256': digest(Path(__file__)), 'cases': rows,
              'parent_calculation_cases': len(paths),
              'limitations': ['Local Bash/filesystem only; actual OH shell equivalence and timing still require independent authorized new run.',
                             'Stat text is fixture metadata; real symlink/type/absence guards execute locally.',
                             'Original transport/decoder/parser inherited by exact pin, not reimplemented.',
                             'No current full128 pin, code, JSON, device or process changed.']}
    (HERE / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'cases': len(rows), 'parent_calculation_cases': len(paths)}))


if __name__ == '__main__':
    main()
