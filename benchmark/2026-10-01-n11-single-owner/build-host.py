"""Exact U8 host baseline then two strict N11 owner builds."""
import hashlib,json,os,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];D=R.parent/'westlake-harness-bms-deploy';B=D/'bms/src/.work/b68-generation'
recipe=json.loads((R/'benchmark/2026-10-01-n10-native/host-command-input.json').read_text())
OUT=Path(os.environ.get('N11_HOST_OUT',str(R.parent/'westlake-n11-build/host')))
env=dict(os.environ,LD_LIBRARY_PATH=str(B/'.work/product-tls-generation/frozen/toolchain/runtime'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipts={}
for variant in ['baseline','candidate','repeat']:
 out=OUT/variant;out.mkdir(parents=True,exist_ok=False)
 c=list(recipe['compile']);c[c.index('-c')+1]=str(D/'benchmark/2026-09-30-n4-native/src/westlake_stock_host_main.c') if variant=='baseline' else str(H/'src/host.c');c[c.index('-o')+1]=str(out/'host.o');c+=['-I'+str(D/'bms/src/adapter/framework/app-native-loader/src')]
 ld=list(recipe['link']);ld[ld.index('-o')+1]=str(out/'appspawn-x');ld=[str(out/'host.o') if x.endswith('/host/westlake_stock_host_main.o') else str(D/'bms/src/.work/b80-network-groups/candidate-service-1.o') if x.endswith('/host/appspawn_service.o') else x for x in ld]
 for cmd in [c,ld]:subprocess.run(cmd,cwd=B,env=env,check=True)
 receipts[variant]={'sha256':sha(out/'appspawn-x'),'commands':[c,ld],'link_objects':{x:sha(Path(x)) for x in ld if x.endswith('.o')}}
 if variant=='baseline':assert receipts[variant]['sha256'].startswith('1d3b0881'),receipts[variant]['sha256']
 if variant=='repeat':assert receipts[variant]['sha256']==receipts['candidate']['sha256']
(H/'host-build-receipt.json').write_text(json.dumps(receipts,indent=2)+'\n');print(receipts['candidate']['sha256'])
