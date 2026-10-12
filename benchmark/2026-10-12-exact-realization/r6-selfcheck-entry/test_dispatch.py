"""Offline shell dispatch checks; fake python3 never imports a collector or calls HDC."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WRAPPER = ROOT / 'scripts/lab/demo_selfcheck.sh'
ENTRY = ROOT / 'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py'


def main():
    before = (HERE / 'before.sh').read_bytes()
    after = WRAPPER.read_bytes()
    marker = b'exec python3 - "$SELF_DIR" "$@" <<\'PY\'\n'
    assert before.split(marker, 1)[1] == after.split(marker, 1)[1], 'legacy default body drift'
    syntax = subprocess.run(['/bin/bash', '-n', str(WRAPPER)], capture_output=True, text=True)
    assert syntax.returncode == 0, syntax.stderr
    common = ['--serial', 'offline-serial', '--boot-id', 'offline-boot', '--out', 'output with spaces.json']
    cases = [
        ('realization_split', 'realization', ['--realization', 'proof with spaces.json', *common, '--hdc', '/never/call/hdc']),
        ('realization_equal', 'realization', [*common, '--realization=proof.json', '--hdc=/never/call/hdc']),
        ('realization_offline', 'realization', ['--realization', 'proof.json', *common, '--observed', 'fixture.json']),
        ('activation_split', 'activation', ['--activation-binding', 'binding.json', '--binding-sha256', 'a' * 64, *common, '--hdc', '/never/call/hdc']),
        ('activation_equal', 'activation', [*common, '--activation-binding=binding.json', '--binding-sha256=' + 'a' * 64, '--hdc=/never/call/hdc']),
        ('activation_offline', 'activation', ['--activation-binding', 'binding.json', '--binding-sha256', 'a' * 64, *common, '--observed', 'fixture.json']),
        ('legacy_default', None, ['--seal', 'seal.json', '--serial', 'offline-serial']),
        ('legacy_offline', None, ['--seal', 'seal.json', '--serial', 'offline-serial', '--observed', 'fixture with spaces.json']),
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix='selfcheck-dispatch-') as temporary:
        fake = Path(temporary) / 'python3'
        fake.write_text('#!' + sys.executable + '\nimport json,sys\nprint(json.dumps({"argv":sys.argv[1:],"stdin":sys.stdin.read()}))\nsys.exit(23)\n')
        fake.chmod(0o755)
        env = {**os.environ, 'PATH': temporary + os.pathsep + os.environ.get('PATH', '')}
        for name, checker, args in cases:
            run = subprocess.run(['/bin/bash', str(WRAPPER), *args], env=env, input='', capture_output=True, text=True)
            assert run.returncode == 23, (name, run.stderr, run.returncode)
            actual = json.loads(run.stdout)
            if checker:
                assert Path(actual['argv'][0]).resolve() == ENTRY
                assert actual['argv'][1:] == ['--checker', checker, *args], (name, actual)
                assert actual['stdin'] == ''
            else:
                assert actual['argv'] == ['-', str(ROOT / 'scripts/lab'), *args], (name, actual)
                assert actual['stdin'].encode() == after.split(marker, 1)[1].rsplit(b'PY\n', 1)[0]
            results.append({'case': name, 'pass': True, 'fake_child_rc': 23, 'argv_tail': actual['argv'][1:] if checker else actual['argv'][2:]})
    print(json.dumps({'status': 'PASS', 'scope': 'OFFLINE_ARGV_AND_SHELL_ONLY', 'cases': results, 'bash_n_rc': syntax.returncode, 'legacy_body_byteequal': True, 'device_access': False}, indent=2))


if __name__ == '__main__':
    main()
