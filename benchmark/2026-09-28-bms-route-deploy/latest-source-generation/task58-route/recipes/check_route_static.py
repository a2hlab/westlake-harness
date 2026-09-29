from pathlib import Path
import json,subprocess,re,hashlib
R=Path.cwd();T=Path(__file__).resolve().parents[1];W=R/'bms/src/.work/b6-task58-route';OLD=R/'bms/src/.work/b6-task58/candidate';llvm='/opt/homebrew/opt/llvm/bin/'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def dis(f,fn):return subprocess.check_output([llvm+'llvm-objdump','-d','--no-show-raw-insn','--disassemble-symbols='+fn,str(f)],text=True)
def tail(s):return bool(re.search(r'\bb\s+0x[0-9a-f]+ <dlopen@plt>',s)) and not re.search(r'\bbl\s+0x[0-9a-f]+ <dlopen@plt>',s)
n=dis(W/'candidate/libwestlake_android_child.z.so','WLSCPL_OpenPreparedNamespace');o=dis(OLD/'libwestlake_android_child.z.so','WLSCPL_OpenPreparedNamespace')
assert tail(n) and not tail(o),'namespace caller shape mismatch'
(T/'new-open-prepared.txt').write_text(n.replace(str(R),'$REPO'));(T/'previous-open-prepared.txt').write_text(o.replace(str(R),'$REPO'))
libc=R/'bms/src/.work/b6-latest/platform-pool/system/lib/ld-musl-aarch64.so.1'
(T/'musl-dlopen.txt').write_text(dis(libc,'dlopen').replace(str(R),'$REPO'))
checks={}
for name in ['appspawn-x','libwestlake_android_child.z.so','libwestlake_android_runtime_provider.so']:
 vals=[]
 for p in [OLD/name,W/'candidate'/name]:
  s=subprocess.check_output([llvm+'llvm-readelf','-dW',str(p)],text=True)
  vals.append([l.split(')',1)[1].strip() for l in s.splitlines() if any('('+x+')' in l for x in ['NEEDED','SONAME','RPATH','RUNPATH','FLAGS','FLAGS_1'])])
 assert vals[0]==vals[1],name
 checks[name]={'ordered_dynamic_matches_previous_r155_aligned':True,'values':vals[1]}
assert sha(W/'candidate/libopenjdkjvm.so')=='8b462862921f3fbca7e4306523d851b2ae00564094a6f5ca1b6658c7c6b457a8'
report={'passed':True,'scope':'One wrapper storage-duration change; previous task58 full static inventory remains the baseline for all other source. Generated identity strings necessarily change.','tail_call_positive':True,'previous_non_tail_negative_rejected':True,'libc_sha256':sha(libc),'dynamic':checks,'source_patch':'loader-tail-call.patch','reference_full_inventory':'../task58/static-dispositions.json','preboard_mapping_gate':'After launch, require one offset-zero ART mapping and one route-a libopenjdkjvm before further app trials.'}
(T/'static-dispositions.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS tail call, prior negative, dynamic parity')
