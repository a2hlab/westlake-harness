#!/usr/bin/env python3
"""Offline exact ABC replay, then minimal Index candidate. No device operation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); here=Path(__file__).resolve().parent
    lock=json.loads((here/'inputs.lock.json').read_text())
    assert sha(a.compiler)==lock['compiler_sha256'],'EXACT_COMPILER_SHA'
    for n,h in lock['sources'].items(): assert sha(here/n)==h, n
    out=a.out.resolve(); out.mkdir(parents=True,exist_ok=False); (out/'raw').mkdir()
    receipt={'status':'INCOMPLETE','compiler':{'sha256':sha(a.compiler),'path':str(a.compiler.resolve())},'source_pins':lock['sources'],'commands':[],'artifacts':{}}
    def save(): (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    for phase,n in [('baseline','EntryAbility'),('baseline','Index'),('candidate','Index')]:
        dest=out/phase;dest.mkdir(exist_ok=True);tag=phase+'-'+n
        argv=[str(a.compiler.resolve()),'--target-api-version=20','--output='+str(dest/(n+'.abc')),n+'.js']
        cwd=here/'sources'/phase
        (out/'raw'/f'{tag}.argv.json').write_text(json.dumps({'argv':argv,'cwd':str(cwd)},indent=2)+'\n')
        with (out/'raw'/f'{tag}.stdout').open('wb') as stdout,(out/'raw'/f'{tag}.stderr').open('wb') as stderr:
            r=subprocess.run(argv,cwd=cwd,stdout=stdout,stderr=stderr)
        (out/'raw'/f'{tag}.rc').write_text(str(r.returncode)+'\n')
        receipt['commands'].append({'tag':tag,'rc':r.returncode});save()
        assert r.returncode==0,tag
        digest=sha(dest/(n+'.abc'))
        receipt['artifacts'][f'{phase}/{n}.abc']={'sha256':digest,'bytes':(dest/(n+'.abc')).stat().st_size};save()
        if phase=='baseline':
            member='ets/'+('entryability' if n=='EntryAbility' else 'pages')+'/'+n+'.abc'
            assert digest==lock['original_hap']['members'][member], 'BASELINE_ABC_MISMATCH '+n
    receipt['raw_pins']={str(f.relative_to(out)):sha(f) for f in sorted((out/'raw').iterdir())}
    receipt['status']='EXACT_BASELINE_AND_CANDIDATE_COMPILED';save()
    print(json.dumps(receipt,indent=2))
if __name__=='__main__': main()
