from pathlib import Path
import json,hashlib,shutil,sys,subprocess
root=Path.cwd();t=root/'benchmark/2026-09-28-bms-route-deploy/latest-source-generation/task44';w=root/'bms/src/.work/b6-task44';p=root/'bms/src/.work/b6-real-work/adapter/framework/appspawn-x/security_specialization/stock_child_plugin';g=p/'out/route-a-generation';out=w/'candidate';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for f in (g/'providers').glob('*.so'):shutil.copy2(f,out/f.name)
for f,name in [(g/'appspawn-x-stock','appspawn-x'),(g/'libwestlake_android_runtime_provider.so','libwestlake_android_runtime_provider.so'),(p/'out/target/libwestlake_android_child.z.so','libwestlake_android_child.z.so')]:shutil.copy2(f,out/name)
for n in ['provider/libwestlake_android_runtime_provider.so','host/appspawn-x-stock']:assert (g/'pass1'/n).read_bytes()==(g/'pass2'/n).read_bytes()
assert (p/'out/target/pass1/libwestlake_android_child.z.so').read_bytes()==(p/'out/target/pass2/libwestlake_android_child.z.so').read_bytes()
for src,dst in [(g/'logs/host-abi-pass1.json','host-abi.json'),(p/'out/target/verification.json','child-target-verification.json')]:
 d=json.loads(src.read_text());assert d['status']=='PASS';shutil.copy2(src,t/dst)
report={'status':'PASS','scope':'real-work child target ABI, stock-host ABI and deterministic strict links; full latest00 generation verifier not reused','route_a_input_generation_sha256':sha(p/'ROUTE_A_INPUTS.json'),'stock_host_sha256':sha(out/'appspawn-x'),'child_plugin_sha256':sha(out/'libwestlake_android_child.z.so'),'runtime_provider_sha256':sha(out/'libwestlake_android_runtime_provider.so'),'libart_sha256':sha(out/'libart.so'),'libsigchain_sha256':sha(out/'libsigchain.so'),'provider_set_preserved_except_libart':True,'board_deployment':False};(t/'generation-verification.json').write_text(json.dumps(report,indent=2)+'\n')
sys.path.insert(0,str(t.parent));from audit_closure import audit
platform=json.loads((root/'bms/src/.work/b6-latest/platform-pins.json').read_text());d=audit(out,sorted(f.name for f in out.iterdir()),platform,'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf');assert d['passed'];(t/'closure.json').write_text(json.dumps(d,indent=2)+'\n')
consumer=json.loads((t/'consumer-audit.json').read_text());syms=set(consumer['missing_exports']);rows=[r for r in consumer['rows'] if 'board-consumer-scan' in r['path']]
for f in sorted(out.iterdir()):
 und=subprocess.check_output(['/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-nm','-D','--undefined-only',str(f)],text=True);names={l.split()[-1].split('@')[0] for l in und.splitlines() if l.strip()};rows.append({'path':str(f.relative_to(root)),'sha256':sha(f),'missing_export_und':sorted(syms&names)})
assert not any(r['missing_export_und'] for r in rows);consumer['rows']=rows;consumer['consumer_elf_count']=len(rows);(t/'consumer-audit.json').write_text(json.dumps(consumer,indent=2)+'\n')
print(report);print('closure',d['passed'],len(d['members']),len(d['needed_edges']))
