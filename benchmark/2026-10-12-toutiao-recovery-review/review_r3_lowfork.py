#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


PREFIX = 'benchmark/2026-10-12-child-readiness'
BASE = '379d1a46de0c388e105157d455916d356c11028b'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def review(repository, commit, output):
    def gitfile(path, revision=commit):
        return subprocess.check_output(['git', '-C', str(repository), 'show', revision + ':' + path])

    folder = PREFIX + '/r3-lowfork-audit'
    checkpoint = json.loads(gitfile(folder + '/checkpoint-manifest.json'))
    checks = {}
    rows = []
    output.mkdir(parents=True, exist_ok=False)
    for row in checkpoint['files']:
        data = gitfile(folder + '/' + row['path'])
        assert sha(data) == row['sha256'] and len(data) == row['bytes'], row['path']
        target = output / 'frozen' / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    checks['checkpoint_rows'] = len(checkpoint['files'])
    for name in ('checkpoint-manifest.json', 'landing-paths.txt'):
        (output / 'frozen' / name).write_bytes(gitfile(folder + '/' + name))
    candidate = output / 'frozen/candidate'
    old_helper = gitfile(PREFIX + '/r2b-quiet-reset/candidate/route-b-owner.sh', BASE)
    current_helper = (candidate / 'route-b-owner.sh').read_bytes()
    def strip_emitter(data):
        start = data.index(b'rb_guard_json(){')
        end = data.index(b'\nrb_deny(){', start)
        return data[:start] + data[end:]
    assert strip_emitter(old_helper) == strip_emitter(current_helper)
    checks['identity_and_quiet_reset_unchanged'] = True
    prior_worker = gitfile(PREFIX + '/r2b-quiet-reset/candidate/readiness-probe.sh', BASE)
    replacement = b'   # Success must leave the 2-second envelope without diagnostic subprocesses.\n   # The caller still runs the final original complete child_owned guard.\n   exit 0;;'
    assert (candidate / 'readiness-probe.sh').read_bytes() == prior_worker.replace(b'   rb_guard_json readiness ready requires_final_original_child_owned || exit 5\n   exit 0;;', replacement)
    for name in ('watchdog.sh', 'launch-common.sh', 'compose.py'):
        relative = name if name == 'compose.py' else 'candidate/' + name
        assert gitfile(folder + '/' + relative) == gitfile(PREFIX + '/r2b-quiet-reset/' + relative, BASE)
    checks['worker_only_success_emitter_removed_and_caller_unchanged'] = True
    mapping = {'start-parent.sh': 'start-parent-prepared.sh', 'spawn.sh': 'spawn-prepared.sh', 'screen-gate': 'screen-gate-feed'}
    members = (candidate / 'members.tsv').read_text().splitlines()
    for line in members:
        digest, name, mode = line.split()
        local = candidate / name
        data = local.read_bytes() if local.exists() else gitfile('benchmark/2026-10-12-recovery-executor/payload/' + mapping.get(name, name))
        assert digest == sha(data), name
    startup = (candidate / 'startup.env').read_bytes()
    assert sha((candidate / 'members.tsv').read_bytes()).encode() in startup
    assert sha(startup) == (candidate / 'startup.expected.sha256').read_text().strip()
    assert sha(current_helper).encode() in (candidate / 'entry.sh').read_bytes()
    checks['boot_member_closure'] = len(members)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        old_path = root / 'old.sh'
        old_path.write_bytes(old_helper)
        script = 'RB_OWNER_UID=20011206; . "$1"; COUNT=$2; od(){ echo od >> "$COUNT"; command od "$@"; }; RB_AUDIT_PHASE=$3; RB_AUDIT_PID=$4; RB_AUDIT_BIRTH=$5; rb_guard_json "$6" "$7" "$8"'
        for values in (['readiness', '6243', '6558', 'uid', '0:0:0:0', '20011206'], ['', '', '', '', '', ''], ['x"\\\n\t', '1', '2', 'uid', 'quote"\\\n\t\x01', '']):
            decoded = []
            counts = []
            for index, helper in enumerate((old_path, candidate / 'route-b-owner.sh')):
                count = root / ('count-' + str(index))
                count.unlink(missing_ok=True)
                result = subprocess.run(['bash', '-c', script, 'fixture', str(helper), str(count), *values], capture_output=True, text=True)
                assert result.returncode == 0, result.stderr
                decoded.append(json.loads(result.stderr))
                counts.append(len(count.read_text().splitlines()))
            assert decoded[0] == decoded[1] and counts == [6, 1]
            rows.append({'kind': 'json_equivalence', 'counts': counts, 'decoded': decoded[1]})
        for fault in ('od(){ return 9; }', 'od(){ echo "61 00"; }', 'exec 2>/dev/null; exec 2>&-'):
            result = subprocess.run(['bash', '-c', 'RB_OWNER_UID=20011206; . "$1"; ' + fault + '; rb_guard_json uid actual expected', 'fixture', str(candidate / 'route-b-owner.sh')], capture_output=True, text=True)
            assert result.returncode != 0
            rows.append({'kind': 'encoder_error', 'fault': fault, 'exit': result.returncode})
    fixture = output / 'frozen/test_readiness.py'
    fixture.write_bytes(gitfile(PREFIX + '/test_readiness.py', 'ee50b0cd6ce8892d7f527ee656ab21c866817f1f'))
    spec = importlib.util.spec_from_file_location('r3_captured_fixture', fixture)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temporary:
        instrumented = Path(temporary)
        for name in ('route-b-owner.sh', 'readiness-probe.sh', 'watchdog.sh'):
            (instrumented / name).write_bytes((candidate / name).read_bytes())
        with (instrumented / 'route-b-owner.sh').open('a') as stream:
            stream.write('\nod(){ printf "UNEXPECTED_ENCODING\\n" >&2; return 9; }\n')
        module.C = instrumented
        result, decoded, elapsed = module.run_case({})
        assert result.returncode == 0 and decoded == [] and result.stderr == ''
        checks['actual_success_worker_zero_encoding'] = True
        rows.append({'kind': 'actual_success_worker_with_failing_od', 'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'desktop_seconds_not_OH_proof': elapsed})
    report = {'commit': commit, 'baseline': BASE, 'checks': checks, 'executed_cases': rows, 'offline_accept': True, 'whole_OH_worker_timing': 'pending', 'board_access': False, 'seal_accepted': False}
    (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    review(args.repository, args.commit, args.output)
