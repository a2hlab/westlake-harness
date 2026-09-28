"""Check the actual libsigchain-owned libart imports before any deployment."""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent
NM='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-nm'
NEW=R.parents[2]/'bms/src/adapter/out/aosp_lib_arm64/libsigchain.so'
OLD=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite/.bridge-payload/pr03-74e6-portable/route/libsigchain.so')
ART=Path('/Users/zhaoyue/.cache/b6-route-a-libart.so')
def symbols(p):
 rows=[x.split() for x in subprocess.check_output([NM,'-D',str(p)],text=True).splitlines()]
 return ({x[-1] for x in rows if len(x)==2 and x[0] in ('U','w','v')},{x[-1] for x in rows if len(x)==3 and x[-2] not in ('U','w','v')})
def check(required,exports):
 missing=sorted(set(required)-set(exports))
 return {'passed':not missing,'missing':missing,'deploy_allowed':not missing}
def main():
 bindings=json.loads((R/'bindings.json').read_text());imports,_=symbols(ART);_,old= symbols(OLD);newimports,new=symbols(NEW)
 overlap=imports&old;assert overlap==set(bindings['bindings'])
 required={n for n,x in bindings['bindings'].items() if x['owner'] and x['owner'].endswith('/libsigchain.so')}
 external={n:x for n,x in bindings['bindings'].items() if n not in required};assert set(external)=={'sigaction'} and external['sigaction']['owner'].endswith('/ld-musl-aarch64.so.1')
 assert required=={'AddSpecialSignalHandlerFn','RemoveSpecialSignalHandlerFn','EnsureFrontOfChain','SkipAddSignalHandler'}
 verdict=check(required,new);assert verdict['passed'],verdict
 negatives={n:check(required,new-{n}) for n in required};assert all(not x['deploy_allowed'] and x['missing']==[n] for n,x in negatives.items())
 assert {'add_special_signal_handler','remove_special_signal_handler'}<=newimports
 assert not any('sigchain_probe' in x or 'l3_' in x for x in new)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 rec={'libart_sha256':sha(ART),'old_sha256':sha(OLD),'new_sha256':sha(NEW),'new_path':str(NEW),'source_sha256':sha(R.parents[2]/'bms/src/adapter/aosp_patches/art/sigchainlib/sigchain_muslcompat.cc'),'old_export_import_overlap':sorted(overlap),'required':sorted(required),'external_bindings':external,'new_exports':sorted(new),'new_imports':sorted(newimports),'positive':verdict,'negative_symbol_manifests':negatives,'negative_kind':'remove each required export from parsed symbol manifest; same deployment predicate, no defective DSO deployed','probe':False,'compiler':'dockbuild a2hlab-build:24.04, locked OH SDK clang++, original compile_sigchain_muslcompat.sh'}
 (R/'symbol-gate.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
if __name__=='__main__':main()
