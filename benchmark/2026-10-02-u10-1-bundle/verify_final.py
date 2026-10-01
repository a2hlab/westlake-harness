"""Audit the assembled payload bytes, including all ELF consumers and readonly data."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
W = Path(os.environ.get('WORKSPACES', REPO.parent)).resolve()
MASTER = W / 'westlake-harness'
DONOR = W / 'westlake-harness-bms/benchmark/2026-10-01-u10-native-shims'
sys.path.insert(0, str(DONOR / 'host-r3'))
sys.path.insert(1, str(DONOR))
from readonly import normalized_relro, rodata_strings
import host_gate
import policy_gate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    return value.replace(str(W), '$WORKSPACES')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    native = args.bundle / 'native'
    base = W / 'westlake-generation-u9-j10g-238ffc14/native'
    llvm = Path('/opt/homebrew/opt/llvm/bin')
    env = dict(os.environ, PATH=str(llvm) + os.pathsep + os.environ.get('PATH', ''))
    components = {'host': ('payload/runtime/appspawn-x', host_gate.validate),
                  'policy': ('payload/route/libnativeloader.so', policy_gate.validate),
                  'compat': ('payload/route/libbionic_compat.so', None)}
    exports = {}

    def symbols(path, defined):
        rows = subprocess.check_output([str(llvm / 'llvm-nm'), '-D', '--defined-only' if defined else '--undefined-only', '--format=just-symbols', str(path)], text=True)
        return {name.split('@')[0] for name in rows.splitlines()}

    for name, (relative, _) in components.items():
        exports[name] = symbols(base / relative, True)
    consumers = {name: [] for name in components}
    scanned = 0
    seen = set()
    for path in sorted((native / 'payload').rglob('*.so')):
        if not path.is_file() or path.is_symlink():
            continue
        scanned += 1
        digest = sha(path)
        if digest in seen:
            continue
        seen.add(digest)
        imports = symbols(path, False)
        for name in components:
            required = sorted(imports & exports[name])
            if required:
                consumers[name].append({'path': str(path), 'sha256': digest, 'required': required})
    # Replay the twelve archived, exact app DSO consumers; no APK substitution.
    pinned = REPO / 'benchmark/2026-10-01-u10-bundle/consumer-replay.json'
    consumer_root = W / 'westlake-inputs/generations/u10-j37465d6d-c015aa3a6-p621caec4-v3/build/pinned-consumers'
    pinned_rows = json.loads(pinned.read_text())['consumers']
    for row in pinned_rows:
        path = consumer_root / row['file']
        assert sha(path) == row['sha256']
        consumers['compat'].append(dict(row, path=str(path)))
    reports = {}
    for name, (relative, validator) in components.items():
        old, new = base / relative, native / relative
        output = args.out / (name + '-abi.json')
        command = ['python3', str(MASTER / 'scripts/lab/abi_diff.py'), '--old', str(old), '--new', str(new), '--calls', '--json', str(output)]
        for row in consumers[name]:
            command += ['--consumer', row['path']]
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        (args.out / (name + '-abi.txt')).write_text(portable(result.stdout + result.stderr))
        assert result.returncode == 0, name + ' ABI/call/consumer gate'
        report = json.loads(output.read_text())
        if validator:
            validator(report, True)
        else:
            assert not report['removed'] and not report['drift'] and not report['consumer_breaks'] and not report['call_diffs']
        reports[name] = report
        dynamic = subprocess.check_output([str(llvm / 'llvm-readelf'), '-d', str(new)], text=True)
        (args.out / (name + '-dynamic.txt')).write_text(dynamic)
        output.write_text(portable(json.dumps(report, indent=2)) + '\n')

    old_host, new_host = base / components['host'][0], native / components['host'][0]
    donor_report = json.loads((DONOR / 'evidence/recovery/results.json').read_text())
    readonly = donor_report['host_readonly']
    expand = lambda x: x.replace('$REPO', str(W / 'westlake-harness-bms')).replace('$WORKSPACES', str(W))
    assert normalized_relro(old_host) == normalized_relro(new_host) == readonly['relro']
    before, after = rodata_strings(old_host), rodata_strings(new_host)
    assert before - after == {expand(v) for v in readonly['rodata_dropped']}
    assert after - before == {expand(v) for v in readonly['rodata_added']}
    raw_exits = {}
    for name, (relative, _) in components.items():
        command = ['python3', str(MASTER / 'scripts/lab/deployed_strings_diff.py'), str(native / relative), '--deployed', str(base / relative)]
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        raw_exits[name] = result.returncode
        (args.out / (name + '-strings-raw.txt')).write_text(portable(result.stdout + result.stderr))
        assert result.returncode == 1, 'preserve raw delta evidence: ' + name
        if name == 'policy':
            allowed = ['--allow-add', 'libstdc++.so']
        elif name == 'host':
            module_spec = importlib.util.spec_from_file_location('strings_tool', MASTER / 'scripts/lab/deployed_strings_diff.py')
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)
            before, after = module.strings(base / relative), module.strings(native / relative)
            allowed = ['--allow-add', *sorted(after - before), '--allow-drop', *sorted(before - after)]
        else:
            allowed = ['--allow-add', '__gnu_strerror_r', 'android_dlopen_ext',
                       '[U10-DLEXT] backend absent; refusing extension flags=0x%lx file=%s.']
        reviewed = subprocess.run(command + allowed, capture_output=True, text=True, env=env)
        (args.out / (name + '-strings-reviewed.txt')).write_text(portable(reviewed.stdout + reviewed.stderr))
        assert reviewed.returncode == 0, name + ' exact string allowance'
    policy_root = W / 'westlake-inputs/generations/u10.1-policy-repro'
    baseline_policy = policy_root / 'fb9dc937-repro/libnativeloader.so'
    assert baseline_policy.read_bytes() == (base / components['policy'][0]).read_bytes()
    import verify as donor_verify
    policy = donor_verify.validate_policy_sources(W / 'westlake-harness-bms-deploy/benchmark/2026-09-30-n1-native/native-loader', policy_root / 'native-loader-u10.1')
    assert policy['system_libraries'][0]['soname'] == 'libsoundpool.so'
    report = {'status': 'PASS', 'scope': 'assembled final ELF bytes, not source tests',
              'scanned_payload_copies': scanned, 'unique_payload_elves': len(seen),
              'consumers': consumers, 'app_consumer_members_verified': len(pinned_rows),
              'system_libraries': policy['system_libraries'], 'shared_sonames': policy['shared_sonames'],
              'policy_baseline_byte_identical': True, 'raw_string_exits': raw_exits,
              'readonly': readonly, 'artifacts': {name: sha(native / row[0]) for name, row in components.items()},
              'board_touched': False, 'runtime_namespace_acceptance': 'unverified until approved window'}
    (args.out / 'results.json').write_text(portable(json.dumps(report, indent=2)) + '\n')
    print(json.dumps({'status': 'PASS', 'consumers': {name: len(rows) for name, rows in consumers.items()}, 'raw_string_exits': raw_exits}))


if __name__ == '__main__':
    main()
