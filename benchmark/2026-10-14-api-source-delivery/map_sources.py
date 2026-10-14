#!/usr/bin/env python3
"""Additive315-row source/build audit. Never executes a recipe or alters source files."""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE_EXT={'.java','.cpp','.c','.h','.hpp','.inc','.cc','.rs','.js'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(main,out,revision=None):
 main=main.resolve();ws=main.parent;delivery=HERE.parents[1];out.mkdir(parents=True,exist_ok=False);(out/'recipes').mkdir()
 def git(*args):return subprocess.check_output(['git','-C',str(main),*args])
 commit=revision or git('rev-parse','master').decode().strip();assert re.fullmatch('[0-9a-f]{40}',commit);git('merge-base','--is-ancestor',commit,'master');tree={}
 for line in git('ls-tree','-rz','--full-tree',commit).split(b'\0'):
  if line:
   meta,path=line.split(b'\t',1);tree[path.decode()]=meta.decode().split()[2]
 def portable(p):
  p=Path(p).resolve()
  return str(p.relative_to(main)) if p.is_relative_to(main) else str(p.relative_to(delivery)) if p.is_relative_to(delivery) else '$WORKSPACES/'+str(p.relative_to(ws)) if p.is_relative_to(ws) else str(p)
 def pin(p):return {'path':portable(p),'sha256':sha(p)}
 def load(p):return json.loads(Path(p).read_text())
 def resolve(p):return Path(p.replace('$WORKSPACES',str(ws)).replace('$REPO',str(main))) if p.startswith('$') else main/p
 source=main/'benchmark/2026-10-14-api-progress-final61b/views/api-progress.json';data=load(source);assert len(data['rows'])==315
 def source_pin(p,role='source_candidate',expected=None):
  p=Path(p);r=pin(p);raw=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();relative=portable(p);r.update(git_blob=blob,master_tracked=tree.get(relative)==blob,master_blob=tree.get(relative),role=role,expected_sha256=expected,exact_expected_match=(sha(p)==expected if expected else None))
  header=raw[:12000].decode(errors='replace');lic='license_header_present' if any(x in header for x in ['Apache License','SPDX-License-Identifier','GNU General Public','Permission is hereby granted']) else 'unknown_needs_license_review'
  r['license_status']=lic;return r
 java_path=HERE/'frozen-inputs/java-source-resolutions.json'
 if not java_path.exists():java_path=main/'benchmark/2026-10-14-api-source-delivery/review/java-source-resolutions.json'
 java_resolutions={r['id']:r for r in load(java_path)['rows']} if java_path.exists() else {}
 java115_path=main/'benchmark/2026-10-14-api-source-delivery/review/java115-resolution.json'
 j115=load(java115_path);j115['limits']=j115['limitations'];java_resolutions['JAVA-115']=j115
 resolutions_path=HERE/'review/native-source-resolutions.json'
 resolutions={r['id']:r for r in load(resolutions_path)['rows']} if resolutions_path.exists() else {}
 late_path=main/'sources/api-implementations/source-build-native691/api-resolutions.json'
 if not late_path.exists():late_path=delivery/'sources/api-implementations/source-build-native691/api-resolutions.json'
 if late_path.exists():resolutions.update({r['id']:r for r in load(late_path)['rows']})
 recipes={};rows=[]
 aliases={'JAVA-001':'REG-007','JAVA-002':'REG-007','JAVA-003':'REG-007','JAVA-004':'REG-007','JAVA-005':'REG-007','JAVA-038':'REG-001','JAVA-039':'REG-001'}
 j7_helpers={'JAVA-006':'AppWidgetFetcher.java','JAVA-007':'VibratorFetcher.java','JAVA-008':'WifiFetcher.java','JAVA-009':'LocalServiceBinders.java','JAVA-010':'WlSearchService.java','JAVA-011':'WlWallpaperColors.java'}
 aliases.update({k:'REG-006' for k in j7_helpers})
 native_summary=main/'benchmark/2026-10-14-api-source-delivery/frozen/source-summary.json'
 ns={x['id']:x for x in load(native_summary)['entries']} if native_summary.exists() else {}
 extracted=main/'benchmark/2026-10-14-api-source-delivery/frozen/extracted-files.json';native=load(extracted).get('entries',{}) if extracted.exists() else {}
 tagmatch=main/'benchmark/2026-10-14-api-source-delivery/tagsoup/source-match.json';tag=load(tagmatch) if tagmatch.exists() else {}
 def unknown_recipe(rid,evidence):return {'id':rid,'status':'UNKNOWN_EXACT_BUILD_ENTRY','entry':None,'command':{'status':'unknown','argv':None,'working_directory':None,'notes':'No command invented from source presence.'},'dependencies':{'status':'unknown','entries':[],'gaps':['Complete producing inputs/toolchain not established.']},'outputs':{'status':'unknown','entries':[]},'verification':{'status':'unknown','evidence':evidence,'executed_this_audit':False,'gaps':['No paired actual producing receipt established.']}}
 def recipe_for(row,entries):
  rid=aliases.get(row['id'],row['id']);loc=row['source_location'];refs=[x for x in row.get('evidence',[]) if Path(x['path']).suffix in ['.json','.md']]
  key='unknown-'+hashlib.sha256(loc.encode()).hexdigest()[:12];r=unknown_recipe(key,refs)
  if row['id'] in java_resolutions:
   d=java_resolutions[row['id']];key='java-reviewed-'+row['id'];r=unknown_recipe(key,[pin(java115_path if row['id']=='JAVA-115' else java_path)])
   r['status']='MEMBER_REVIEWED_SOURCE_BUILD_LOCATOR';builds=[main/p for p in d['build_recipe']];r['entry']=next((pin(p) for p in builds if p.suffix in ['.py','.sh']),None);r['recipe_documents']=[pin(p) for p in builds]
   r['dependencies']['gaps']=d['limits'];r['verification']['gaps']=d['limits'];r['verification']['status']='ACTUAL_MEMBER_SOURCE_REVIEW_NOT_BUILD_RECEIPT'
   if d.get('build_lock'):
    lockpath=main/d['build_lock'];r['dependencies']['entries']=[pin(lockpath)]
   if row['id']=='JAVA-115':
    assert d['cli_help_rc']==0 and all(x['passed'] for x in d['offline_actual_ast_checks'])
    r['command']={'status':'INTERPRETED_LAUNCHER_INTERFACE_CHECK','argv':d['build_command']['argv'],'working_directory':'$REPO','notes':d['build_command']['scope']}
    r['dependencies']['entries']+=d['build_dependencies']
    r['outputs']={'status':'INTERPRETED_SOURCE_NO_COMPILED_ARTIFACT','entries':[]}
    r['verification']={'status':'FOUR_NORMALIZER_CASES_AND_HELP_RC0','normalizer_cases':4,'help_rc':0,'historical_exact_binding':False,'current_deployment':False,'evidence':[pin(java115_path)],'executed_this_audit':False,'gaps':d['limitations']}
   if any(p.name=='build-java.py' for p in builds):
    r['command']={'status':'DELIVERED_ACTUAL_SOURCE_COMPILER','argv':['python3','sources/api-implementations/source-build-host/build-java.py','--workspace','$RESTORED_SOURCE_WORKSPACE','--core-build','$CORE_JAVA_BUILD','--framework-build','$FRAMEWORK_JAVA_BUILD','--core-extension-build','$JAVA_EXTENSIONS_BUILD','--out','$FRESH_OUTPUT'],'working_directory':'$REPO','notes':'New class JAR only; no historical DEX or deployed-byte equivalence.'}
    br=main/'benchmark/2026-10-14-api-source-delivery/review/later-java-build-01.json'
    if br.exists():
     actual=load(br);assert actual['status']=='NEW_ADAPTER_JAVA_BUILD_PASS' and actual['exit_code']==0
     for e in entries:
      rel=e['path'].split('/westlake-java/',1)[1];assert actual['actual_source_input_sha256'].get(rel)==e['sha256'],rel
     r['outputs']={'status':'NEW_CLASS_JAR_NOT_DEPLOYABLE','entries':[{'name':'westlake-unrelocated.classes.jar',**actual['artifact']}]}
     r['verification']={'status':'NEW_ADAPTER_JAVA_BUILD_PASS','exit_code':0,'source_input_count':83,'owned_class_count':160,'historical_r84_r89_output_equivalent':False,'deployable_runtime_jar':False,'new_dex_or_boot_image_built':False,'evidence':[pin(br),pin(br.with_name('later-java-build-01-archive.json'))],'executed_this_audit':False,'gaps':['New javac class JAR is not the historical runtime JAR/DEX or deployment identity.']}
     r['dependencies']['gaps']=['External locked JDK/AOSP and prerequisite class artifacts are required.'];r['status']='NEW_ADAPTER_JAVA_BUILD_PASS'
   recipes[key]=r;return r
  if row['id'] in resolutions:
   d=resolutions[row['id']];key='reviewed-'+row['id'];rp=late_path if d.get('source_revision')=='691433b967ba01365a382d30fbd820c1231c0811' else resolutions_path;r=unknown_recipe(key,[pin(rp)])
   r.update(entry=d['build_entry'],status='REVIEWED_CODE_AND_RECIPE_SCOPE_PARTIAL',command=d['command'])
   r['dependencies']['gaps']=[d['scope']];r['verification']['gaps']=[d['scope'],d['production_binary_equivalence']]
   if rp==late_path:
    root=late_path.parent;locks=main/'sources/api-implementations/source-build-host/manifest-tools'
    r['dependencies']={'status':'DELIVERED_NATIVE_INPUTS_EXTERNAL_AOSP_OH_SDK_LOCKS','entries':[pin(root/'sources.lock.json')]+[pin(locks/n) for n in ['upstream.lock.json','toolchains.lock.json','native-sources.lock.json'] if (locks/n).is_file()],'gaps':['External AOSP libcore/libnativehelper/expat and OH SDK compiler/sysroot/CRT are not vendored by this package. Their exact historical producing hashes remain unproven.']}
    r['outputs']={'status':'DECLARED_NEW_BUILD_OUTPUTS_NOT_EXECUTED','entries':[{'name':n,'sha256':None} for n in (['libwl_missing_natives.so'] if d['build_entry']['path'].endswith('build_missing_natives.sh') else ['libwebview_bionic_shim.so','libaaudio.so'])]}
    r['verification']['status']='EXACT_SOURCE_GIT_BLOBS_AND_RECIPE_SYNTAX_PASS_NO_NATIVE_BUILD';r['verification']['evidence'].append(pin(root/'results.json'))

   if row['id'] in ['NATIVE-115','NATIVE-116']:
    r['dependencies']['entries']=[pin(delivery/'sources/api-implementations/native-sqlite187/source.json'),pin(main/'benchmark/2026-10-10-adapter-buildchain/runtime-persistence.json')]
    r['outputs']={'status':'ORIGINAL_RUNTIME_EXPECTATION','entries':[{'name':'liboh_android_runtime.so','sha256':'18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae'}]}
    r['verification']={'status':'EXISTING_TWO_SOURCE_BUILDS_EQUAL','evidence':[pin(main/'benchmark/2026-10-10-adapter-buildchain/runtime-reproduction.json')],'executed_this_audit':False,'gaps':['Full restored external6347-input closure remains required; this source delivery is8 units.']}
   recipes[key]=r;return r
  # Frozen family packages are delivered by native lanes, consumed without source searching.
  if re.fullmatch(r'REG-00[1-8]',rid):
   n=int(rid[-3:]);key=f'FZ-{n:03d}';root=main/'sources/api-implementations'/('FZ-007-tagsoup' if n==7 else key);r=unknown_recipe(key,[])
   build_refs=[p for p in root.rglob('*') if p.is_file() and (p.name in ['build.py','BUILD.md'] or 'build-evidence' in p.parts) and (p.suffix in ['.json','.md','.txt'] or p.name=='build.py')]
   r['verification']['evidence']=[pin(p) for p in sorted(build_refs) if p.suffix=='.json'];r['dependencies']['entries']=[pin(p) for p in sorted(build_refs) if any(x in p.name for x in ['toolchain','source-link','manifest','sources.lock','dependencies.lock'])];r['status']='NATIVE_DELIVERY_SOURCE_AND_HISTORICAL_RECIPE';r['entry']=pin(root/'build.py') if (root/'build.py').is_file() else next((pin(p) for p in build_refs if p.name=='BUILD.md'),None)
   r['verification']['gaps']=['Native package source and original build scope require its independent review; no build executed by this mapper.'];r['recipe_documents']=[pin(p) for p in build_refs if 'build' in p.name.lower()]
   if n in [1,2,3,4,5,6,8] and key in ns:
    delivered=ns[key]; entry=main/delivered['build_entry']; r['entry']=pin(entry)
    required={1:['OH_ROOT','AOSP_ROOT','BUILD_OUT'],2:['GENERATION','FRESH_OUT'],3:['ADAPTER_ROOT','AOSP_ROOT','OH_ROOT','AOSP_LIB_DIR','BUILD_OUT'],4:['BUILD_OUT'],5:['AOSP_R1_ROOT','JARS_DIR','OUT_DIR','BOARD_LIBART','T5C_DIR'],6:['ANDROID_JAR','BUILD_OUT'],8:['BUILD_OUT']}[n]
    r['command']={'status':'DELIVERED_BUILD_ENTRY_NOT_EXECUTED_THIS_AUDIT','argv':(['python3',portable(entry),'--generation','$GENERATION','--out','$FRESH_OUT','--run'] if n==2 else ['bash',portable(entry)]),'environment':{v:'$'+v for v in required},'working_directory':'$REPO','notes':'Read BUILD.md and supply exact pinned dependencies in a fresh scratch tree. API-unit build is not whole production artifact reproduction.'}
    r['dependencies']['status']='DOCUMENTED_EXTERNAL_DEPENDENCIES_PARTIAL_CLOSURE';r['dependencies']['entries'] += [pin(root/'BUILD.md'),pin(native_summary)]
    r['dependencies']['gaps']=delivered['gaps'];r['verification']['gaps']=delivered['gaps'];r['verification']['evidence'].append(pin(native_summary));r['verification']['status']='SOURCE_UNIT_DELIVERED_NO_NEW_BUILD_CLAIM'
    names={1:'archived installer translation units; BMS separate original ninja',2:'libwestlake_android_runtime_provider.so',3:'runtime including AssetManager unit',4:'JarVerificationProviderFix.class',5:'dex2oat64 and optional 27-file boot image',6:'VibratorFetcher.class',8:'android/net/ssl/SSLSockets.class'}
    r['outputs']={'status':'DECLARED_BUILD_SCOPE','entries':[{'name':names[n],'sha256':('0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c' if n==2 else 'ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b' if n==5 else None),'hash_scope':'expected historical output' if n in [2,5] else 'unknown new build output'}]}
   full_results=main/'benchmark/2026-10-14-api-source-delivery/full-jar/results.json'
   if n in [4,6] and full_results.exists():
    fb=root/'full-jar';result=next(x for x in load(full_results)['builds'] if x['id']==key)
    assert result['producer_rc']==0 and result['wrapper_rc']==2 and not result['output_matches_historical']
    r['unit_build_entry']=r['entry'];r['unit_build_command']=r['command'];r['entry']=pin(fb/'build.py')
    r['status']='COMPLETE_OVERLAY_PRODUCER_DELIVERED_HISTORICAL_BYTES_DIFFER'
    r['command']={'status':'ACTUAL_OVERLAY_BUILD_ENTRY_STRICT_HISTORICAL_REJECTION','argv':['python3',portable(fb/'build.py'),'--inputs','$PINNED_JAR_INPUTS','--out','$FRESH_OUT','--run'],'working_directory':'$REPO','notes':'Fetch/verify the14 pinned jars first. Full overlay producer, not full baseline source build. Actual producer rc0; strict wrapper rc2 for changed DEX/whole JAR.'}
    r['dependencies']={'status':'PINNED_COMPLETE_OVERLAY_INPUTS_BASELINE_BINARY','entries':[pin(fb/'sources.lock.json'),pin(fb/'dependencies.lock.json'),pin(fb/'fetch-dependencies.py')],'gaps':['Baseline JAR remains binary input; original historical stdout/stderr not recovered.']}
    r['outputs']={'status':'NEW_BUILD_AND_HISTORICAL_DISTINCT','entries':[{'name':'historical_jar','sha256':result['historical_output_sha256']},{'name':'new_jar','sha256':result['output_sha256']},{'name':'historical_classes.dex','sha256':result['historical_dex_sha256']},{'name':'new_classes.dex','sha256':result['new_dex_sha256']}]}
    r['verification']={'status':'PRODUCER_RC0_WRAPPER_RC2_DEX_AND_JAR_DIFFER','producer_rc':0,'wrapper_rc':2,'historical_dex_equal':False,'historical_jar_equal':False,'evidence':[pin(full_results),pin(full_results.parent/'build-comparison.json'),pin(full_results.parent/(key+'-execution.json')),pin(full_results.parent/'archive-verification.json')],'executed_this_audit':False,'gaps':['Byte-difference root cause unknown; no equivalent frozen artifact or recovered historical build logs asserted.']}
   if n==7:
    deps=load(root/'dependencies.lock.json');lock=load(root/'t7d-sources.lock.json');r['dependencies']={'status':'PINNED_125_SOURCES_PLUS_EXTERNAL_CLASSPATH','entries':[pin(root/'dependencies.lock.json'),pin(root/'t7d-sources.lock.json')],'gaps':['Pinned external compile-only jars/R8 and Java toolchain must be supplied.']};r['command']={'status':'EXISTING_BUILD_ENTRY','argv':['python3','sources/api-implementations/FZ-007-tagsoup/build.py','--mode','t7d','--dependencies','$A2HLAB_WS','--out','$FRESH_OUT'],'working_directory':'$REPO','notes':'Fresh output only; original T7d build log not recreated retroactively.'};r['outputs']={'status':'HISTORICAL_EXPECTATIONS','entries':[{'name':'historical_t7d_jar','sha256':deps['historical_jar_sha256']},{'name':'historical_classes.dex','sha256':deps['historical_dex_sha256']}]};vr=main/'benchmark/2026-10-14-api-source-delivery/tagsoup/new-t7d-container.json'
    br=main/'benchmark/2026-10-14-api-source-delivery/tagsoup/t7d-build-receipt.json'
    if br.exists():
     actual=load(br);assert actual['status']=='PASS' and all(x['rc']==0 for x in actual['steps'])
     assert actual['historical_dex_equal'] and actual['dex_sha256']==deps['historical_dex_sha256']
     assert actual['historical_jar_equal'] is False and actual['artifact']['sha256']!=deps['historical_jar_sha256']
     r['verification']={'status':'NEW_SOURCE_BUILD_DEX_EQUAL_JAR_NOT_EQUAL','evidence':[pin(br),pin(vr),pin(tagmatch)],'executed_this_audit':False,'historical_dex_equal':True,'historical_jar_equal':False,'compiled_class_files':actual['compiled_class_files'],'historical_build_receipt_recovered':False,'gaps':['This is a new native-lane build with original new stdout/stderr; old producing stdout/stderr remains unknown. ZIP wrapper does not reproduce historical JAR bytes.']}
     r['outputs']['entries'] += [actual['artifact'],{'name':'new_classes.dex','sha256':actual['dex_sha256']}]
     for name in ['archive.json','archive-results.json']:
      archive=br.parent/name
      if archive.exists():r['verification']['evidence'].append(pin(archive))
   recipes[key]=r;return r
  if rid=='NATIVE-173':
   key='runtime-f28';root=main/'benchmark/2026-10-13-runtime-surfaceview-split';receipt=ws/'westlake-inputs/generations/boat-v2-runtime-f28bd1b3-20261013/receipt.json';d=load(receipt);r=unknown_recipe(key,[pin(receipt)]);r.update(status='EXISTING_COLD_SOURCE_BUILD_RC0',entry=pin(root/'build_candidate.py'));r['command']={'status':'EXISTING_BUILD_ENTRY','argv':['python3','benchmark/2026-10-13-runtime-surfaceview-split/build_candidate.py'],'working_directory':'$REPO','notes':'Requires retained original source layout, pinned Docker image and sibling dependency trees; creates a fresh .artifacts/cold-* output. Not executed here.'};r['dependencies']={'status':'PINNED_EXTERNAL_SOURCE_TOOLCHAIN_CLOSURE','entries':[d['original_source_archive'],d['closure_before']['inventory'],d['clang'],{'container_image':d['container_image']}],'gaps':['Dependencies are archived, not all supplied as source files on master.']};r['outputs']={'status':'ACTUAL_OUTPUT','entries':[d['candidate']]};r['verification']={'status':'ORIGINAL_COLD_RC0','evidence':[pin(receipt),pin(root/'evidence/build-provenance.json')],'executed_this_audit':False,'gaps':[]};recipes[key]=r;return r
  if '2026-10-02-u12-mediandk/candidate.c' in loc:
   key='u12-mediandk8fc';bp=main/'benchmark/2026-10-02-u12-mediandk/build-receipt.json';d=load(bp);r=unknown_recipe(key,[pin(bp)]);r.update(status='EXISTING_COMPILER_ARGV',entry=None,recipe_documents=[pin(bp)]);r['command']={'status':'EXACT_RECORDED_COMPILER_ARGV','argv':d['commands'][0]['command'],'working_directory':'$REPO','notes':'Historic output names must be mapped to a fresh output path; no invocation here.'};r['dependencies']={'status':'PARTIAL_PINNED_TOOLS_AND_SOURCES','entries':[{'path':k,'sha256':v} for k,v in d['sources'].items()]+[{'path':d['compiler'],'sha256':d['compiler_sha256']}],'gaps':['Complete SDK/sysroot redistribution and original split stderr not established by this receipt.']};r['outputs']={'status':'ACTUAL_HISTORICAL_CANDIDATE','entries':[{'path':d['candidate_path'],'sha256':d['candidate_sha256']}]};r['verification']={'status':'HISTORICAL_TWO_BUILDS_REPORTED_EQUAL','evidence':[pin(bp)],'executed_this_audit':False,'gaps':['Candidate provenance does not prove deployed generation identity.']};recipes[key]=r;return r
  # Existing source-package build files are explicit locators, not guessed shell commands.
  roots=[]
  for e in entries:
   p=resolve(e['path']);parts=p.parts
   if p.is_relative_to(main/'benchmark'):
    root=main/'benchmark'/p.relative_to(main/'benchmark').parts[0]
    if root not in roots:roots.append(root)
  candidates=[]
  for root in roots:
   candidates += [p for p in root.iterdir() if p.is_file() and ('build' in p.name or 'compile' in p.name) and p.suffix in ['.py','.sh','.json']]
  if candidates:
   r['status']='BUILD_LOCATOR_COMMAND_NOT_CERTIFIED';r['entry']=next((pin(p) for p in sorted(candidates) if p.suffix in ['.py','.sh']),None);r['recipe_documents']=[pin(p) for p in sorted(candidates)];r['command']['notes']='Existing build files found; exact producing argv/dependency closure not inferred. Follow linked original receipt/README.'
  recipes[key]=r;return r
 for row in data['rows']:
  loc=row['source_location'];entries=[];missing=[];native_delivery=None;expected={e['path']:e['sha256'] for e in row.get('evidence',[]) if 'sha256' in e}
  mapped_id=aliases.get(row['id'],row['id'])
  if re.fullmatch(r'REG-00[1-8]',mapped_id):
   num=int(mapped_id[-3:]);fz=f'FZ-{num:03d}'
   if num==7:
    native_delivery=pin(tagmatch) if tagmatch.exists() else None;files=tag.get('files',[])
    override={'JAVA-002':'NetworkRequest.java','JAVA-003':'MediaStore.java','JAVA-004':'NetworkInfo.java','JAVA-005':'NetworkCapabilities.java'}.get(row['id'])
    if override:
     lock=load(main/'sources/api-implementations/FZ-007-tagsoup/t7d-sources.lock.json')
     items=lock if isinstance(lock,list) else lock.get('sources',lock.get('files',[]))
     files=[{'path':x['repo_path'],'sha256':x['sha256']} for x in items if Path(x['repo_path']).name==override]
   else:files=native.get(fz,[]);native_delivery=pin(extracted) if extracted.exists() else None
   for r in files:
    p=main/r['path']
    if p.suffix in SOURCE_EXT and '.before.' not in p.name and p.is_file():
     # Exclude unrelated archive support TUs from the lead source when src/ is available.
     if num in [2,3,4,6,8] and '/src/' not in str(p):continue
     if num==1 and p.name!='base_bundle_installer.cpp':continue
     entries.append(source_pin(p,'implementation' if num not in [6,8] else 'stub',r.get('sha256')))
   if num==5:missing.append('Upstream ART source is a pinned dependency; delivered patches/build recipes are not the full ART source tree.')
   if not entries:missing.append('Native lane source delivery pending or not mapped as an implementation file.')
  elif row['id']=='NATIVE-173':
   p=main/'benchmark/2026-10-13-runtime-surfaceview-split/source/android_graphics_compat_shim.cpp';entries=[source_pin(p,'implementation','c208788a90ee19ad891af5cbe6fb8d7b29f339467ece084255d168dab45d1aef')]
  else:
   extra={'JAVA-022':'stubs/donor/android/telephony/TelephonyFrameworkInitializer.java','JAVA-023':'stubs/donor/com/android/internal/util/Predicate.java','JAVA-024':'src-runtime/adapter/core/GcmDefaultNonce.java'}
   paths=['benchmark/2026-10-02-u12-java-walls/'+extra[row['id']]] if row['id'] in extra else []
   # Parse actual code file locators only. Reports/registries never become implementation sources.
   for match in re.finditer(r'(?:\$WORKSPACES/)?(?:[A-Za-z0-9_.-]+/)+(?:[A-Za-z0-9_.$-]+\.(?:java|cpp|cc|c|hpp|h|inc|rs))(?![A-Za-z])',loc):paths.append(match.group())
   for e in row.get('evidence',[]):
    if Path(e['path']).suffix in SOURCE_EXT:paths.append(e['path'])
   if 'u12-mediandk/candidate.c' in loc:paths += ['benchmark/2026-10-02-u12-mediandk/objects.c.inc','benchmark/2026-10-02-u12-mediandk/platform.h']
   for v in dict.fromkeys(paths):
    p=resolve(v)
    if p.is_file():entries.append(source_pin(p,'stub' if row['implementation_status']=='stub' else 'source_candidate',expected.get(v)))
    else:missing.append('missing literal source: '+v)
  if row['id'] in j7_helpers:
   root=main/'sources/api-implementations/FZ-006/full-jar';lockfile=root/'sources.lock.json';lock=load(lockfile);entries=[];native_delivery=pin(lockfile)
   selected=[e for e in lock['sources'] if Path(e['path']).name==j7_helpers[row['id']]];assert len(selected)==1
   for e in selected:
    q=source_pin(root/e['path'],'stub' if row['implementation_status']=='stub' else 'implementation',e['sha256']);q['original_source_commit']=e['commit'];q['original_source_blob']=e['git_blob'];entries.append(q)
  if row['id'] in java_resolutions:
   entries=[];native_delivery=pin(java115_path if row['id']=='JAVA-115' else java_path)
   for e in java_resolutions[row['id']]['source_entry']:
    p=main/e['path'];assert sha(p)==e['sha256']
    q=source_pin(p,'permission_resource' if p.suffix=='.json' else 'source_candidate',e['sha256']);q['member_evidence']=e.get('member_evidence',java_resolutions[row['id']].get('member_evidence',[]));q['original_source_commit']=java_resolutions[row['id']].get('source_revision');entries.append(q)
   missing.extend(x for x in java_resolutions[row['id']]['limits'] if not x.startswith('New full compilation is not executed'))
  if row['id'] in resolutions:
   entries=[]
   for e in resolutions[row['id']]['source_entry']:
    p=main/e['path']
    if not p.is_file():p=delivery/e['path']
    q=source_pin(p,e.get('role','implementation' if row['id'] in ['NATIVE-115','NATIVE-116'] else 'source_candidate'),e['sha256']);q.update(symbol=e['symbol'],lines=e['lines']);q['original_source_commit']=resolutions[row['id']].get('source_revision');entries.append(q)
   missing.append(resolutions[row['id']]['scope'])
  if row['id'] in ['JAVA-037','REG-110']:
   rel={'JAVA-037':'sources/api-implementations/FZ-001/archive-source/adapter/framework/package-manager/jni/apk_network_permissions.h','REG-110':'sources/api-implementations/legacy-graphics-7e4b38/android_graphics_compat_shim.cpp'}[row['id']]
   p=main/rel
   if not p.exists():p=delivery/rel
   want={'JAVA-037':'c68cfac4657cf24c0d1b3b0dac4d751aaddd9e7df39754524147ab066d94c16c','REG-110':'7e4b38a0dbf3191245ef85df52e49e627895e2982f6acc72193bf066667e8cac'}[row['id']]
   entries=[source_pin(p,'source_candidate',want)]
  # A source snapshot is available, but absent original producing pin remains explicit.
  for e in entries:
   if e['exact_expected_match'] is False:missing.append('expected source SHA mismatch: '+e['path'])
  recipe=recipe_for(row,entries);allmaster=bool(entries) and all(e['master_tracked'] for e in entries);allbound=bool(entries) and all(e['exact_expected_match'] is True for e in entries)
  status='UNKNOWN_IMPLEMENTATION_SOURCE'
  if entries:status='MASTER_SOURCE_LOCATED_BINDING_PARTIAL' if allmaster else 'SOURCE_PRESENT_NOT_ALL_ON_MASTER'
  if row['implementation_status']=='stub' or any(e['role']=='stub' for e in entries):status='STUB_SOURCE_ONLY_NOT_COMPLETE_API'
  if row['record_kind']=='supporting_knowledge':status='SUPPORTING_RECORD_NOT_IMPLEMENTATION'
  if row['id']=='REG-005':status='UPSTREAM_DEPENDENCY_AND_RECIPE_NOT_FULL_SOURCE'
  if allmaster and allbound and all(e['role']=='implementation' for e in entries):status='MASTER_EXACT_SOURCE_LOCATED_BUILD_SCOPE_SEPARATE'
  if not allbound:missing.append('Actual implementation revision-to-source full SHA binding remains partial/unknown; current file presence alone is insufficient.')
  rr={'id':row['id'],'capability':row['capability'],'record_kind':row['record_kind'],'implementation_status':row['implementation_status'],'original_source_location':loc,'coverage_status':status,'source_entry':entries,'source_revision':{'master_commit':commit,'expected_source_sha256':sorted({e['expected_sha256'] for e in entries if e['expected_sha256']}),'exact_binding':allbound,'binding_scope':'source_evidence_pins_not_automatic_current_deployment','status':'exact_pins_match' if allbound else 'partial_or_unknown'},'build_recipe':{'id':recipe['id'],'path':'recipes/recipes.json','sha256':None,'status':recipe['status']},'build_command':recipe['command'],'build_dependencies':recipe['dependencies'],'build_outputs':recipe['outputs'],'build_verification':recipe['verification'],'native_delivery':native_delivery,'gaps':missing,'complete_delivery_claim':False,'original_grades_unchanged':True}
  rows.append(rr)
 for recipe in recipes.values():
  if recipe['entry'] and Path(recipe['entry']['path']).suffix not in ['.py','.sh']:
   recipe.setdefault('recipe_documents',[]).append(recipe['entry']);recipe['entry']=None
 recipefile=out/'recipes/recipes.json';recipefile.write_text(json.dumps({'schema':'api-build-recipes/v1','recipes':list(recipes.values())},ensure_ascii=False,indent=2)+'\n')
 for row in rows:
  row['build_recipe']['sha256']=sha(recipefile)
  finalrecipe=recipes[row['build_recipe']['id']]
  for field,key in [('build_command','command'),('build_dependencies','dependencies'),('build_outputs','outputs'),('build_verification','verification')]:row[field]=finalrecipe[key]
 summary={'rows':len(rows),'source_file_refs':sum(len(x['source_entry']) for x in rows),'master_exact_refs':sum(e['master_tracked'] for x in rows for e in x['source_entry']),'coverage_counts':dict(collections.Counter(x['coverage_status'] for x in rows)),'full315_source_delivery':False,'device_calls':0,'builds_executed':0}
 result={'schema':'api-source-build-mapping/v1','input':pin(source),'master_commit':commit,'rows':rows,'recipes':{'path':'recipes/recipes.json','sha256':sha(recipefile)},'summary':summary}
 (out/'source-build-mapping.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--main',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--master-revision');a=ap.parse_args();generate(a.main,a.out,a.master_revision)
