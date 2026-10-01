"""Historical pre-SKIA_OHOS ABI prototype; retained evidence, not a delivery recipe.
Use build-runtime.py for the corrected 152-byte OH vtable implementation.
"""
import hashlib,json,os,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent
WS=H.parents[2]; D=WS/'westlake-harness-bms-deploy'; W=D/'bms/src/.work'
F=W/'product-tls-generation/frozen'; S=W/'b68-generation/oh/third_party/skia/m133'
if os.environ.get('N10B_ALLOW_HISTORICAL_ABI_PROBE') != '1':
 raise SystemExit('Historical ABI prototype disabled; use build-runtime.py')
O=Path(os.environ['N10B_EMBOSS_PROBE_OUT']);O.mkdir(parents=True,exist_ok=False)
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(F/'toolchain/runtime')
cc=[str(F/'toolchain/bin/clang++'),'--target=aarch64-linux-ohos','--sysroot='+str(F/'sysroot'),'-isystem',str(F/'sysroot/include/aarch64-linux-ohos'),'-nostdinc++','-isystem',str(F/'toolchain/include/c++/v1'),'-std=c++17','-fPIC','-O2','-fno-rtti','-fno-exceptions','-fvisibility=hidden','-ffunction-sections','-fdata-sections','-DSK_SUPPORT_LEGACY_EMBOSSMASKFILTER','-DSK_GANESH','-DSK_GL','-DENABLE_TEXT_ENHANCE','-DSKIA_OHOS_SINGLE_OWNER','-DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1','-DNDEBUG','-I'+str(S)]
commands=[]
for name in ['SkEmbossMaskFilter','SkEmbossMask']:
 a=cc+['-c',str(S/('src/effects/'+name+'.cpp')),'-o',str(O/(name+'.o'))];commands.append(a);subprocess.run(a,env=env,check=True)
for rel in ['src/core/SkMask.cpp','src/base/SkMathPriv.cpp']:
 a=cc+['-c',str(S/rel),'-o',str(O/(Path(rel).stem+'.o'))];commands.append(a);subprocess.run(a,env=env,check=True)
mask=(S/'src/core/SkMaskFilter.cpp').read_text()
segments=[mask[mask.index('bool SkMaskFilterBase::asABlur'):mask.index('static SkMask extractMaskSubset')],mask[mask.index('SkMaskFilterBase::FilterReturn\nSkMaskFilterBase::filterRRectToNine'):mask.index('void SkMaskFilter::RegisterFlattenables')]]
(O/'emboss-base.cpp').write_text('#include "include/core/SkImageFilter.h"\n#include "include/core/SkMatrix.h"\n#include "src/core/SkMaskFilterBase.h"\n'+''.join(segments))
(O/'entry.cpp').write_text('#include "include/effects/SkBlurMaskFilter.h"\nextern "C" __attribute__((visibility("default"))) SkMaskFilter* probe_emboss() { const float d[3]={1,1,1};return SkBlurMaskFilter::MakeEmboss(1,d,0.5f,2).release(); }\n')
for name in ['emboss-base','entry']:
 a=cc+['-c',str(O/(name+'.cpp')),'-o',str(O/(name+'.o'))];commands.append(a);subprocess.run(a,env=env,check=True)
ld=cc+['-shared','-Wl,-z,defs','-Wl,--no-undefined','-Wl,--gc-sections','-Wl,-soname,libemboss-probe.so',str(O/'SkEmbossMaskFilter.o'),str(O/'SkEmbossMask.o'),str(O/'SkMask.o'),str(O/'emboss-base.o'),str(O/'entry.o'),str(O/'SkMathPriv.o'),str(W/'b11-egl-retry/link-inputs/libskia_canvaskit.z.so'),'-o',str(O/'libemboss-probe.so')]
commands.append(ld)
result=subprocess.run(ld,env=env,capture_output=True,text=True);(O/'link.txt').write_text(result.stdout+result.stderr)
receipt={'returncode':result.returncode,'commands':commands,'source_hashes':{str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in S.glob('src/effects/SkEmboss*')},'skia_sha256':hashlib.sha256((W/'b11-egl-retry/link-inputs/libskia_canvaskit.z.so').read_bytes()).hexdigest(),'device_io':False}
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(result.stdout+result.stderr);print('returncode',result.returncode)
