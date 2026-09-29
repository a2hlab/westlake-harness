from pathlib import Path
import re,shutil,json,hashlib,subprocess
R=Path.cwd();W=R/'bms/src/.work/b6-task58';T=Path(__file__).resolve().parents[1];src=W/'trial-complete/helloworld';dst=T/'trial/helloworld';dst.mkdir(parents=True,exist_ok=True)
for name in ['record.json','t3.jpeg','final.jpeg','timeline.txt','processes-after.txt','click-before.txt','click-after.txt','child-proof-26935.sha256','child-proof-26935.late-sha256','child-proof-26935.late-maps']:
 shutil.copy2(src/name,dst/name)
log=(src/'hilog.txt').read_text();lines=log.splitlines();focused=[f'{i}: {l}' for i,l in enumerate(lines,1) if re.search(r'\s26935\s',l) or ('WLCGATE' in l and '25303' in l)]
(dst/'hilog-excerpt.txt').write_text('\n'.join(focused)+'\n');signals=[f'{i}: {l}' for i,l in enumerate(lines,1) if re.search(r'\s26935\s',l) and ('signal: 11' in l or 'signal: 7' in l)]
(dst/'signal-chain.txt').write_text('\n'.join(signals)+'\n')
f=next(src.glob('fault-*.txt'));fault=f.read_text().splitlines();excerpt=fault[:63]+['','Relevant fault maps:']+[l for l in fault if re.match(r'[0-9a-f]+-[0-9a-f]+ ',l) and any(n in l for n in ['libart.so','libsigchain.so','libopenjdkjvm.so','libdfx_signalhandler'])];(dst/'fault-excerpt.txt').write_text('\n'.join(excerpt)+'\n')
for lib,start,end,out in [(W/'system-libopenjdkjvm.so','0x6b8c','0x6c20','system-JVM_NativeLoad.txt'),(W/'candidate/libart.so','0x417210','0x41722c','art-sigsegv-handler.txt')]:
 a=subprocess.check_output(['/opt/homebrew/opt/llvm/bin/llvm-objdump','-d','--no-show-raw-insn','--start-address='+start,'--stop-address='+end,str(lib)],text=True);(dst/out).write_text(a.replace(str(R),'$REPO'))
rel=subprocess.check_output(['/opt/homebrew/opt/llvm/bin/llvm-readelf','-rW',str(W/'system-libopenjdkjvm.so')],text=True)
(dst/'JVM-runtime-relocation.txt').write_text('\n'.join(l for l in rel.splitlines() if '000000000000ad98' in l)+'\n')
receipt={'raw_vm_directory':'$VM_HOME/a2hlab/board/b6-task58-helloworld-5ea/helloworld','raw_files':{f.name:{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in src.iterdir() if f.is_file()},'excerpt_numbering':'1-based original hilog lines','raw_fault_complete_private_copy':str(f.name)}
(dst/'provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
(T/'signal-chain-results.json').write_text(json.dumps({'sigsegv':{'verdict':'verified','pid':26935,'first_slot':0,'handler_address':'0x7f02cd7210','art_load_bias':'0x7f028c0000','elf_offset':'0x417210','symbol':'art::art_sigsegv_handler(int, siginfo_t*, void*)','next_slot':3,'next_handler_address':'0x7f86607e78','next_handler_library':'libdfx_signalhandler.z.so','evidence':'trial/helloworld/signal-chain.txt'},'sigbus':{'verdict':'unverified','reason':'No SIGBUS registration or dispatch for candidate PID is present in captured hilog. Conditional placement not claimed.'},'java_implicit_null_to_npe':'unverified; observed native Runtime::instance_ null dereference is outside compiled Java implicit-null coverage'},indent=2)+'\n')
print('evidence collected')
