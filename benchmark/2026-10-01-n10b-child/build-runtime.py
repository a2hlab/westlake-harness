"""Replay U8 runtime recipe; add isolated real Emboss without changing cached API objects."""
import hashlib,json,os,re,shlex,shutil,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parents[1];D=R.parent/'westlake-harness-bms-deploy';W=D/'bms/src/.work'
OLD=W/'n4-registration-order';F=W/'product-tls-generation/frozen';S=W/'b68-generation/oh/third_party/skia/m133'
OUT=Path(os.environ.get('N10B_RUNTIME_OUT',str(R.parent/'westlake-n10b-build/runtime')))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
recipe=(OLD/'recipe.sh').read_text();driver=(OLD/'driver.sh').read_text();assert (OLD/'runtime-out/liboh_android_runtime.so').is_file()
# Exact baseline is read from the signed U8 manifest rather than assumed source equivalence.
baseline=json.loads((R.parent/'westlake-generation-u8-j9-t7e/native/package.json').read_text())['files']['payload/android/lib64/liboh_android_runtime.so']
records={};env=os.environ.copy();env.update(N3B_SOURCE=str(D/'benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp'),N3B_WITH_PUBLICATION='1',LD_LIBRARY_PATH=str(W/'b6-art14-recovery/tools/lib64'))
for variant in ['baseline','candidate','repeat']:
 out=OUT/variant;out.mkdir(parents=True,exist_ok=False);shutil.copytree(OLD/'runtime-objects',out/'runtime-objects');(out/'runtime-out').mkdir()
 for p in (out/'runtime-objects').glob('*.o'):p.touch()
 (out/'runtime-objects/AndroidRuntime.o').unlink()
 if variant!='baseline': (out/'runtime-objects/android_graphics_Typeface.o').unlink()
 patched=recipe
 if variant!='baseline':
  patched=patched.replace(str(D/'benchmark/2026-10-01-j6-n4-sweep/n4-registration-order/AndroidRuntime.cpp'),str(H/'src/AndroidRuntime.cpp'))
  patched=patched.replace('$SRC/src/android_graphics_Typeface.cpp',str(H/'src/android_graphics_Typeface.cpp'))
  patched=patched.replace('SRCS=(','SRCS=(\n    '+shlex.quote(str(H/'src/asset-offsets-init.cpp')))
  cc=[str(F/'toolchain/bin/clang++'),'--target=aarch64-linux-ohos','--sysroot='+str(F/'sysroot'),'-isystem',str(F/'sysroot/include/aarch64-linux-ohos'),'-nostdinc++','-isystem',str(F/'toolchain/include/c++/v1'),'-std=c++17','-fPIC','-O2','-fno-rtti','-fno-exceptions','-fvisibility=hidden','-DSK_SUPPORT_LEGACY_EMBOSSMASKFILTER','-DSKIA_OHOS','-DSK_GANESH','-DSK_GL','-DENABLE_TEXT_ENHANCE','-DSKIA_OHOS_SINGLE_OWNER','-DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1','-DNDEBUG','-I'+str(S),'-I'+str(W/'b6-art14-recovery/aosp-restoration/libnativehelper/include_jni'),'-I'+str(W/'b6-art14-recovery/aosp-restoration/libnativehelper/include'),'-I'+str(W/'b6-art14-recovery/aosp-restoration/system/logging/liblog/include')]
  objects=[];commands=[]
  for p in sorted((H/'src/emboss').glob('*.cpp')):
   o=out/'runtime-objects'/('n10b-'+p.stem+'.o');cmd=cc+['-c',str(p),'-o',str(o)];commands.append(cmd);subprocess.run(cmd,check=True,env=env);objects.append(str(o))
  patched=patched.replace('if $CXX --target=aarch64-linux-ohos $LDFLAGS', 'objs+=('+ ' '.join(shlex.quote(x) for x in objects)+')\nif $CXX --target=aarch64-linux-ohos $LDFLAGS')
  patched=patched.replace('    -landroidfw -lbase', '    '+shlex.quote(str(W/'b11-egl-retry/link-inputs/libskia_canvaskit.z.so'))+' \\\n    -landroidfw -lbase')
  (out/'extra-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 (out/'recipe.sh').write_text(patched)
 run=driver.replace(str(OLD),str(out));run=run.replace('bash '+str(out/'recipe.sh'),'bash '+str(out/'recipe.sh'))
 (out/'driver.sh').write_text(run)
 with (out/'build.log').open('w') as f: subprocess.run(['bash',str(out/'driver.sh')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 binary=out/'runtime-out/liboh_android_runtime.so';records[variant]={'sha256':sha(binary),'objects':{p.name:sha(p) for p in (out/'runtime-objects').glob('*.o')},'recipe_sha256':sha(out/'recipe.sh'),'driver_sha256':sha(out/'driver.sh')}
 if variant=='baseline':assert sha(binary)==baseline,(sha(binary),baseline)
 if variant=='repeat':assert sha(binary)==records['candidate']['sha256']
(H/'runtime-build-receipt.json').write_text(json.dumps({'baseline_expected':baseline,'variants':records,'out_directory':str(OUT.relative_to(R.parent))},indent=2)+'\n');print(records['candidate']['sha256'])
