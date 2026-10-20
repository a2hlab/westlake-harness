#!/usr/bin/env python3
"""Verify real build receipts and outputs; missing evidence is an error."""
import argparse,json,hashlib,sys
from pathlib import Path
from build import BASE,OLD_AUDIO,compare_owner,HERE,T18
CANDIDATE='dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
    for name in ['production-01','production-02']:
        d=root/name;r=json.loads((d/'result.json').read_text())
        assert r['status']=='BUILT_PENDING_ABI_AND_INDEPENDENT_REVIEW'
        assert sha(d/'baseline.so')==BASE and sha(d/'candidate.so')==CANDIDATE
        for stage in ['frozen','baseline-link','baseline-compile','candidate-compile','candidate-link','baseline-elf','candidate-elf']:
            assert (d/(stage+'.rc')).read_text()=='0\n'
            assert (d/(stage+'.stdout')).is_file() and (d/(stage+'.stderr')).is_file()
        old=json.loads((d/'baseline-link.argv.json').read_text());new=json.loads((d/'candidate-link.argv.json').read_text())
        assert len(old)==len(new)
        delta=[i for i,(x,y) in enumerate(zip(old,new)) if x!=y]
        assert len(delta)==2 and old.index('-o')+1 in delta
        audio=next(i for i in delta if i!=old.index('-o')+1)
        assert old[audio].endswith('westlake_framework_core_jni_oh_audiotrack_shim.cpp.o') and new[audio]==str(d/'candidate-audio.o')
        assert sha(Path(old[audio]))==OLD_AUDIO
        assert compare_owner(Path(old[audio]),d/'baseline-audio.o')['all_other_bytes_equal']
        assert sha(d/'audiotrack_effective_size.inc')==sha(T18/'audiotrack_effective_size.inc')
        for path,rec in json.loads((d/'all-includes.json').read_text()).items():assert sha(Path(path))==rec['sha256']
    abi=json.loads((root/'production-01/abi.json').read_text())
    assert not any(abi[x] for x in ['removed','added','drift','consumer_breaks'])
    assert abi['old']['sha256']==BASE and abi['new']['sha256']==CANDIDATE
    assert (root/'production-01/abi.rc').read_text()=='0\n'
    needed=json.loads((root/'production-01/needed.json').read_text());assert needed['equal'] and needed['old']==needed['new'] and len(needed['old'])==42
    # Static call-set exception is reviewed separately; do not silently erase it.
    assert len(abi['call_diffs'])==1 and abi['call_diffs'][0]['added_callees']==['__CortexA53843419_D1004']
    return {'status':'STATIC_BUILD_EVIDENCE_VERIFIED_NOT_RUNTIME','runs':2,'candidate_sha256':CANDIDATE,'call_diff_exception':'documented A53 load/return thunk; independent review required'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw-root',type=Path,default=Path.home()/'.local/share/westlake/t18-production');a=p.parse_args()
    print(json.dumps(verify(a.raw_root)))
