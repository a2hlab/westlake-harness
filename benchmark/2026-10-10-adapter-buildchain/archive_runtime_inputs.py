#!/usr/bin/env python3
"""Archive observed dependency closure and exact tool/link/build inputs for runtime187.

Compiler-generated .d files cover the main C++ sources; dependency-only -M
invocations cover sqlite, four GL and six Emboss sources (including system
headers). Symlinks are materialized in the archive, with content hashes retained.
No board or historical source/object is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import tarfile


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def dependency_paths(p):
    line=p.read_text().replace('\\\n',' ').splitlines()[0]
    return [Path(s) for s in shlex.split(line.split(':',1)[1])]


def archive(w, root):
    w, root=Path(w).resolve(),Path(root).resolve()
    files=set()
    deps=list((root/'r1/runtime-objects').glob('*.d'))+list((root/'r1/dependencies').rglob('*.d'))
    if len(deps)<60: raise ValueError('incomplete dependency receipt')
    for d in deps: files.update(dependency_paths(d))
    b=w/'westlake-harness-bms-deploy'; p=w/'westlake-inputs/generations/u13-runtime-m1-v1/build/u13'
    for rel in ('recipe.sh','driver.sh','extra-commands.json'): files.add(p/rel)
    extra=json.loads((p/'extra-commands.json').read_text())
    for argv in extra: files.add(Path(argv[0])); files.add(Path(argv[argv.index('-c')+1]))
    for group in ('n2','n4'):
        for d in (root/'r1'/group).glob('*.c'): files.add(d)
    for name in ('build-globjects.sh','westlake-gl/gen_gl_forwarders.py'):
        files.add(b/'benchmark/2026-09-30-n2-native'/name)
    files.add(b/'benchmark/2026-09-30-n4-native/build-egl.sh')
    files.add(b/'bms/src/.work/b6-art14-recovery/build/cxx-sdk15')
    files.add(b/'bms/src/.work/b6-art14-recovery/build/sdk15-declarations.h')
    files.add(b/'bms/src/.work/b6-art14-recovery/tools/aidl')
    for f in (b/'bms/src/.work/b6-art14-recovery/tools/lib64').glob('*'):
        if f.is_file(): files.add(f)
    tc=b/'bms/src/.work/product-tls-generation/frozen/toolchain'
    for name in ('clang','clang++','clang-15','lld','ld.lld','llvm-nm','llvm-readelf','llvm-objdump'):
        files.add(tc/'bin'/name)
    # -MMD omits system includes: retain both exact sysroot/header trees and libc++.
    for base in (tc/'include', b/'bms/src/.work/product-tls-generation/frozen/sysroot/include',
                 b/'bms/src/.work/b6-latest/oh/out/wukong100/obj/third_party/musl/usr/include'):
        if not base.is_dir(): raise ValueError('missing complete header tree: '+str(base))
        files.update(f for f in base.rglob('*') if f.is_file())
    a=b/'bms/src/.work/b6-art14-recovery/aosp-restoration'
    files.update([a/'frameworks/native/libs/input/android/os/IInputConstants.aidl',
                  a/'system/core/toolbox/generate-input.h-labels.py',
                  a/'bionic/libc/kernel/uapi/linux/input.h',
                  b/'bms/src/.work/b68-generation/platform-pool/system/lib64/platformsdk/libGLESv3.so',
                  b/'scripts/lab/check_frozen.py', b/'knowledge/frozen/frozen.json',
                  b/'bms/src/.work/n4-native/frozen-source-view/benchmark/2026-09-30-asset-fd-runtime/src/android_util_AssetManager_aosp.cpp'])
    # Clang resource headers and compiler-rt are selected by its installation path.
    for f in (tc/'lib/clang').rglob('*'):
        if f.is_file(): files.add(f)
    prior=w/'westlake-inputs/generations/u15-runtime-m3-v1/link/mirrored-inputs.txt'
    files.add(prior)
    for name in prior.read_text().splitlines():
        f=w/name
        if f.is_file() and f.suffix!='.o': files.add(f)
    # Actual build output uses the registry copied by the historical driver.
    files.add(b/'bms/src/.work/b91-common-event/runtime-out/libwestlake_thread_guard_registry.so')
    for run in ('r1','r2'):
        files.update(f for f in (root/run).glob('*.sh'))
        files.add(root/run/'preparation.json')
    files.add(Path(__file__).resolve().parent/'prepare_runtime_cold.py')
    files.add(Path(__file__).resolve().parent/'prepare_runtime_dependencies.py')
    rows=[]
    for f in sorted(files):
        if not f.is_absolute(): f=b/f
        if not f.is_file(): raise ValueError('missing dependency: '+str(f))
        if not f.is_relative_to(w): raise ValueError('dependency outside WORKSPACES: '+str(f))
        rows.append({'path':'$WORKSPACES/'+str(f.relative_to(w)), 'sha256':digest(f), 'bytes':f.stat().st_size})
    inventory=root/'input-inventory.json'; inventory.write_text(json.dumps({'schema':1,'scope':'observed compiler dependency closure + frozen tools and retained link input witnesses','dependencies':len(deps),'files':rows},indent=2)+'\n')
    out=root/'runtime187-inputs.tar.gz'
    if out.exists(): raise ValueError('refuse overwrite archive')
    with tarfile.open(out,'w:gz',compresslevel=1,dereference=True) as tar:
        for row in rows:
            f=w/row['path'].removeprefix('$WORKSPACES/')
            tar.add(f, arcname=str(f.relative_to(w)), recursive=False)
        tar.add(inventory,arcname='input-inventory.json')
    # Hashes must still equal the archived/read closure after writing.
    for row in rows:
        f=w/row['path'].removeprefix('$WORKSPACES/')
        if digest(f)!=row['sha256']: raise ValueError('input changed during archive: '+str(f))
    receipt={'schema':1,'file_count':len(rows),'dependency_files':len(deps),'total_input_bytes':sum(r['bytes'] for r in rows),
             'inventory':{'path':'$WORKSPACES/'+str(inventory.relative_to(w)),'sha256':digest(inventory)},
             'archive':{'path':'$WORKSPACES/'+str(out.relative_to(w)),'sha256':digest(out),'bytes':out.stat().st_size},
             'archive_scope':'observed dependency closure, not a whole upstream checkout; includes exact source/header contents, generated headers, clang resources, link input witnesses and recipes',
             'container_image':'sha256:12ffb9324ca4df6427cbf6a6da0ac8ce575599291e933724275fce704520db63',
             'system_runtime':'Ubuntu loader/system libraries supplied by pinned container image; not duplicated into the tar'}
    (root/'archive-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n'); print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--workspaces',required=True);ap.add_argument('--root',required=True)
    a=ap.parse_args();archive(a.workspaces,a.root)
