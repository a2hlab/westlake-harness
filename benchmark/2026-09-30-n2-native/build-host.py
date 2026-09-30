#!/usr/bin/env python3
import hashlib,json,os,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent; repo=r.parents[1]
frozen=repo/'bms/src/.work/b68-generation';out=repo/'bms/src/.work/n2-native/host';out.mkdir(parents=True,exist_ok=True)
x=json.loads((r/'host-commands.json').read_text());os.environ['LD_LIBRARY_PATH']=str(frozen/'.work/product-tls-generation/frozen/toolchain/runtime')
for n in (1,2):
 c=list(x['compile']); c[c.index('-c')+1]=str(r/'src/westlake_stock_host_main.c'); c[c.index('-o')+1]=str(out/f'host-{n}.o'); c+=['-I'+str(repo/'bms/src/adapter/framework/app-native-loader/src')]
 subprocess.run(c,cwd=frozen,check=True)
 c=list(x['link']);c[c.index('-o')+1]=str(out/f'appspawn-x-{n}')
 c=[str(out/f'host-{n}.o') if v.endswith('/host/westlake_stock_host_main.o') else str(repo/'bms/src/.work/b80-network-groups/candidate-service-1.o') if v.endswith('/host/appspawn_service.o') else v for v in c]
 subprocess.run(c,cwd=frozen,check=True)
a=(out/'appspawn-x-1').read_bytes();assert a==(out/'appspawn-x-2').read_bytes();print(hashlib.sha256(a).hexdigest())
