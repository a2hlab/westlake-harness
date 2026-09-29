#!/usr/bin/env python3
"""Compare linked candidates with the accepted #89 pair; retain raw evidence."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
baseline,candidate,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
def inspect(p,tag):
    dyn=subprocess.check_output(['llvm-readelf','-dW',str(p)],text=True)
    syms=subprocess.check_output(['llvm-readelf','--dyn-syms','-W',str(p)],text=True)
    (out/(tag+'.dynamic.txt')).write_text(dyn)
    (out/(tag+'.symbols.txt')).write_text(syms)
    exp=set();und=set()
    for line in syms.splitlines():
        x=line.split()
        if len(x)>=8 and x[0].rstrip(':').isdigit() and x[4] in ['GLOBAL','WEAK']:
            (und if x[6]=='UND' else exp).add(x[7])
    return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'dynamic':[l.split(')',1)[1].strip() for l in dyn.splitlines() if any('('+k+')' in l for k in ['NEEDED','SONAME','RUNPATH','RPATH','FLAGS','FLAGS_1'])],'exports':exp,'imports':und}
result={}
for n in ['libapk_installer.so','libbms.z.so']:
    a=inspect(baseline/n,n+'.baseline');b=inspect(candidate/n,n+'.candidate')
    result[n]={'baseline_sha':a['sha256'],'candidate_sha':b['sha256'],'dynamic_unchanged':a['dynamic']==b['dynamic'],'needed_soname_flags':b['dynamic'],'removed_exports':sorted(a['exports']-b['exports']),'added_exports':sorted(b['exports']-a['exports']),'added_imports':sorted(b['imports']-a['imports']),'removed_imports':sorted(a['imports']-b['imports'])}
(out/'elf-diff.json').write_text(json.dumps(result,indent=2)+'\n')
assert all(r['dynamic_unchanged'] and not r['removed_exports'] for r in result.values()),'ELF compatibility change requires review'
print(json.dumps({k:{x:v for x,v in r.items() if x not in ['needed_soname_flags','added_exports']} for k,r in result.items()},indent=2))
