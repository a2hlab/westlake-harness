#!/usr/bin/env python3
"""Offline evidence packaging; no devices, execution of target or builds."""
import hashlib,json,subprocess,zipfile
from pathlib import Path
D=Path(__file__).resolve().parent
R=D.parents[3]; MAIN=R.parent/'westlake-harness'
BASE=Path.home()/'.local/share/westlake/commercial-game-20261021'
ARC=R.parent/'westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x): (D/n).write_text(json.dumps(x,indent=2)+'\n')
def ref(p):
 s=str(p)
 for root,alias in [(BASE,'$COMMERCIAL_PRIVATE'),(MAIN,'$MAIN'),(ARC,'$U13_NATIVE'),(R,'$REPO')]:
  if p.is_relative_to(root):return alias+'/'+str(p.relative_to(root))
 return s.replace(str(Path.home()),'$HOME')
def pin(p):return {'path':ref(p),'sha256':sha(p),'bytes':p.stat().st_size}
def run(name,argv):
 q=D/'.private'/name;c=subprocess.run(argv,capture_output=True)
 q.with_suffix('.argv.json').write_text(json.dumps(argv));q.with_suffix('.stdout').write_bytes(c.stdout);q.with_suffix('.stderr').write_bytes(c.stderr);q.with_suffix('.rc').write_text(str(c.returncode))
 return c
log=BASE/'g24-window02/game-observe/hilog.txt';lines=log.read_text().splitlines()
selected=[(2938,2940),(3073,3073),(3135,3136),(3161,3162),(3276,3280),(3682,3684),(3733,3733)]
(D/'log-excerpt.txt').write_text('\n'.join(f'L{i}: {lines[i-1]}' for lo,hi in selected for i in range(lo,hi+1))+'\n')
put('log-provenance.json',{**pin(log),'line_ranges':selected,'child':31523,'raw_public':False})
app=BASE/'g24-window02/apply.json';a=json.loads(app.read_text());sel={k:v for k,v in a['plan']['expected'].items() if any(x in k for x in ['libnativeloader.so','libbionic_compat.so','libwestlake_bionic_pthread_bridge.so','libwestlake_native_abi.so','libapp_native_loader.so','appspawn-x'])}
put('deployment-evidence.json',{'source':pin(app),'status':a['status'],'apply_boot':a['boot_id'],'expected_files':sel,'verification_child':a['verification']['child'],'limitation':'apply transaction/control verification is not a game child31523 provider map or binding measurement','game_identities_file':pin(BASE/'g24-window02/game-observe/identities.json'),'game_identities':json.loads((BASE/'g24-window02/game-observe/identities.json').read_text())})
spec=MAIN/'specs/commercial-game-round1/t16-runtime-loader-triage.spec.md'
run('lint',['agent-spec','lint',str(spec),'--min-score','0.7'])
run('contract',['agent-spec','contract',str(spec)])
source_ranges=[(R/'bms/src/adapter/framework/appspawn-x/bionic_compat/src/unity_libc_stubs.c',84,97),(R/'benchmark/2026-10-21-commercial-game/runtime-loader-triage/sources/benchmark/2026-09-30-n3-native/src/native_abi.c',10,17),(MAIN/'benchmark/2026-10-03-u15-compat-v3/README.md',92,105),(MAIN/'bms/src/adapter/framework/app-native-loader/src/app_native_loader.c',60,76),(MAIN/'bms/src/adapter/framework/app-native-loader/src/app_native_loader.c',447,475),(ARC/'native-checks/n4-host.c',184,230),(ARC/'native-checks/n4-host.c',263,291),(ARC/'native-checks/n4-host.c',345,358),(MAIN/'benchmark/2026-10-21-commercial-game/gles-loader-candidate/sources/candidate/include/nativeloader/native_bridge_policy.h',15,58)]
idx=[];chunks=[]
for p,lo,hi in source_ranges:
 idx.append({**pin(p),'lines':[lo,hi]});ls=p.read_text().splitlines();chunks.append(f'FILE {ref(p)} SHA256 {sha(p)}\n'+'\n'.join(f'{i}: {ls[i-1]}' for i in range(lo,min(hi,len(ls))+1)))
put('source-index.json',idx);(D/'source-excerpts.txt').write_text('\n\n'.join(chunks)+'\n')
rea=json.loads((R/'benchmark/2026-10-21-commercial-game/runtime-loader-triage/rea-reuse.json').read_text());entries=[]
for i,e in enumerate(rea['existing_methods']):
 p=BASE/f'exact-static/outer-rea/method-{i}.tool-result.json';assert sha(p)==e['raw']['sha256'];entries.append({'method':e['method'],'evidence_id':e['evidence_id'],**pin(p),'verified':True,'executed_by':'outer(codex), prior G04'})
put('rea-reuse.json',{'existing_methods':entries,'new_REA':'NOT_EXECUTED: exact ELF tables and existing source/evidence sufficient','new_target_execution':False})
elf=json.loads((D/'elf-evidence.json').read_text());game=next(e for e in elf if e['object']=='game')
apk=BASE/'official-input/apk/yuanshen_7.1.0.apk'
with zipfile.ZipFile(apk) as z:
 with z.open('lib/arm64-v8a/libyuanshen.so') as f:
  h=hashlib.sha256();size=0
  while b:=f.read(1024*1024):h.update(b);size+=len(b)
assert h.hexdigest()==game['sha256'] and size==game['bytes']
assert sha(apk)=='abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
put('apk-binding.json',{'apk':pin(apk),'member':'lib/arm64-v8a/libyuanshen.so','member_sha256':h.hexdigest(),'member_bytes':size,'local_extracted_match':True})
for name,file,lo,hi in [('abi-forward',ARC/'payload/android/lib64/libwestlake_native_abi.so','0x2454','0x24ac'),('pthread-forward',ARC/'payload/android/lib64/libwestlake_bionic_pthread_bridge.so','0x2db8','0x2dbc')]:
 c=run(name,['/opt/homebrew/bin/llvm-objdump','-d','--no-show-raw-insn','--start-address='+lo,'--stop-address='+hi,str(file)])
 (D/(name+'.txt')).write_text(c.stdout.decode().replace(str(ARC),'$U13_NATIVE'))
# Keep only small public excerpts; raw disassemblies and game symtab remain private.
put('raw-index.json',[{'path':'.private/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((D/'.private').iterdir()) if p.is_file()])
put('verification.json',{'APK_member_exact':True,'existing_REA_hashes_verified':len(entries),'raw_rc':{p.stem:int(p.read_text()) for p in sorted((D/'.private').glob('*.rc'))},'runtime_test':False})
print('packaged exact APK/member, five ELF tables, two function excerpts, five prior REA, lint/contract')
