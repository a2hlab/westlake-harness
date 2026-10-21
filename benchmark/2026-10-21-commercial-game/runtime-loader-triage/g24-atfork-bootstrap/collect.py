#!/usr/bin/env python3
"""Local source/ELF evidence only. Does not compile, execute target or touch devices."""
from pathlib import Path
import hashlib,json,subprocess
D=Path(__file__).resolve().parent;R=D.parents[3];M=R.parent/'westlake-harness';BD=R.parent/'westlake-harness-bms-deploy';A=R.parent/'westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native';B=Path.home()/'.local/share/westlake/commercial-game-20261021';G=M/'benchmark/2026-10-21-commercial-game/gles-loader-candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alias(p):
 for root,a in [(A,'$U13_NATIVE'),(BD,'$BMS_DEPLOY'),(M,'$MAIN'),(R,'$REPO'),(B,'$COMMERCIAL_PRIVATE')]:
  if p.is_relative_to(root):return a+'/'+str(p.relative_to(root))
 return str(p).replace(str(Path.home()),'$HOME')
def pin(p):return {'path':alias(p),'sha256':sha(p),'bytes':p.stat().st_size}
def put(n,d): (D/n).write_text(json.dumps(d,indent=2)+'\n')
sources=[(G/'sources/candidate/src/native_loader_registry.cpp',215,247),(G/'sources/candidate/include/nativeloader/native_bridge_policy.h',14,58),(M/'bms/src/adapter/framework/app-native-loader/src/app_native_loader.c',395,427),(A/'native-checks/n4-host.c',184,230),(A/'native-checks/n4-host.c',246,260),(A/'native-checks/n4-host.c',329,357),(BD/'benchmark/2026-10-01-n5-native/source-evidence/oh61-dynlink.c',737,762),(BD/'benchmark/2026-10-01-n5-native/source-evidence/oh61-dynlink.c',1927,1949),(BD/'benchmark/2026-10-01-n5-native/source-evidence/oh61-dynlink.c',2029,2050),(BD/'benchmark/2026-10-01-n5-native/source-evidence/oh61-dynlink.c',3508,3535),(BD/'benchmark/2026-10-01-n5-native/source-evidence/oh61-dynlink.c',3698,3718),(BD/'benchmark/2026-09-30-n4-native/src/native_abi.c',10,17),(BD/'benchmark/2026-09-30-n4-native/build-abi.sh',1,28),(M/'benchmark/2026-10-03-u14-native-abi-gecko/README.md',1,25)]
chunks=[];idx=[]
for p,lo,hi in sources:
 ls=p.read_text().splitlines();hi=min(hi,len(ls));idx.append({**pin(p),'lines':[lo,hi]});chunks.append(f'FILE {alias(p)} SHA256 {sha(p)}\n'+'\n'.join(f'{i}: {ls[i-1]}' for i in range(lo,hi+1)))
put('source-index.json',idx);(D/'source-excerpts.txt').write_text('\n\n'.join(chunks)+'\n')
# Bind the candidate actually used, not the earlier b8be layout.
loader=B/'g21-rollout-01/candidate/native/payload/android/lib64/libnativeloader.so'
assert sha(loader)=='878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23'
put('objects.json',{'loader':pin(loader),'host':pin(A/'payload/runtime/appspawn-x'),'anl':pin(A/'payload/android/lib64/libapp_native_loader.so'),'loader_build_receipt':pin(G/'build-01-receipt.json'),'linker_source_limit':'OH6.1 archived source reference; exact G24 libc/linker source-to-deployed-byte equality NOT established'})
pcs={'loader':['5b80:','65a8:'],'anl':['35dc:'],'host':['ceac:','cefc:','cfec:','d0fc:','d130:','d190:','d5bc:']};chunks=[]
for n,needles in pcs.items():
 p=D/'.private'/f'{n}.stdout';ls=p.read_text().splitlines()
 for needle in needles:
  matches=[i for i,s in enumerate(ls) if s.strip().startswith(needle)];assert len(matches)==1,(n,needle,matches)
  i=matches[0];chunks.append(f'OBJECT {n} {needle}\n'+'\n'.join(ls[max(0,i-6):i+5]))
(D/'exact-pc-excerpts.txt').write_text('\n\n'.join(chunks)+'\n')
orig=BD/'bms/src/.work/n4-native/abi/libwestlake_native_abi.so';assert sha(orig)=='d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'
ps=[BD/'benchmark/2026-09-30-n4-native'/x for x in ['build-abi.sh','build-abi.log','src/native_abi.c','src/native_abi.map','src/bionic_stdio_compat.c']]
ps += [M/'benchmark/2026-10-03-u14-native-abi-gecko'/x for x in ['repro_d2053066.sh','results.json','evidence/hw248-repro-a.log','evidence/hw248-repro-b.log','evidence/toolchains.txt']]
put('provider-build-chain.json',{'native_abi_original':pin(orig),'sources_and_receipts':[pin(p) for p in ps],'original_log':'contains exact d205 SHA; historical combined output, not newly executed','later_reproduction':'two 554bf6bc builds; recorded allocated/code equality and debug/path-only differences, NOT byte-identical to d205','toolchain_limit':'recipe identifies frozen clang-15/sysroot and historical feef13a3 version; full current compiler/sysroot closure NOT rehashed here','db31_bridge':'exact ELF/export/tailcall known; exact standalone source/recipe receipt NOT closed in this bounded local slice','cce31_bridge':'exact ELF lacks atfork; current same-name source is not promoted to byte-reproduced source'})
for name in ['build-abi.log']:
 p=BD/'benchmark/2026-09-30-n4-native'/name;s=p.read_text().replace(str(BD),'$BMS_DEPLOY').replace(str(Path.home()),'$HOME');(D/'original-build-log.excerpt.txt').write_text(s)
# Separate actual lint execution.
argv=['agent-spec','lint',str(M/'specs/commercial-game-round1/t16-runtime-loader-triage.spec.md'),'--min-score','0.7'];c=subprocess.run(argv,capture_output=True)
for ext,b in [('argv.json',json.dumps(argv).encode()),('stdout',c.stdout),('stderr',c.stderr),('rc',str(c.returncode).encode())]:(D/'.private'/f'lint.{ext}').write_bytes(b)
(D/'lint.stdout.txt').write_text(c.stdout.decode());(D/'lint.rc').write_text(str(c.returncode))
put('raw-index.json',[{'path':'.private/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((D/'.private').iterdir()) if p.is_file()])
print('PASS exact 878c, 9 PC excerpts, d205 local original and historical reproduction references; no build')
