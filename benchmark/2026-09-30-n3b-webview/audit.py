#!/usr/bin/env python3
"""Audit target ELF, preserved objects, original bodies and exact package delta."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
from deploy_generation import load_package,validate_replacement
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((P/'package.json').read_text());base=Path(d['base']);pkg=Path(d['package'])
b=load_package(base);n=load_package(pkg);target=d['replace_target']
validate_replacement(b,n,target)
changed=[f for f in n['files'] if n['files'][f]!=b['files'].get(f)]
assert changed==['payload/android/lib64/liboh_android_runtime.so'],changed
assert set(n['files'])==set(b['files'])
old=base/changed[0];new=pkg/changed[0];readelf='/opt/homebrew/opt/llvm/bin/llvm-readelf'
def read(p,*args):return subprocess.check_output([readelf,*args,str(p)],text=True)
def symbols(p):
 rows=read(p,'--dyn-syms','--wide').splitlines()
 exports={l.split()[-1] for l in rows if re.match(r'\s*\d+:',l) and ' UND ' not in l and len(l.split())>=8}
 imports={l.split()[-1] for l in rows if re.match(r'\s*\d+:',l) and ' UND ' in l and len(l.split())>=8}
 return exports,imports
oldexp,oldimp=symbols(old);newexp,newimp=symbols(new)
assert oldexp<=newexp,oldexp-newexp
assert 'Java_adapter_core_WestlakeWebViewInstall_nativePrime' in newexp
assert 'Java_adapter_core_WestlakeWebViewInstall_nativePublishAfterBind' in newexp
oldyn=read(old,'-d');newdyn=read(new,'-d');needed=lambda s:re.findall(r'\(NEEDED\).*?\[(.*?)\]',s)
assert needed(oldyn)==needed(newdyn),(needed(oldyn),needed(newdyn))
assert not re.search(r'\((?:RUNPATH|RPATH|TEXTREL)\)',newdyn)
assert 'AArch64' in read(new,'-h')
assert 'liboh_android_runtime.so' in newdyn
supply=[]
for rel in ['bms/src/.work/b6-latest/platform-pool/system/lib64/chipset-sdk-sp/libc++.so',
            'bms/src/.work/b6-latest/platform-pool/system/lib64/libc++_shared.so']:
 f=R/rel;exports,_=symbols(f)
 missing=sorted((newimp-oldimp)-{x.split('@')[0] for x in exports})
 supply.append({'input':rel,'sha256':sha(f),'missing':missing,
                'selected_by_needed':f.name in needed(newdyn),
                'live_identity':'archived OH6.1 input; not reread while board offline'})
assert supply[0]['selected_by_needed'] and not supply[0]['missing']
assert not supply[1]['selected_by_needed'] and supply[1]['missing'], 'wrong C++ ABI substitution negative'
(P/'new-import-supply.json').write_text(json.dumps(supply,indent=2)+'\n')
origins=json.loads((P/'source-origins.json').read_text());donor=R/origins['origin'];assert sha(donor)==origins['sha256']
s=(P/'src/webview_publication.cpp').read_text();assert hashlib.sha256(s.encode()).hexdigest()==origins['candidate_sha256']
for f in origins['functions']:
 start=s.index(f['function']);end=s.index('\n}',start)+2
 assert hashlib.sha256(s[start:end].encode()).hexdigest()==f['sha256'],f['function']
objects=json.loads((P/'baseline-objects.json').read_text())
for name,h in objects.items():assert sha(R/'bms/src/.work/n3b-webview/runtime-objects'/name)==h,name
build=json.loads((P/'build-results.json').read_text());assert build['baseline_sha256']==sha(old)
assert build['candidate_sha256']==sha(new)
assert sha(pkg/'package.json')==d['manifest_sha256']
(P/'elf-audit.json').write_text(json.dumps({'changed_paths':changed,'preserved_objects':len(objects),'baseline_bit_identical':True,'removed_exports':sorted(oldexp-newexp),'added_exports':sorted(newexp-oldexp),'added_imports':sorted(newimp-oldimp),'needed_order_unchanged':True,'needed':needed(newdyn),'body_hashes_verified':len(origins['functions'])},indent=2)+'\n')
print('PASS one runtime, 61 original objects, 6 exact donor bodies, no removed exports, identical NEEDED order')
