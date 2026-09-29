from pathlib import Path
import json,subprocess,shutil,hashlib
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent;W=R/'bms/src/.work/b68-generation';P=W/'adapter/framework/appspawn-x/security_specialization/stock_child_plugin';G=P/'out/route-a-generation'
v=json.loads((E/'generation-verification.json').read_text());gen=v['route_a_input_generation_sha256'];base=R.parent/'westlake-generation-v2-15728be5';out=R.parent/('westlake-generation-v3-'+gen[:8]);assert not out.exists()
subprocess.run(['cp','-Rc',str(base),str(out)],check=True)
def cp(src,name):
 dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():dst.unlink()
 shutil.copy2(src,dst)
for p in (G/'providers').glob('*.so'):cp(p,'payload/route/'+p.name)
cp(G/'libwestlake_android_runtime_provider.so','payload/route/libwestlake_android_runtime_provider.so')
cp(G/'appspawn-x-stock','payload/runtime/appspawn-x');cp(P/'out/target/libwestlake_android_child.z.so','payload/runtime/libwestlake_android_child.z.so')
cp(W/'out/liboh_adapter_bridge.so','payload/android/lib64/liboh_adapter_bridge.so')
# Clear inherited v2 receipts: none of them should masquerade as v3 results.
shutil.rmtree(out/'receipts');(out/'receipts').mkdir()
for n in ['ROUTE_A_INPUTS.json','SOURCE_CLOSURE.json']:cp(P/n,'receipts/'+n);shutil.copy2(P/n,E/n)
for n in ['generation-verification.json','closure.json','provider-comparison.json','host-abi.json','child-target-verification.json']:cp(E/n,'receipts/'+n)
for n in ['deploy_generation.py','deploy_generation.sh','prepare_generation_replacement.py']:cp(R/'scripts/lab'/n,'tools/'+n)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((base/'package.json').read_text());oldgen=m['generation'];m['generation']=gen;m['previous_generation']=oldgen;m['source_commit']='c2891f11 plus task68 recorded source snapshots';m['runtime_identity']='deployment-only';m['bridge_sha256']=sha(out/'payload/android/lib64/liboh_adapter_bridge.so');m['files']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and str(p.relative_to(out)).startswith(('payload/','receipts/','tools/')) and '__pycache__' not in p.parts}
for row in m['mounts']:row['target']=row['target'].replace(oldgen,gen)
m['live_hashes']={p.replace(oldgen,gen):digest for p,digest in m['live_hashes'].items()}
for row in m['mounts']:
 if row['source'] in m['files']:m['live_hashes'][row['target']]=m['files'][row['source']]
m['live_hashes']['/system/android/lib64/liboh_adapter_bridge.so']=m['bridge_sha256']
(out/'package.json').write_text(json.dumps(m,indent=2)+'\n');(E/'package-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
(out/'README.md').write_text('Generation v3 '+gen+'\n\nRuntime loading has no file SHA admission. Use tools/deploy_generation.sh; deployment file SHA/maps checks remain mandatory. Candidate pending 5ea validation. See benchmark/2026-09-29-unlocked-generation.\n')
(E/'package-path.txt').write_text(str(out)+'\n');print(out)
