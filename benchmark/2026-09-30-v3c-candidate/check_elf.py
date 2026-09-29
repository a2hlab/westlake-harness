#!/usr/bin/env python3
"""Read ELF declarations; this does not prove namespace resolution on device."""
import json,re,subprocess
from pathlib import Path
from assemble import HERE,pin,save,sha
TOOL=Path('/opt/homebrew/opt/llvm/bin/llvm-readelf')
def inspect(p):
    raw=subprocess.check_output([str(TOOL),'--file-header','--dynamic','--dyn-syms','--wide',str(p)],text=True)
    strong=[];weak=[];exports=[]
    for line in raw.splitlines():
        f=line.split()
        if len(f)<8 or not f[0][:-1].isdigit() or not f[0].endswith(':'):continue
        name=f[7].split('@')[0]
        if f[6]=='UND':
            (weak if f[4]=='WEAK' else strong).append(name)
        elif f[4] in ('GLOBAL','WEAK'):exports.append(name)
    return dict(needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',raw),strong_undefined=sorted(set(strong)),weak_undefined=sorted(set(weak)),exports=sorted(set(exports)),aarch64='AArch64' in raw,raw=raw)
def main():
    inputs=json.loads((HERE/'inputs.json').read_text());rows=[]
    for a in inputs['artifacts']:
        pin(a['path'],a['sha256']);d=inspect(a['path'])
        if not d['aarch64']:raise ValueError('not AArch64: '+a['name'])
        (HERE/'evidence'/('elf-'+a['name']+'.txt')).write_text(d.pop('raw'))
        d.update(name=a['name'],sha256=a['sha256'],hard_cpp_undefined=[s for s in d['strong_undefined'] if s.startswith(('_Z','__cxa_'))])
        if a['name'] in {'liboh_tls_boundary.so','libwestlake_jni_gapfill.so'}:
            assert d['needed']==['libc.so'],d['needed']
            assert not d['hard_cpp_undefined'],d['hard_cpp_undefined']
            assert 'JNI_OnLoad' in d['exports']
        rows.append(d)
    save(HERE/'elf-audit.json',dict(tool=str(TOOL),tool_sha256=sha(TOOL),libraries=rows,device_load_validated=False))
    print(json.dumps({x['name']:{k:x[k] for k in ['needed','hard_cpp_undefined']} for x in rows if x['name'] in {'liboh_tls_boundary.so','libwestlake_jni_gapfill.so'}},indent=2))
if __name__=='__main__':main()
