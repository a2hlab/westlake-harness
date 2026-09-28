"""B6 task 37: no admission or UI claim before a matched source generation exists."""
import json,re,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent
d=json.loads((r/'results.json').read_text())
def accepts(actual,expected,source_matched):
    return bool(source_matched and actual and expected and
        all(re.fullmatch('[0-9a-f]{64}',expected.get(k) or '') and actual.get(k)==expected[k]
            for k in ('libsigchain','child','host')) and actual.get('mapped_new_sigchain') is True)
which=sys.argv[1]
if which in ('caller','symbols'):
    subprocess.run([sys.executable,str(r.parent/'native-generation-hw248/verify.py'),which],check=True)
elif which=='negative':
    # Exercise the deployed-artifact check with all three mismatches and missing proof.
    expected={'libsigchain':d['sigchain_sha256'],'child':'a'*64,'host':'b'*64}
    actual=dict(expected,mapped_new_sigchain=True)
    assert accepts(actual,expected,True)
    for key in expected:
        bad=dict(actual);bad[key]='c'*64;assert not accepts(bad,expected,True)
    assert not accepts(actual,expected,False)
    assert not accepts(actual,dict(expected,child=None),True)
    assert not accepts(dict(actual,mapped_new_sigchain=False),expected,True)
    assert not accepts(None,expected,True)
    assert not accepts(d['child_proof'],d['candidate_identity'],d['source_matched'])
    assert d['lit_delta']==0 and not d['deployed']
elif which=='identity':
    assert d['identity_gate_passed'] and accepts(d['child_proof'],d['candidate_identity'],d['source_matched']),'no deployable matched generation; WLCGATE and child maps not collected'
elif which=='wikipedia':
    assert d['wikipedia_retested'] and d.get('wikipedia_own_ui_signed',False),'Wikipedia not retested'
elif which=='regression':
    assert d['quick_accepted'],'candidate not deployed; prior baseline UI is not candidate validation'
elif which=='null':
    assert d['npe_retested'] and d['null_check_mode']=='npe','no repaired-generation NPE evidence'
elif which=='nextwall':
    assert d['status']=='advanced','source mismatch is not advancement past getTheme'
else:raise ValueError(which)
print(which+': passed')
