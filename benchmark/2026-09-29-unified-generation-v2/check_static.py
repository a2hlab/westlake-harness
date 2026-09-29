from pathlib import Path
import subprocess,json,re
R=Path.cwd();E=Path(__file__).resolve().parent;W=R/'bms/src/.work/b67-generation';new=W/'candidate';old=R.parent/'westlake-generation-6cb40cd6/payload';llvm='/opt/homebrew/opt/llvm/bin/'
rows={}
for name,base in [('appspawn-x',old/'runtime/appspawn-x'),('libwestlake_android_child.z.so',old/'runtime/libwestlake_android_child.z.so'),('libwestlake_android_runtime_provider.so',old/'route/libwestlake_android_runtime_provider.so'),('liboh_android_runtime.so',old/'android/lib64/liboh_android_runtime.so'),('libapp_native_loader.so',old/'route/libapp_native_loader.so')]:
 vals=[]
 for p in [base,new/name]:
  x=subprocess.check_output([llvm+'llvm-readelf','-dW',str(p)],text=True)
  vals.append([l.split(')',1)[1].strip() for l in x.splitlines() if any('('+k+')' in l for k in ['NEEDED','SONAME','RPATH','RUNPATH','FLAGS','FLAGS_1'])])
 assert vals[0]==vals[1],(name,vals)
 rows[name]={'ordered_dynamic_equal':True,'dynamic':vals[1]}
x=subprocess.check_output([llvm+'llvm-objdump','-d','--no-show-raw-insn','--disassemble-symbols=WLSCPL_OpenPreparedNamespace',str(new/'libwestlake_android_child.z.so')],text=True)
assert re.search(r'\bb\s+0x[0-9a-f]+ <dlopen@plt>',x) and not re.search(r'\bbl\s+0x[0-9a-f]+ <dlopen@plt>',x)
(E/'loader-tail-call.txt').write_text(x)
nm=lambda p:subprocess.check_output([llvm+'llvm-nm','-D','-C','--defined-only',str(p)],text=True)
a=nm(old/'android/lib64/liboh_android_runtime.so');b=nm(new/'liboh_android_runtime.so')
regs=['SQLiteConnection','SQLiteGlobal','SQLiteDebug','CursorWindow']
for n in regs:
 assert re.search(r' W android::register_android_database_'+n+r'\(',a)
 assert re.search(r' T android::register_android_database_'+n+r'\(',b)
(E/'sqlite-registrars.txt').write_text('BASELINE\n'+'\n'.join(l for l in a.splitlines() if 'register_android_database_' in l)+'\nCANDIDATE\n'+'\n'.join(l for l in b.splitlines() if 'register_android_database_' in l)+'\n')
report={'passed':True,'ordered_dynamic':rows,'loader_tail_call_retained':True,'sqlite_registrars_weak_to_real':regs,'note':'Only ANL/runtime functionality is changed; host/child keep accepted G1-G4 sources and update sealed pins. Restored pre-extension AndroidRuntime cohort avoids unrelated ICU/TLS/AudioTrack changes.'}
(E/'static-dispositions.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS all five ordered dynamic tables, original dlopen tail call, four strong SQLite registrars')
