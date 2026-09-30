#!/usr/bin/env python3
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts/lab'));import lab_paths
from deploy_generation import load_package,validate_upgrade
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=sys.argv[1]
if a=='paths':
 for script in ['test_paths.py','test_musl_lookup.py']:subprocess.run([sys.executable,str(HERE/script)],check=True)
elif a=='hook':
 for cmd in [[str(HERE/'test_predeploy_hook.py')],['-m','unittest','discover','-s','scripts/lab','-p','test_deploy_frozen.py']]:subprocess.run([sys.executable,*cmd],cwd=ROOT,check=True)
elif a=='package':
 package=lab_paths.workspaces()/'westlake-generation-n5-6d001bb8';base=lab_paths.workspaces()/'westlake-generation-n4-order-216b68fb'
 m=load_package(package);old=load_package(base);validate_upgrade(old,m)
 changed={p for p,d in m['files'].items() if old['files'].get(p)!=d};assert changed=={'payload/android/lib64/libapp_native_loader.so','payload/route/libapp_native_loader.so'}
 assert set(m['files'])==set(old['files']) and m['rollout_ready'] is False
 subprocess.run([sys.executable,str(ROOT/'scripts/lab/check_frozen.py'),'--package',str(package)],check=True)
 r=subprocess.run([sys.executable,str(ROOT/'scripts/lab/native_predeploy.py'),'--package',str(package),'--inputs',str(package/'native-checks/native-gates.json'),'--gate','all','--exceptions',str(HERE.parent/'2026-10-01-n5-baseline-gates/registry-at-proposal.json')],text=True,capture_output=True)
 assert r.returncode==1,r.stderr;d=json.loads(r.stdout);assert not d['errors']
 edge=[x for x in d['gates']['N2']['details']['edges'] if x['library']=='/system/android/lib64/westlake_flutter/libandroid.so' and x['needed']=='liboh_android_runtime.so'];assert len(edge)==1 and edge[0]['resolved']=='/system/android/lib64/liboh_android_runtime.so'
 assert d['gates']['N1']['rejected']>0 and d['gates']['N2']['rejected']>0
 print('PASS package scope and honest strict rejection; NOT deployment eligible')
elif a=='handoff':
 text=(HERE/'README.md').read_text();assert 'No N5 device deployment' in text and 'REJECT' in text and '--rollback-state' in text
else:raise SystemExit('unknown check')
