"""Task 39 gates: a host build probe cannot stand in for target admission."""
import json
import re
import subprocess
import sys
from pathlib import Path
r = Path(__file__).resolve().parent
d = json.loads((r / 'results.json').read_text())

def accepts(actual, expected, complete):
    return bool(complete and actual and expected and all(
        re.fullmatch('[0-9a-f]{64}', expected.get(k) or '')
        and actual.get(k) == expected[k]
        for k in ('libsigchain', 'child', 'host'))
        and actual.get('mapped_new_sigchain') is True)

which = sys.argv[1]
if which == 'caller':
    subprocess.run([sys.executable, str(r.parent / 'sigchain-bridge/verify.py'), 'caller'], check=True)
elif which == 'negative':
    expected = {'libsigchain': d['sigchain_sha256'], 'child': 'a' * 64, 'host': 'b' * 64}
    actual = dict(expected, mapped_new_sigchain=True)
    assert accepts(actual, expected, True)
    for key in expected:
        assert not accepts(dict(actual, **{key: 'c' * 64}), expected, True)
    assert not accepts(dict(actual, mapped_new_sigchain=False), expected, True)
    assert not accepts(actual, expected, False)
    assert not accepts(None, expected, True)
    assert not accepts(d['child_proof'], d['candidate_identity'], d['build']['whole_generation_built'])
    assert d['lit_delta'] == 0 and not d['deployed']
elif which == 'symbols':
    assert d['new_art_built'] and d['symbol_coverage_against_new_art'], 'No new ART; old ART coverage is not new-generation coverage'
elif which == 'identity':
    assert d['identity_gate_passed'] and accepts(d['child_proof'], d['candidate_identity'], d['build']['whole_generation_built']), 'No admitted whole generation or child mapping proof'
elif which == 'wikipedia':
    assert d['wikipedia_retested'] and d.get('wikipedia_own_ui_signed', False), 'Wikipedia not retested'
elif which == 'regression':
    assert d['quick_accepted'] and not d['regressions'], 'No candidate HelloWorld/ZigZag quick acceptance'
elif which == 'null':
    assert d['npe_retested'] and d['null_check_mode'] == 'npe', 'No repaired-generation NPE evidence'
elif which == 'nextwall':
    assert d['status'] == 'advanced', 'Host input blocker is not advancement past getTheme'
else:
    raise ValueError(which)
print(which + ': passed')
