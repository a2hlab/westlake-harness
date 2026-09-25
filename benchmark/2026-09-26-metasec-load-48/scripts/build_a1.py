"""Reproduce stock libart link, compile only link_stubs, replace one weak object and relink."""
from board48 import *
w=pathlib.Path.home()/'a2hlab/ws';source=w/'art-build-operator48'
old=w/'out/art';out=w/'out-operator48';out.mkdir(exist_ok=False)
record=json.loads((old/'runtime/artifacts.json').read_text())
objects=old/'objects';runtime=old/'runtime'
assert sha(runtime/'libart.so')=='009a08fb8282b4ed8b857eaf014038adb93bb5cac0daa5d32ab89a13f29c8bbc'
for rel,h in record['objects'].items():assert sha(objects/rel)==h,rel
env=dict(__import__('os').environ,SOURCE_DATE_EPOCH='1772755200',TZ='UTC',LC_ALL='C')
commands=[]
def run(args):
 args=list(map(str,args));commands.append(args)
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 with (out/'build.log').open('a') as f:subprocess.run(args,check=True,env=env,stdout=f,stderr=subprocess.STDOUT)
make=['make','--no-print-directory','-s','-C',source,'-f','Makefile.ohos-arm64','WORKSPACE='+str(w),'BUILDDIR='+str(objects)]
core=subprocess.check_output(list(map(str,make+['print-clean-core-objects'])),text=True).splitlines()
additional=['stubs/nterp_real_port.o','sigchain/sigchain.o','stubs/link_stubs_arm64.weak.o','stubs/code_generator_vector_arm64_sve_stub.o','stubs/fault_handler_stubs.o','stubs/template_instantiations.weak.o','stubs/metrics_stubs.weak.o','stubs/thread_cpu_stub.weak.o','stubs/openjdkjvm_runtime_services.weak.o','fmtlib/format.o','tinyxml2/tinyxml2.o','asm_arm64/quick_entrypoints_arm64.o','asm_arm64/jni_entrypoints_arm64.o','asm_arm64/memcmp16_arm64.o','asm_arm64/mterp_arm64ng.o']
inputs=[pathlib.Path(p) for p in core]+[objects/p for p in additional]
assert {str(p.relative_to(objects)) for p in inputs}==set(record['objects'])
sdk=w/'toolchains/ohos-sdk/native';compiler=sdk/'llvm/bin/clang++'
flags=['--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-fPIC','-O2','-Werror=date-time','-ffile-prefix-map='+str(w)+'=/src','-ffile-prefix-map='+str(runtime)+'=/build/runtime','-I'+str(w/'upstream/aosp-11/libnativehelper/include_jni')]
def link(dest,ins):
 run([compiler,*flags,'-shared','-fuse-ld=lld','-nostdlib++','-Wl,-Bsymbolic','-Wl,--build-id=sha1','-Wl,--version-script='+str(source/'ziparchive_hide.map'),'-Wl,-soname,libart.so','-Wl,--allow-shlib-undefined','-o',dest,*ins,'-Wl,--no-as-needed',runtime/'libwestlake_runtime_boundary.so',w/'toolchains/clang-15/lib/aarch64-linux-ohos/libc++.so','-Wl,--as-needed',runtime/'libz.so','-lc','-ldl','-lpthread'])
link(out/'stock-libart.so',inputs)
assert sha(out/'stock-libart.so')==sha(runtime/'libart.so'),'stock link does not reproduce deployed binary'
print('STOCK_RELINK_IDENTICAL',sha(out/'stock-libart.so'),flush=True)
newobj=out/'objects';target=newobj/'stubs/link_stubs_arm64.weak.o'
run(['make','--no-print-directory','-C',source,'-f','Makefile.ohos-arm64','WORKSPACE='+str(w),'BUILDDIR='+str(newobj),target])
replaced=[target if str(p.relative_to(objects))=='stubs/link_stubs_arm64.weak.o' else p for p in inputs]
link(out/'libart.so',replaced)
nm=sdk/'llvm/bin/llvm-nm'
syms=subprocess.check_output([str(nm),'-D','--undefined-only',str(out/'libart.so')],text=True)
oldsyms=subprocess.check_output([str(nm),'-D','--undefined-only',str(runtime/'libart.so')],text=True)
(out/'undefined-added.txt').write_text('\n'.join(sorted(set(syms.splitlines())-set(oldsyms.splitlines())))+'\n')
result={'source_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),'baseline_art':sha(runtime/'libart.so'),'patched_art':sha(out/'libart.so'),'stock_relink_identical':True,'objects':len(inputs),'changed_object':'stubs/link_stubs_arm64.weak.o','old_object':record['objects']['stubs/link_stubs_arm64.weak.o'],'new_object':sha(target)}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
