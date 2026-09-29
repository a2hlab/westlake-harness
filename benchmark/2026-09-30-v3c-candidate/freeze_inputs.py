#!/usr/bin/env python3
"""Pin local, read-only handoff inputs. No device commands."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
W=Path('/Users/zhaoyue/orca/workspaces')
D=W/'westlake-harness-bms-deploy'
B=W/'westlake-harness-b4'
BASE=W/'westlake-generation-b87-vt-c835a93e'
CE=W/'westlake-jni-gapfill-c5ed50d5/package-61b-ce-9e14bf20'
B92=W/'westlake-b92-bigstack-0509fe23'
B93=W/'westlake-b93-tls-html-9c0f8d38-26ac847b'
BI=B/'bms/src/adapter/framework/native-compat/westlake-bionic'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def commit(repo,c):return subprocess.check_output(['git','-C',str(repo),'rev-parse',c+'^{commit}'],text=True).strip()
def row(name,p,prefix,repo,commits,source,recipe,order):
 h=sha(p)
 if not h.startswith(prefix):raise ValueError((name,h,prefix))
 return dict(name=name,path=str(p),sha256=h,source_repository=str(repo),source_commits=[commit(repo,c) for c in commits],source_paths=[str(repo/s) for s in source],recipe=str(recipe),order=order)
r=[]
r.append(row('appspawn-x',CE/'payload/runtime/appspawn-x','d977bd15',D,['2e5bdd73'],['benchmark/2026-09-29-wikipedia-line/network-groups/appspawn_service.c'],D/'benchmark/2026-09-29-wikipedia-line/network-groups/build-inet.sh',0))
r.append(row('liblog.so',BASE/'payload/android/lib64/liblog.so','8c81a937',D,['e90e0b29'],['benchmark/2026-09-29-native-abi-port'],D/'benchmark/2026-09-29-native-abi-port/build-log-bionic.sh',1))
for n,prefix,c,src in [('libc.so','ee6034f5',['08b59282','ec342e3e'],['bionic_assert_compat.c','bionic_stdio_compat.c','malloc_compat.cpp','android_native_network_compat.c','bionic-abi.map']),('libGLESv2.so','befb6ec7',['ec342e3e'],['libglesv2_shim.c']),('libstdc++.so','7e06cd8b',['3302406b'],['libstdcxx_shim.c']),('libOpenSLES.so','5891f899',['3302406b'],['opensles_android_compat.c'])]:
 r.append(row(n,BI/'build'/n,prefix,B,c,[str((BI/s).relative_to(B)) for s in src],BI/'build.sh',len(r)))
for n,prefix in [('libapp_native_loader.so','a9c9187d'),('libwestlake_android_runtime_provider.so','0509fe23')]:
 r.append(row(n,B92/'payload/route'/n,prefix,D,['d8d7a3e0'],['benchmark/2026-09-30-child-stack-default', 'bms/src/adapter/framework/app-native-loader/src/app_native_loader.c' if n=='libapp_native_loader.so' else 'bms/src/adapter/framework/appspawn-x/src/child_main_after_stock.cpp'],D/('benchmark/2026-09-30-child-stack-default/build-anl.sh' if n=='libapp_native_loader.so' else 'benchmark/2026-09-30-child-stack-default/build-provider.sh'),len(r)))
r.append(row('liboh_android_runtime.so',W/'westlake-b91-commonevent-9e14bf20/liboh_android_runtime.so','9e14bf20',D,['f6a60fc0','4cf55d40','dc3b3756'],['bms/src/adapter/framework/native-compat/westlake-commonevent','benchmark/2026-09-30-commonevent-registration'],D/'benchmark/2026-09-30-commonevent-registration/build.sh',len(r)))
r.append(row('liboh_tls_boundary.so',W/'vm-copies/tls-boundary-39c2cfe9/liboh_tls_boundary.so','39c2cfe9cb830f08',B,['7e511ad0'],['bms/src/adapter/framework/native-compat/westlake-tls'],B/'bms/src/adapter/framework/native-compat/westlake-tls/build.sh',len(r)))
held_html=row('libwestlake_html_compat.so',B93/'2-html/payload/android/lib64/libwestlake_html_compat.so','26ac847b',B,['fe153eb8'],['benchmark/2026-09-29-westlake-port/html-compat'],B/'benchmark/2026-09-29-westlake-port/html-compat/build.sh',len(r))
r.append(row('libwestlake_jni_gapfill.so',W/'vm-copies/jni-gapfill-d1a1961d/libwestlake_jni_gapfill.so','d1a1961d7682a482',B,['56b5295c'],['benchmark/2026-09-29-westlake-port/jni-gapfill'],B/'benchmark/2026-09-29-westlake-port/jni-gapfill/build.sh',len(r)))
boards={
 '5ea':dict(serial='5ea34a4500000000000000001123012c',package=W/'westlake-b93-tls-39c2cfe9-5ea',fingerprint=W/'westlake-harness-wiki/benchmark/2026-09-29-wikipedia-line/runs/outer-tls39c-r17e/5ea34a4500000000000000001123012c/runtime-fingerprint.txt'),
 '5cd':dict(serial='5cd1e3dd00000000000000000923012c',package=W/'westlake-jni-gapfill-c5ed50d5/package-5cd',fingerprint=W/'westlake-harness/benchmark/2026-09-30-r17c-sweep/runs/r17c-all-5cd/5cd1e3dd00000000000000000923012c/runtime-fingerprint.txt'),
 '61b':dict(serial='61b0657200000000000000000324012c',package=CE,fingerprint=D/'benchmark/2026-09-30-commonevent-registration/evidence-61b/apps/runtime-fingerprint.txt')}
for k,b in boards.items():
 b['package_sha256']=sha(b['package']/'package.json');b['fingerprint_sha256']=sha(b['fingerprint'])
 b['fingerprint_snapshot']='evidence/'+k+'-runtime-fingerprint.txt';(HERE/b['fingerprint_snapshot']).write_bytes(b['fingerprint'].read_bytes())
 b['manifest_snapshot']='evidence/'+k+'-resident-package.json';(HERE/b['manifest_snapshot']).write_bytes((b['package']/'package.json').read_bytes())
 b['package']=str(b['package']);b['fingerprint']=str(b['fingerprint'])
for a in r:
 a['source_paths_exist']=all(Path(p).exists() for p in a['source_paths'])
 a['recipe_exists']=Path(a['recipe']).is_file()
 a['recipe_sha256']=sha(a['recipe']) if a['recipe_exists'] else None
 files=set()
 for source in a['source_paths']:
  root=Path(source)
  files.update([root] if root.is_file() else (p for p in root.rglob('*') if p.is_file() and p.suffix in {'.c','.cpp','.h','.sh','.patch','.map'}))
 a['source_snapshot']={str(p):sha(p) for p in sorted(files)}
 a['build_recipe_status']='recorded'
 if a['name'] in {'liboh_tls_boundary.so','libwestlake_jni_gapfill.so'}:
  a['build_recipe_status']='new static-link recipe not yet present in Mac source; old source bodies and recipe recorded, new build commit unknown'
  a['new_link_recipe_commit']=None
  a['announced_link_change']='separate object compile + -l:libc++.a -l:libc++abi.a; see outer-steering.txt'
 recipe_copy=HERE/'evidence'/('recipe-'+a['name']+'.sh')
 recipe_copy.write_bytes(Path(a['recipe']).read_bytes())
 if not a['source_paths_exist'] or not a['recipe_exists']:raise ValueError('missing provenance: '+a['name'])
archive=D/'benchmark/2026-09-29-native-abi-port/archive.json'
(HERE/'evidence/b87-build-archive.json').write_bytes(archive.read_bytes())
board_path=W/'westlake-harness/.octos/boards/app-lighting.md'
selected=[line for line in board_path.read_text(errors='replace').splitlines() if ('外环' in line and ('HTML' in line or '_Znwm' in line)) or ('02:14:19' in line) or ('02:20:41' in line)]
(HERE/'evidence/outer-steering.txt').write_text('\n'.join(selected[-5:])+'\n')
out=dict(schema=1,base=str(BASE),base_manifest_sha256=sha(BASE/'package.json'),artifacts=r,boards=boards,tools={p.name:sha(p) for p in (HERE/'tools').glob('*.py')},excluded=[dict(**held_html,reason='Outer 02:14+ paused HTML; removed from 5ea. Excluded from deployable payload; no load or function acceptance.'),dict(name='libnativeloader.so',candidate_prefix='76092855',reason='Latest cx-t0 handoff selects Java namespace mainline; retain fde6f31c'),dict(name='liblog.so',candidate_prefix='cf6f9d8c',reason='Old weak b4 build; retain measured B87 8c81a937')])
(HERE/'inputs.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'artifacts':len(r),'missing_sources':[a['name'] for a in r if not a['source_paths_exist']], 'missing_recipes':[{k:a[k] for k in ['name','recipe']} for a in r if not a['recipe_exists']]},indent=2))
