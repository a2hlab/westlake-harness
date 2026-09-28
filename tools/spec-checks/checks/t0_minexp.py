"""Offline regression checks; synthetic log input is not board evidence."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'benchmark/2026-09-27-app-breadth-sweep/scripts/t0_collect.py'


def check(namespace):
    raw = '\n'.join([
        '100.500 42 42 E APP: Error relocating libdemo.so: symbol not found',
        '100.600 43 43 F APP: Fatal signal 11',
        '100.700 42 42 E HDC_LOG: ExecuteCommand Error relocating libdemo.so',
        '99.500 42 42 E APP: Fatal signal 11',
        '102.500 42 42 E APP: Fatal signal 11',
    ])
    actual = namespace['filter_hilog'](raw, 42, 100, 101)
    assert actual == raw.splitlines()[0] + '\n', repr(actual)


sys.path.insert(0, str(SOURCE.parent))

def load(source):
    namespace = {'__name__': 't0_under_test'}
    exec(compile(source, str(SOURCE), 'exec'), namespace)
    return namespace


source = SOURCE.read_text()
check(load(source))
# Bind this test run to the actual failed attempt without treating it as a log capture.
evidence = ROOT / 'benchmark/2026-09-28-blocker-triage/evidence'
assert 'Installed host differs from the signed source payload' in (evidence / 'probe-failure.txt').read_text()
assert json.loads((evidence / 'attempt-original.json').read_text())['status'] == 'interrupted'
if sys.argv[1] == 'negative':
    for before, after in [('int(m[2]) == pid', 'True'), ('start <= float(m[1]) <= end', 'True')]:
        assert before in source
        try:
            check(load(source.replace(before, after)))
        except AssertionError:
            print('DETECTED real production mutation:', before, '->', after)
        else:
            raise AssertionError('mutation escaped: ' + before)
print('PASS', sys.argv[1], '(offline synthetic filter test; no board crash capture claimed)')
