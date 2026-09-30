#!/usr/bin/env python3
"""Export a single-runtime replacement package; no device operations."""
import hashlib,json,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths
from prepare_generation_replacement import prepare
W=lab_paths.workspaces();base=W/'westlake-generation-n3-8a7880fa';stage=W/'westlake-generation-n3b-candidate'
lib=R/'bms/src/.work/n3b-webview/runtime-out/liboh_android_runtime.so'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=json.loads((P/'build-results.json').read_text());assert build['baseline_bit_identical']
assert sha(lib)==build['candidate_sha256']
prepare(base,'/system/android/lib64/liboh_android_runtime.so',lib,sha(lib),stage)
h=sha(stage/'package.json');out=W/('westlake-generation-n3b-'+h[:8])
if out.exists():raise RuntimeError('immutable export exists: '+str(out))
subprocess.run(['/bin/cp','-Rc',str(stage),str(out)],check=True)
(P/'package.json').write_text(json.dumps({'base':str(base),'base_manifest_sha256':sha(base/'package.json'),'package':str(out),'manifest_sha256':h,'runtime_sha256':sha(lib),'replace_target':'/system/android/lib64/liboh_android_runtime.so','device_status':'unverified','rollout_ready':False,'java_and_provider_inputs':'not bundled; pending cc-t3 integration'},indent=2)+'\n')
print(out)
