"""Audit the actual linked child against deployed U9 and reproduced N11f."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=Path(os.environ.get('WORKSPACES',R.parent))
sys.path.insert(0,str(R/'scripts/lab'))
import abi_diff, deployed_strings_diff as strings
from generation_bundle import validate
from deploy_generation import load_package
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd):return subprocess.run(cmd,text=True,capture_output=True,check=True).stdout
def save(name,data):(H/name).write_text(json.dumps(data,indent=2)+'\n')
D=W/'westlake-inputs/generations/n11g-u9-sealed-owner-v1';new=D/'build-r2/candidate/libwestlake_android_child.z.so';n11f=D/'build-r2/baseline/libwestlake_android_child.z.so'
base=W/'westlake-generation-u9-j10g-238ffc14';old=base/'native/payload/runtime/libwestlake_android_child.z.so'
_,_,expected=validate(base);save('baseline-u9-expected.json',expected)
report={}
consumers=sorted(p for p in (base/'native/payload').rglob('*') if p.is_file() and (p.name.endswith('.so') or p.name.endswith('.z.so')))
consumers.append(base/'native/payload/runtime/appspawn-x')
for label,binary in [('deployed-u9',old),('n11f',n11f)]:
 command=[sys.executable,str(R/'scripts/lab/abi_diff.py'),'--old',str(binary),'--new',str(new),'--calls','--json',str(H/f'abi-{label}.json')]
 for p in consumers:command+=['--consumer',str(p)]
 p=subprocess.run(command,text=True,capture_output=True);(H/f'abi-{label}.txt').write_text((p.stdout+p.stderr).replace(str(W),'$WORKSPACES'));assert p.returncode==0
 report[label]=json.loads((H/f'abi-{label}.json').read_text())
elf={}
reader=os.environ.get('NATIVE_READELF','llvm-readelf')
for label,p in [('deployed-u9',old),('n11f',n11f),('candidate',new)]:
 for option,suffix in [('-dW','dynamic'),('-SW','sections'),('-rW','relocations')]:
  (H/f'{label}-{suffix}.txt').write_text(run([reader,option,str(p)]))
 elf[label]={'sha256':sha(p),'size':p.stat().st_size}
# Raw strings must be retained even when reviewed differences are acceptable.
p=subprocess.run([sys.executable,str(R/'scripts/lab/deployed_strings_diff.py'),str(new),'--deployed',str(old)],text=True,capture_output=True)
(H/'deployed-strings-raw.txt').write_text((p.stdout+p.stderr).replace(str(W),'$WORKSPACES'))
old_strings,new_strings=strings.strings(old),strings.strings(new)
critical={s:(s.encode()+b'\0') in new.read_bytes() for s in old_strings if '/system/' in s or 'WLCGATE:' in s}
assert all(critical.values()), 'deployed system path/gate string dropped'
byte_paths={s.decode():s in new.read_bytes() for s in [b'WLCGATE:PROVIDER:ENTRY_RESULT',b'/system/android/lib64/liboh_adapter_bridge.so',b'/system/android/lib64/liboh_android_runtime.so']}
assert all(byte_paths.values())
objects=json.loads((H/'build-receipt.json').read_text())['variants']
changed=[n for n in objects['candidate']['objects'] if objects['candidate']['objects'][n]!=objects['baseline']['objects'][n]]
assert changed==['sealed_child_provider_loader.o'] or set(changed)=={'sealed_child_provider_loader.o'}
assert objects['candidate']['objects']['sealed_provider_manifest.o']==objects['baseline']['objects']['sealed_provider_manifest.o']
save('elf-review.json',{'artifacts':elf,'consumer_count':len(consumers),'changed_objects':changed,'sealed_manifest_object_equal':True,'system_path_and_gate_strings_preserved':critical,'critical_bytes_preserved':byte_paths,'deployed_strings_raw_returncode':p.returncode,'added':sorted(new_strings-old_strings),'dropped':sorted(old_strings-new_strings),'ABI_calls_reports':list(report)})
# Production candidate must differ only at the child path, not at aliases/data.
_,_,candidate=validate(D/'bundle');changes={p:[expected[p],candidate[p]] for p in expected if expected[p]!=candidate[p]}
assert set(changes)=={'/system/lib64/appspawn/libwestlake_android_child.z.so'}
save('candidate-delta.json',changes)
print('consumer_count',len(consumers),'changed_objects',changed,'deployed_strings_raw_rc',p.returncode)
