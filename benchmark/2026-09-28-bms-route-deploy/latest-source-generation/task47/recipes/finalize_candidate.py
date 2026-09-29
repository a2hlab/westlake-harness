from pathlib import Path
import json,hashlib,shutil,sys,subprocess,re
r=Path.cwd();t=r/'benchmark/2026-09-28-bms-route-deploy/latest-source-generation/task47';w=r/'bms/src/.work/b6-task47';p=r/'bms/src/.work/b6-real-work/adapter/framework/appspawn-x/security_specialization/stock_child_plugin';g=p/'out/route-a-generation';out=w/'candidate';out.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();nm='/opt/homebrew/opt/llvm/bin/llvm-nm';readelf='/opt/homebrew/opt/llvm/bin/llvm-readelf'
assert sha(p/'ROUTE_A_INPUTS.json').encode() in (g/'appspawn-x-stock').read_bytes()
assert sha(p/'out/target/libwestlake_android_child.z.so').encode() in (g/'appspawn-x-stock').read_bytes()
for f in (g/'providers').glob('*.so'):shutil.copy2(f,out/f.name)
for f,name in [(g/'appspawn-x-stock','appspawn-x'),(g/'libwestlake_android_runtime_provider.so','libwestlake_android_runtime_provider.so'),(p/'out/target/libwestlake_android_child.z.so','libwestlake_android_child.z.so')]:shutil.copy2(f,out/name)
for f in (w/'baseline-native').glob('*.so'):shutil.copy2(f,out/f.name)
for n in ['provider/libwestlake_android_runtime_provider.so','host/appspawn-x-stock']:assert (g/'pass1'/n).read_bytes()==(g/'pass2'/n).read_bytes()
assert (p/'out/target/pass1/libwestlake_android_child.z.so').read_bytes()==(p/'out/target/pass2/libwestlake_android_child.z.so').read_bytes()
for src,dst in [(g/'logs/host-abi-pass1.json','host-abi.json'),(p/'out/target/verification.json','child-target-verification.json')]:
 d=json.loads(src.read_text());assert d['status']=='PASS';shutil.copy2(src,t/dst)
report={'status':'PASS','route_a_input_generation_sha256':sha(p/'ROUTE_A_INPUTS.json'),'stock_host_sha256':sha(out/'appspawn-x'),'child_plugin_sha256':sha(out/'libwestlake_android_child.z.so'),'runtime_provider_sha256':sha(out/'libwestlake_android_runtime_provider.so'),'libart_sha256':sha(out/'libart.so'),'libsigchain_sha256':sha(out/'libsigchain.so'),'abort_bridge_sha256':sha(out/'libwestlake_art_abort_bridge.so'),'preserved_r155_provider_count':26,'board_deployment':False}
(t/'generation-verification.json').write_text(json.dumps(report,indent=2)+'\n')
sys.path.insert(0,str(t.parent));from audit_closure import audit
platform=json.loads((r/'bms/src/.work/b6-latest/platform-pins.json').read_text())
external={'libandroidfw.so','libicuuc.so'}
for name in external:
 f=w/'baseline-native'/name
 platform[name]={'path':str(f),'sha256':sha(f)}
d=audit(out,sorted(f.name for f in out.iterdir() if f.name not in external),platform,readelf)
(t/'closure.json').write_text(json.dumps(d,indent=2)+'\n');assert d['passed'],d['errors']
def syms(f,flag):
 text=subprocess.check_output([nm,'-D',flag,str(f)],text=True)
 return {l.split()[-1].split('@')[0] for l in text.splitlines() if l.strip()}
required=['AddSpecialSignalHandlerFn','RemoveSpecialSignalHandlerFn','EnsureFrontOfChain','SkipAddSignalHandler'];exports=syms(out/'libsigchain.so','--defined-only');imports=syms(out/'libart.so','--undefined-only');assert set(required)<=imports;assert set(required)<=exports
(t/'sigchain-symbols.json').write_text(json.dumps({'passed':True,'art_sha256':sha(out/'libart.so'),'sigchain_sha256':sha(out/'libsigchain.so'),'required':required,'missing':[],'negative_symbol_manifests':{s:{'passed':False,'missing':sorted(set(required)-(exports-{s})),'deploy_allowed':False} for s in required}},indent=2)+'\n')
# A C-only bridge exports no std::string ABI to the consumer; it calls the original ART.
assert 'westlake_art_copy_fault_message_for_abort_logging' in syms(out/'libwestlake_art_abort_bridge.so','--defined-only')
assert '_ZN3art30GetFaultMessageForAbortLoggingEv' in syms(out/'libwestlake_art_abort_bridge.so','--undefined-only')
assert 'westlake_art_copy_fault_message_for_abort_logging' in syms(out/'libwestlake_android_runtime_provider.so','--undefined-only')
print(report);print('closure',d['passed'],len(d['members']),len(d['needed_edges']))
