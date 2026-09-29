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
rows={}
for key,old,new in [('host',base/'payload/appspawn-x',w/'host/appspawn-x-1'),('anl',base/'payload/route/libapp_native_loader.so',w/'anl-build/pass1/app-loader/libapp_native_loader.so'),('runtime',base/'payload/android/lib64/liboh_android_runtime.so',w/'runtime-out/liboh_android_runtime.so')]:
 if not old.exists() and key=='host':old=next(base.glob('payload/**/appspawn-x'))
 a,b=audit(old),audit(new);rows[key]={'old':a,'new':b,'added_imports':sorted(set(b['imports'])-set(a['imports'])),'removed_imports':sorted(set(a['imports'])-set(b['imports']))}
 assert a['needed']==b['needed'] and a['soname']==b['soname'],key
 assert a['exports']==b['exports'],key
(r/'elf-audit.json').write_text(json.dumps(rows,indent=2)+'\n');print({k:{'sha':v['new']['sha256'],'added_imports':v['added_imports']} for k,v in rows.items()})
