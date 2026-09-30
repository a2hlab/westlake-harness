#!/usr/bin/env python3
"""Exact target GNU versions, with mutation negative; not a namespace proof."""
import hashlib,json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
REA='/opt/homebrew/opt/llvm/bin/llvm-readelf'
abi=R/'bms/src/.work/n3-native/flutter/libwestlake_native_abi.so'
def symbols(p):
 text=subprocess.check_output([REA,'--dyn-syms',str(p)],text=True)
 return [dict(undefined=' UND ' in l,name=l.split()[-1].replace('@@','@')) for l in text.splitlines() if re.match(r'\s*\d+:',l) and len(l.split())>=8]
exports={x['name'] for x in symbols(abi) if not x['undefined']}
needed={'__errno@LIBC','__register_atfork@LIBC','__FD_SET_chk@LIBC','__FD_CLR_chk@LIBC','__FD_ISSET_chk@LIBC','__system_property_get@LIBC','android_set_abort_message@LIBC','__sF@LIBC','__system_property_find@LIBC','__system_property_read_callback@LIBC_O'}
assert needed<=exports,needed-exports
rows=[]
for key,lib,names in [('firefox','libjnidispatch.so',{'__errno','__sF'}),('fd-fennec_fdroid','libjnidispatch.so',{'__errno','__sF'}),('vlc','libc++_shared.so',{'android_set_abort_message'}),*[(k,'libflutter.so',{'__system_property_get','__system_property_find'}) for k in ['fd-immich','fd-libre','fd-saber']]]:
 f=Path('/Users/zhaoyue/a2hlab/app-inputs')/key/'lib/arm64-v8a'/lib
 imports={x['name'] for x in symbols(f) if x['undefined'] and x['name'].split('@')[0] in names}
 assert len(imports)==len(names),(key,imports)
 assert imports<=exports,(key,imports-exports)
 rows.append(dict(key=key,file=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),imports=sorted(imports)))
assert not needed<=(exports-{'__errno@LIBC'}),'negative accepted missing errno version'
assert not needed<=(exports-{'android_set_abort_message@LIBC','__sF@LIBC','__system_property_find@LIBC','__system_property_read_callback@LIBC_O'}),'negative accepted missing abort version'
(P/'abi-audit.json').write_text(json.dumps(dict(abi_sha256=hashlib.sha256(abi.read_bytes()).hexdigest(),exact_exports=sorted(needed),consumers=rows,removed_export_negative='rejected',device_visibility='unverified'),indent=2)+'\n')
print('PASS exact 10 ABI exports, 6 actual consumers, removed-export negatives')
