"""Offline U9 installer build from preserved OH 6.1 recipe; never access a board."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
W=Path(os.environ.get('WORKSPACES',R.parent))
D=W/'westlake-harness-bms-deploy';seed=D/'bms/src/.work/installer-background-launcher/adapter'
patch=R/'benchmark/2026-10-01-icon-invalid-fallback/apk_installer.cpp.patch'
source=R/'bms/src/adapter/framework/package-manager/jni/apk_installer.cpp'
out=Path(os.environ.get('U9_BUILD_OUT',W/'westlake-u9-native-build'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source)=='1ffed6bcd4941767d048988ee230577d8134fcd256055705ce104ca6a51b2730'
assert sha(patch)=='d1165c8e3e513f10473f209bc7c3015c73c0566c1a1c14892de72ce3cacf255b'
assert not out.exists();out.mkdir()
records={}
for name in ('baseline','candidate','repeat'):
 folder=out/name;adapter=folder/'adapter';shutil.copytree(seed,adapter)
 target=adapter/'framework/package-manager/jni/apk_installer.cpp'
 shutil.copy2(source,target)
 if name!='baseline':
  with (folder/'patch.log').open('w') as f:
   subprocess.run(['patch','--batch','--fuzz=0','-p4','-i',str(patch)],cwd=adapter,stdout=f,stderr=subprocess.STDOUT,check=True)
  assert sha(target)==json.loads((patch.parent/'results.json').read_text())['proposed_sha256']
 with (folder/'preserve-permissions.log').open('w') as f:
  subprocess.run(['patch','--batch','--fuzz=0','-p4','-i',str(H/'preserve-network-background.patch')],cwd=adapter,stdout=f,stderr=subprocess.STDOUT,check=True)
 assert 'MapApkNetworkPermissions(permissionManifest.usesPermissions)' in target.read_text()
 assert 'AdapterBackgroundLaunchPermissions()' in target.read_text()
 assert 'moduleJson[\"module\"][\"requestPermissions\"] = requests' in target.read_text()
 env=os.environ.copy();env.update(BUILD_INNER_INVOKED='1',OH_ROOT=str(W/'oh61-bms-kit'),ADAPTER_ROOT=str(adapter),APK_INSTALLER_BUILD_TMP=str(folder/'objects'))
 sdk=Path(os.environ.get('U9_SDK',Path.home()/'a2hlab/ws/toolchains/ohos-sdk/native/llvm'))
 env['LD_LIBRARY_PATH']=str(sdk/'lib')
 with (folder/'build.log').open('w') as f:
  subprocess.run(['bash',str(adapter/'build/inner/compile_apk_installer.sh')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 errors=[p for p in (folder/'objects').glob('*.err') if 'error:' in p.read_text(errors='replace')]
 assert not errors,[str(p) for p in errors]
 binary=adapter/'out/adapter/libapk_installer.so';subprocess.run([str(sdk/'bin/llvm-strip'),'--strip-unneeded',str(binary)],check=True)
 shutil.copy2(binary,folder/'libapk_installer.so')
 records[name]={'source_sha256':sha(target),'sha256':sha(binary),'recipe_sha256':sha(adapter/'build/inner/compile_apk_installer.sh'),'objects':{p.name:sha(p) for p in (folder/'objects').glob('*.o')}}
 (out/'partial-receipt.json').write_text(json.dumps(records,indent=2)+'\n')
 print(name,sha(binary),flush=True)
 if name=='repeat':assert records[name]['sha256']==records['candidate']['sha256']
records['tools']={'clang_sha256':sha(sdk/'bin/clang'),'strip_sha256':sha(sdk/'bin/llvm-strip'),'patch_sha256':sha(patch),'seed_source_sha256':records['baseline']['source_sha256'],'input_files':{str(p.relative_to(seed)):sha(p) for p in seed.rglob('*') if p.is_file()}}
(out/'build-receipt.json').write_text(json.dumps(records,indent=2)+'\n')
