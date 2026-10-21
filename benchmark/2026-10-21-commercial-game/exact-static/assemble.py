#!/usr/bin/env python3
"""Assemble a bounded public report from exact offline receipts; explicit --write only."""
import argparse,hashlib,json,os,re,shutil,struct
from pathlib import Path
D=Path(__file__).resolve().parent; REPO=D.parents[2]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def put(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n')
def load(p):return json.loads(p.read_text())
def sanitize(s):return s.replace(str(Path.home()),'$HOME').replace(str(REPO),'$REPO')
def main():
 a=argparse.ArgumentParser();a.add_argument('--write',action='store_true',required=True);a.add_argument('--main',type=Path,required=True);args=a.parse_args()
 P=D/'.private/g04-01';E=D/'evidence';E.mkdir(exist_ok=True)
 official=Path.home()/'.local/share/westlake/commercial-game-20261021/official-input';outer=official.parent/'exact-static/outer-rea'
 sources=[]
 def snap(path,label):
  dest=D/'source-snapshots'/label;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
  row={'path':label,'sha256':sha(path),'bytes':path.stat().st_size,'snapshot_path':dest.relative_to(REPO).as_posix()}
  original=dest.read_text(errors='replace')
  redacted=original.replace(str(Path.home()),'$HOME')
  redacted=re.sub(r'/home/[A-Za-z0-9_.-]+', '$REMOTE_HOME', redacted)
  if redacted!=original:
   private=P/'source-originals'/label;private.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,private);dest.write_text(redacted)
   row['snapshot_sha256']=sha(dest);row['snapshot_bytes']=dest.stat().st_size;row['snapshot_transform']='personal-root aliases only; exact original preserved under $G04_PRIVATE/source-originals'
  sources.append(row);return row
 for n in ['project.spec.md','t4-exact-static.spec.md']:snap(args.main/'specs/commercial-game-round1'/n,'specs/commercial-game-round1/'+n)
 reuse=D.parent/'reuse';snap(reuse/'reuse-matrix.json','benchmark/2026-10-21-commercial-game/reuse/reuse-matrix.json')
 for r in load(reuse/'source-index.json'):
  if r['path'] in {s['path'] for s in sources}:continue
  candidates=[REPO/r.get('snapshot_path',r['path']),args.main/r['path'],REPO/r['path']]
  found=next((p for p in candidates if p.is_file() and sha(p)==r['sha256']),None)
  if not found:raise RuntimeError('source unavailable: '+r['path'])
  # Ship the exact referenced source snapshot, avoiding changing main/spec/dispatch dependencies.
  snap(found,r['path'])
 put(D/'source-index.json',sources)
 g03=[]
 for stem in ['i04-aapt2-badging','i05-aapt2-manifest-xmltree','i06-apksigner-verify']:
  for ext in ['argv.json','stdout','stderr','rc']:
   src=official/'raw'/(stem+'.'+ext);out=E/(stem+'.'+ext+('.txt' if ext in ['stdout','stderr'] else ''))
   out.write_text(sanitize(src.read_text(errors='replace')))
   g03.append({'source':'$OFFICIAL_INPUT/raw/'+src.name,'sha256':sha(src),'bytes':src.stat().st_size,'public':out.relative_to(D).as_posix(),'public_sha256':sha(out),'transform':'personal-root aliases only'})
 put(D/'g03-evidence-index.json',g03)
 elf=load(D/'elf-inventory.json');dex=load(D/'dex-inventory.json');libs=elf['libraries'];names={Path(x['member']).name for x in libs}
 edges=[{'caller':x['member'],'needed':n,'classification':'UNRESOLVED_STRING_TABLE' if n=='<?>' else 'PACKAGED_SAME_ABI_CANDIDATE' if n in names else 'EXTERNAL_PROVIDER_UNBOUND','runtime_namespace':'UNKNOWN'} for x in libs for n in x['needed']]
 put(D/'dependency-edges.json',{'apk_sha256':elf['apk_sha256'],'edges':edges,'note':'Name inventory only. Packaged presence does not establish load order, symbol versions, namespace or actual provider.'})
 bundle=outer/'package-evidence-bundle.json';copy=P/'outer-rea'/bundle.name;copy.parent.mkdir(exist_ok=True);shutil.copyfile(bundle,copy)
 records=[r for r in load(bundle)['records'] if r['subject']['digest']['sha256']==elf['apk_sha256']]
 parent=next(r for r in records if r['operation']=='inspect_android_package');norm=parent['normalized_result']
 put(E/'rea-package-observed.json',{'evidence_id':parent['evidence_id'],'executed_by':'outer(codex)','analyzed_by':'inner(codex)','subject_sha256':elf['apk_sha256'],'engine':norm['engine'],'class_count':norm['class_count'],'resource_count':norm.get('resource_count'),'limitations':parent['limitations'],'raw_bundle':{'alias':'$G04_PRIVATE/outer-rea/'+bundle.name,'sha256':sha(bundle),'bytes':bundle.stat().st_size},'scope':'Only exact-target records used; unrelated historical Toutiao records in export are excluded.'})
 manifest=norm['manifest']['text'];(E/'manifest.rea.xml').write_text(manifest)
 attempts=[]
 for stem in ['rea-package','rea-cli-package','rea-cli-package-cache']:
  if stem=='rea-package':f=P/(stem+'.json');attempts.append({'name':stem,'status':'CLIENT_APPROVAL_REJECTED_NOT_EXECUTED','raw':f.name,'sha256':sha(f)});continue
  f=P/(stem+'.stdout');rc=int((P/(stem+'.rc')).read_text());err=load(f)
  dest=E/(stem+'.error.json');dest.write_text(sanitize(json.dumps(err,indent=2))+'\n')
  attempts.append({'name':stem,'rc':rc,'status':'FAILED_NO_SUCCESSFUL_EVIDENCE','raw':f.name,'sha256':sha(f),'error_code':err['error']['code'],'public':dest.relative_to(D).as_posix()})
 put(D/'rea-ledger.json',{'attempts':attempts,'successful_package':{'executed_by':'outer(codex)','evidence_id':parent['evidence_id'],'artifact_sha256':elf['apk_sha256'],'raw_bundle_sha256':sha(bundle)},'method_requests_pending':['com.combosdk.openapi.ComboApplication.attachBaseContext/onCreate','com.miHoYo.GetMobileInfo.MainActivity.onCreate','com.unity3d.player.UnityPlayer.loadLibraryStatic(java.lang.String)','org.fmod.FMODAudioDevice.run()'],'note':'No APK execution; REA does not verify APK signatures. No retry after cleanup_incomplete.'})
 rows=[
 ('manifest','OBSERVED','ComboApplication; launcher MainActivity; GLES 3.1 and AEP requested, Vulkan optional.','evidence/manifest.rea.xml','Manifest projection/activity lifecycle support on actual target is unbound.'),
 ('application','OBSERVED_DEX','ComboApplication.attachBaseContext falls through to Application; onCreate calls CryptoUtils.init and Initializer.start unless hotfix redirect handles invocation.','startup-excerpts.json','Dynamic hotfix branch selection and downloaded content UNKNOWN.'),
 ('launcher','OBSERVED_DEX','MainActivity.onCreate calls ComboSDKActivity, then UnityPlayerActivity creates UnityPlayer and setContentView.','startup-excerpts.json','No first frame/runtime initialization observed.'),
 ('native-load','OBSERVED_DEX','UnityPlayer.<clinit> tries yuanshen, then main only if loadLibraryStatic returned false; NativeLoader.load(nativeLibraryDir) is native.','startup-excerpts.json','main not packaged; runtime resolution/fallback outcome UNKNOWN. No separate unity/il2cpp file in APK lib directory.'),
 ('engine-identity','STRING_HINT_ONLY','libyuanshen contains 2017.4.30f1 strings and global-metadata references; APK includes 80748380-byte global-metadata.dat.','native-string-hints.json','Exact engine revision/configuration and combined engine/generated-code division UNKNOWN; Boat 2020.3.23f1 transforms not portable.'),
 ('graphics','OBSERVED_ELF_IMPORT','libyuanshen imports ANativeWindow_fromSurface/acquire/release/getWidth/getHeight/setBuffersGeometry and EGL window/context/swap functions.','elf-inventory.json','Actual OH wrapper/owner/ABI/ns and GLES/AEP support unbound. No assumption of pin-compatible native windows.'),
 ('vulkan','STRING_HINT_ONLY','libvulkan.so string present in libyuanshen; optional manifest feature.','native-string-hints.json','No direct vk import in scanned dynamic symbol tables; dlsym/branch selection UNKNOWN, not absence of Vulkan path.'),
 ('fmod-audio','OBSERVED_DEX','FMODAudioDevice.run calls fmodGetInfo, AudioTrack.getMinBufferSize, constructor(IIIIII), getState, play and write(byte[],int,int); fmodProcess fills buffer.','startup-excerpts.json','Native registration/provider and actual selected output UNKNOWN. No direct getBufferSizeInFrames call found in this method.'),
 ('opensles','OBSERVED_ELF_IMPORT','Mmoron and cri_ware_unity need libOpenSLES and import engine/PLAY/buffer queues; CRI also RECORD and effects.','elf-inventory.json','Existing Android/OH IID widths and PLAY callback hard stubs are relevant conditional constraints; exact playback interfaces selected UNKNOWN.'),
 ('aaudio','BOUNDED_NEGATIVE','No AAudio-prefixed name among decoded undefined dynamic symbols; two LLVM warning objects limit completeness.','elf-inventory.json','Dynamic lookup, other resources and later downloaded code not ruled out.'),
 ('jni','NAME_MATCH_ONLY',f"{len(dex['native_declarations'])} native declarations; {sum(bool(x['short_export_candidates'] or x['long_export_candidates']) for x in dex['native_declarations'])} exported-name candidates.",'dex-inventory.json','Unmatched names are NOT missing JNI: dynamic RegisterNatives and class ownership remain UNKNOWN; short exports may have overload ambiguity.'),
 ('first-fatal','UNKNOWN','No device or APK execution.','results.json','All runtime outcomes NOT_TESTED; no claim of install admission, playable state, first fatal removed, graphics/audio pass.')]
 put(D/'startup-matrix.json',{'rows':[dict(zip(['id','basis','finding','evidence','limit'],r)) for r in rows]})
 targets=[['launcher','jni'],['graphics'],['manifest','graphics'],['launcher'],['engine-identity','native-load'],['engine-identity','jni'],['native-load','jni'],['engine-identity'],['fmod-audio'],['fmod-audio','opensles','aaudio'],['opensles']]
 matrix=load(reuse/'reuse-matrix.json');new=[]
 for row,refs in zip(matrix['rows'],targets):
  row=dict(row);row['target_evidence_ids']=refs;row['runtime_provider']='UNKNOWN';row['runtime_namespace']='UNKNOWN';row['target_runtime']='NOT_TESTED';new.append(row)
 new[8]['target_limit']='Observed FMOD Java path uses getMinBufferSize and 4-byte PCM buffer arithmetic, not a direct effective-ring getter call. Reuse cap/bpf logic only if the corresponding adapter method is actually required; never assume requested size equals usable capacity.'
 new[6]['target_limit']='Guest namespace only, preserve ART SIGSEGV/SIGBUS handler policy; not a pure struct conversion and no global injection.'
 put(D/'reuse-map.json',{'basis':'Exact frozen G02 11-row source matrix plus current target references; conditional mechanisms, not runtime transfer.','rows':new})
 counts={'elfs':len(libs),'abis':sorted({x['member'].split('/')[1] for x in libs}),'dexes':len(dex['dexes']),'dex_classes':dex['class_count'],'native_declarations':len(dex['native_declarations']),'export_name_candidates':sum(bool(x['short_export_candidates'] or x['long_export_candidates']) for x in dex['native_declarations']),'targeted_callsites':len(dex['calls']),'dependency_edges':len(edges),'libraries_with_llvm_warnings':[q['member'] for q in libs if q.get('llvm_warnings')],'unresolved_needed_entries':sum(e['classification']=='UNRESOLVED_STRING_TABLE' for e in edges),'external_needed_names':sorted({e['needed'] for e in edges if e['classification']=='EXTERNAL_PROVIDER_UNBOUND'})}
 headercounts=[]
 for x in dex['dexes']:
  f=P/'scan/members'/x['member'];b=f.read_bytes()[:112];headercounts.append({'member':x['member'],'class_defs_size':struct.unpack_from('<I',b,96)[0]})
 put(E/'dex-class-counts.json',{'dex_headers':headercounts,'sum':sum(x['class_defs_size'] for x in headercounts),'rea_class_count':norm['class_count'],'interpretation':'Different inventory counts retained separately; cause not established. DEX header count covers all five packaged DEX, not REA class coverage.'})
 put(D/'results.json',{'schema':'commercial-game-exact-static-v1','status':'STATIC_SLICE_COMPLETE_METHOD_REA_PENDING','input':load(P/'identity.json'),'counts':counts,'signature':'G03 apksigner rc0, v1/v2 true; same exact APK SHA; see original warning list','runtime':'NOT_TESTED','first_fatal':'UNKNOWN','device_actions':0,'game_executions':0,'human_review':'PENDING','rea_executed_by':'outer(codex)','audio_audibility':'UNKNOWN','graphics_runtime':'UNKNOWN','private_root_alias':'$G04_PRIVATE = exact-static/.private/g04-01','target_binaries_built':0,'elf_coverage':'All 32 invoked rc0; two objects emit LLVM warnings, six libmsaoaidsec NEEDED strings unresolved. Reported imports are not a complete registration/provider proof.'})
 # Preserve the initial failed UTF-8-only extraction as a tool receipt, not a fabricated shell log.
 put(P/'focus-first-tool-failure.json',{'capture_kind':'tool_output_transcription','exit_code':1,'error':"UnicodeDecodeError: utf-8 cannot decode byte 0xc0 at position 39602369 while reading classes3.stdout",'correction':'decode diagnostic text with errors=replace; original raw bytes never altered'})
 raw=[]
 for f in sorted(P.rglob('*')):
  if not f.is_file() or 'module-cache' in f.parts or f.name=='raw-index.json':continue
  raw.append({'path':f.relative_to(P).as_posix(),'sha256':sha(f),'bytes':f.stat().st_size})
 put(D/'raw-index.json',{'root_alias':'$G04_PRIVATE','entries':raw,'remote_archive':'NOT_CREATED','excluded':'Disposable REA compiler module cache; no target Evidence omitted.'})
 tools=load(P/'scan/tools.json')
 for x in tools:x['path']=sanitize(x['path'])
 put(D/'tool-pins.json',tools)
 print(json.dumps({'counts':counts,'raw_files':len(raw),'sources':len(sources)}))
if __name__=='__main__':main()
