#!/usr/bin/env python3
import hashlib,json,re,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent;repo=r.parents[1];w=repo/'bms/src/.work/v3c-next4-native';base=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next3-audio-anl')
readelf=repo/'bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf'
def audit(p):
 d=subprocess.check_output([str(readelf),'-d',str(p)],text=True);s=subprocess.check_output([str(readelf),'--dyn-syms','--wide',str(p)],text=True)
 imports=[];exports=[]
 for line in s.splitlines():
  q=line.split()
  if len(q)>=8 and q[0].endswith(':') and q[4] in ['GLOBAL','WEAK']:
   (imports if q[6]=='UND' else exports).append(q[7])
 return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'needed':re.findall(r'\(NEEDED\).*\[(.*?)\]',d),'soname':re.findall(r'\(SONAME\).*\[(.*?)\]',d),'imports':sorted(set(imports)),'exports':sorted(set(exports))}
base=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate')
a=audit(repo/'bms/src/.work/b91-common-event/runtime-out/liboh_android_runtime.so')
assert a['sha256'].startswith('9e14bf20')
b=audit(repo/'bms/src/.work/b12-graphics/runtime-out/liboh_android_runtime.so')
rows={'old':a,'new':b,'added_imports':sorted(set(b['imports'])-set(a['imports'])), 'removed_exports':sorted(set(a['exports'])-set(b['exports']))}
assert a['needed']==b['needed'] and a['soname']==b['soname']
assert not rows['removed_exports']
assert not rows['added_imports'],rows['added_imports']
(r/'elf-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
print({'sha':b['sha256'],'needed_count':len(b['needed']),'added_imports':rows['added_imports'],'removed_exports':rows['removed_exports']})
