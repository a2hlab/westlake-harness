"""Assemble G02B evidence from captured local runs; never executes APK/device/network."""
from pathlib import Path
import hashlib,json,os,zipfile,argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--write",action="store_true",help="assemble initial report from existing private receipts")
a=parser.parse_args()
if not a.write: parser.error("explicit --write required; this is not the final receipt checker")
D=Path(__file__).resolve().parent; ROOT=D.parents[2]
MAIN=Path(os.environ.get('COMMERCIAL_G02_MAIN',ROOT))
P=D/'.private/g02b-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
sources=[]
def ref(path, actual=None):
 snapshot=D/'source-snapshots'/path
 p=snapshot if snapshot.is_file() else (actual or ROOT/path)
 if not p.exists():p=MAIN/path
 item={'path':path,'sha256':sha(p),'bytes':p.stat().st_size}
 if snapshot.is_file():item['snapshot_path']=str(snapshot.relative_to(ROOT))
 if item not in sources:sources.append(item)
 return item
for pack in ['dispatch-g02','dispatch-audio']:
 base=D.parent/pack
 for row in json.loads((base/'manifest.json').read_text()):
  p=base/'inputs'/row['path'];assert sha(p)==row['sha256'];ref(row['path'],p)
digest=ref('benchmark/2026-10-21-commercial-game/dispatch-audio/audio-digest-extract.txt')
close=ref('benchmark/2026-10-14-verified-source-closeout/boat/results.json')
lock=ref('sources/api-implementations/boat-v2-production/source.lock.json')
recipe=ref('sources/api-implementations/boat-v2-production/build.py')
signal=ref('sources/api-implementations/boat-v2-production/signal/src/unity_signal_box.c')
backend=ref('sources/api-implementations/boat-v2-production/signal/src/oh_musl_signal_backend.c')
get=ref('benchmark/2026-10-20-t18-audiotrack-size/audiotrack_effective_size.inc')
audio=ref('benchmark/2026-10-20-t18-audiotrack-size/source-profile/oh_audiotrack_shim.cpp')
old=json.loads((D.parent/'dispatch-g02/inputs/benchmark/2026-10-21-genshin-static-intake/boatattack-comparison.json').read_text())
rows=[]
for r in old['rows'][:4]:
 rows.append({'item':r['item'],'class':r['class'],'source_refs':[x['alias'] for x in r['boat_refs']], 'output_sha256':'f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0' if 'shared bridge' in r['item'] else None,'validated_scope':r['observation'],'reuse_condition':r['reuse_condition'],'genshin':'UNKNOWN'})
rows[1]['validated_scope']='Source registers graphics JNI; pin-compatible is a source comment, NOT a general cross-provider ABI guarantee. Exact framework, native window owner/layout and namespace must be re-bound.'
rows[1]['output_sha256_note']='No separate deployed shim-to-this-TU output equivalence established in this slice.'
c=json.loads((ROOT/close['path']).read_text())
for key,title in [('c7','Unity engine C7 binary transform'),('c4','Boat-generated IL2CPP C4 binary transform')]:
 rows.append({'item':title,'class':'boat_specific_not_reusable','source_refs':[recipe['path'],lock['path'],close['path']],'output_sha256':c[key]['sha256'],'validated_scope':'New exact replay rc0, not engine rebuild; fixed Boat input/patch sequence only.','reuse_condition':'No transfer to a different game/version. Inspect authorized exact inputs first.','genshin':'UNKNOWN'})
rows.append({'item':'bionic/musl signal adapter','class':'public_reusable_candidate_exact_binding_required','source_refs':[signal['path'],backend['path'],recipe['path'],close['path']],'output_sha256':c['signal']['expected'],'new_output_sha256':c['signal']['actual'],'validated_scope':'Own C compatibility implementation, not Unity engine code. Compile/link/strip0; signed comparison2, 19 build-id bytes differ; runtime equivalence unproven.','reuse_condition':'Match consumer signal ABI/export namespace/handler ownership and exact source generation; do not copy Boat engine patches. Namespaced guest scope only; preserve the ART SIGSEGV/SIGBUS handler strategy. This is not merely a structure conversion and must not be injected globally.','genshin':'UNKNOWN'})
rows.append({'item':'Boat game logic and coordinates','class':'boat_specific_not_reusable','source_refs':[old['rows'][5]['boat_refs'][0]['alias'],old['rows'][3]['boat_refs'][0]['alias']],'output_sha256':None,'validated_scope':'Boat scoped image/input review, not a full-race or game-independent result.','reuse_condition':'Do not copy game content or blind UI coordinates.','genshin':'UNKNOWN'})
rows.extend([
 {'item':'AudioTrack effective ring getter','class':'public_reusable_candidate_exact_binding_required','source_refs':[get['path'],audio['path'],'benchmark/2026-10-20-t18-audiotrack-production/README.md','benchmark/2026-10-20-t18-audiotrack-production/recipe.json'],'output_sha256':'dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9','validated_scope':'native_get_buffer_size_frames()I returns cap/bytesPerFrame under existing owner mutex, validates stopping/ring bounds/int range. Not free space, requested Java frames or OH hardware capacity; no new release lifetime guarantee. Getter source lines15-28.','reuse_condition':'Only if exact target calls this Java JNI owner; match JAR method/registration/owner and backend.','genshin':'UNKNOWN'},
 {'item':'Actual audio backend and namespace','class':'public_reusable_candidate_exact_binding_required','source_refs':[audio['path'],digest['path'],'scripts/lab/open_site_scan.py'],'output_sha256':None,'validated_scope':'AudioTrack source targets OH_AudioRenderer via libohaudio dynamic loading. T18 human audio belongs to one Toutiao clip. T34 signoff reuses prior 5cd audio, not new61b human audio.','reuse_condition':'Read target Java/native dependencies first; trace actual caller open sites and namespace to provider, callbacks and buffer format. Maps/library presence cannot select the backend.','genshin':'UNKNOWN'},
 {'item':'OpenSLES Android/OH ABI and PLAY callbacks','class':'known_provider_limitation','source_refs':[digest['path']],'output_sha256':'05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100','validated_scope':'Prior exact05d8 evidence: OH IID24 vs Android16; GetState8-byte store vs4. PLAY RegisterCallback/SetCallbackEventsMask return12 FEATURE_UNSUPPORTED. No new REA or provider test here.','reuse_condition':'Width adapter alone does not supply callback-driven playback; inspect exact target imports/interface use and actual provider version. Do not infer audible output from engine creation.','genshin':'UNKNOWN'}])
write('reuse-matrix.json',{'rows':rows,'corrections':['Signal adapter split from app-private Unity/IL2CPP','Old provenance gaps superseded only by new exact replay records; historical logs stay unknown','Source pin-compatible comment is not arbitrary native-window ABI proof'],'runtime_verdict':'NOT_TESTED'})
entry=[
 {'id':'manifest','argv':['$AAPT2','dump','badging','$APK'],'additional_argv':['$AAPT2','dump','xmltree','$APK','--file','AndroidManifest.xml'],'inputs':'Exact base APK; inspect splits separately','output':'package/version/SDK/ABI declarations/XML','actual_smoke':'manifest and xmltree rc0'},
 {'id':'elf','argv':['$LLVM_READELF','-h','-d','$EXTRACTED_ELF'],'inputs':'Exact ZIP member, member SHA and containing APK SHA','output':'machine/class/DT_NEEDED, not runtime provider','actual_smoke':'arm64 graphics.path member rc0'},
 {'id':'open-sites','argv':['python3','scripts/lab/open_site_scan.py','$HOST_ELF','$CHILD_ELF','--json','$OUT/sites.json'],'inputs':'Exact host and child ELF; Android NDK llvm-objdump/nm (tool() picks sorted installed path)','output':'direct open-site PCs/namespace edges; unresolved indirect paths remain unknown','actual_smoke':'one APK arm64 ELF rc0, zero direct sites; not host/child closure'},
 {'id':'jni','argv':['python3','scripts/lab/jni_gate.py','--package','$GENERATION','--allowlist','$APPROVED_EXCEPTIONS','--output','$OUT/jni.json'],'inputs':'Generation package.json + actual JAR/native/source closure; not an APK-only CLI','output':'export/registration coverage, strict exception gate; no app reachability proof','actual_smoke':'NOT_RUN; target generation missing'}]
for p in ['scripts/lab/open_site_scan.py','scripts/lab/jni_gate.py','benchmark/2026-09-29-static-wall-prediction/scan_jni.py']:ref(p)
write('scan-entry.json',{'entries':entry,'next':'t1 exact Genshin input manifest including splits/assets then manifest -> ELF/imports -> target callsites/JNI and host/child open sites; no backend selected before dependencies.'})
E=D/'evidence';E.mkdir(exist_ok=True); receipts=[]
for name in ['manifest','xmltree','opensite','llvm-readelf','llvm-nm','contract','branch']:
 d=P/name;row={'id':name,'rc':int((d/'rc').read_text()),'raw_alias':'$G02B_PRIVATE/'+name,'raw':[]}
 for f in sorted(d.iterdir()):
  if f.name not in ['argv.json','stdout','stderr','rc','result.json']:continue
  row['raw'].append({'name':f.name,'sha256':sha(f),'bytes':f.stat().st_size})
  text=f.read_text().replace(str(Path.home()),'$HOME').replace(str(ROOT),'$REPO')
  dest=E/(name+'.'+f.name+('.txt' if f.name=='stderr' else ''));dest.write_text(text)
  row.setdefault('public',[]).append({'path':str(dest.relative_to(D)),'sha256':sha(dest),'bytes':dest.stat().st_size})
 receipts.append(row)
write('receipts.json',receipts)
apk=Path.home()/'.local/share/westlake/commercial-game-20261021/reuse/input/org.fossify.notes_13.apk'
with zipfile.ZipFile(apk) as z:
 member='lib/arm64-v8a/libandroidx.graphics.path.so';native=[x for x in z.namelist() if x.startswith('lib/') and x.endswith('.so')];member_sha=hashlib.sha256(z.read(member)).hexdigest()
aapt=Path.home()/'Library/Android/sdk/build-tools/37.0.0/aapt2'
write('smoke.json',{'scope':'REAL_NOTES_APK_TOOL_SMOKE_NOT_GENSHIN','input_alias':'$HOME/.local/share/westlake/commercial-game-20261021/reuse/input/org.fossify.notes_13.apk','apk_sha256':sha(apk),'apk_bytes':apk.stat().st_size,'package':'org.fossify.notes','version_code':13,'version_name':'1.7.0','min_sdk':26,'target_sdk':36,'native_members':native,'scanned_member':member,'member_sha256':member_sha,'direct_open_sites':0,'aapt2_sha256':sha(aapt),'runtime_executed':False})
write('source-index.json',sources)
write('results.json',{'token':'COMMERCIAL-G02B','status':'OFFLINE_DELIVERY_PENDING_HUMAN_REVIEW','dispatch_verified':15,'audio_inputs_verified':5,'genshin':{k:'UNKNOWN' for k in ['exact_input','version','abi','engine_version','graphics_api','audio_backend','namespace','first_fatal','blocker_count']},'genshin_runtime':'NOT_TESTED','device_calls':0,'network_calls':0,'rea_calls':0,'smoke':'smoke.json','receipt':'receipts.json','branch_create_rc':128,'commit':None,'git_failure':'shared refs Operation not permitted; no retry','missing':['t1 exact Genshin artifact SHA/splits/assets','Target generation/runtime provider binding','Historical exact signal producing invocation; new build differs only build-id'],'private_alias':'$G02B_PRIVATE = this delivery .private/g02b-01; no raw binaries committed'})
print('wrote',len(rows),'reuse rows',len(sources),'source refs')
