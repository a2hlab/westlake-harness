#!/usr/bin/env python3
"""Read signed inventory and retained evidence; never invokes device/build tools."""
import argparse,collections,hashlib,json,os,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
B='benchmark/2026-10-09-demo-boatattack/v2-20261013'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(main,out):
 main=main.resolve();ws=main.parent;out.mkdir(parents=True,exist_ok=False)
 def load(p):return json.loads(Path(p).read_text())
 def resolve(p):return Path(str(p).replace('$WORKSPACES',str(ws)))
 def portable(p):
  p=Path(p).resolve()
  return '$WORKSPACES/'+str(p.relative_to(ws)) if p.is_relative_to(ws) else '$WORKSPACES/../'+str(p.relative_to(ws.parent)) if p.is_relative_to(ws.parent) else str(p)
 def pin(p):return {'path':portable(p),'sha256':sha(p)}
 def sanitize(x):
  if isinstance(x,dict):return {k:sanitize(v) for k,v in x.items()}
  if isinstance(x,list):return [sanitize(v) for v in x]
  if isinstance(x,str) and x.startswith(str(ws.parent)+'/'):return portable(x)
  return x
 def write(name,x):(out/name).write_text(json.dumps(sanitize(x),ensure_ascii=False,indent=2)+'\n')
 signed=main/B/'outer/final61b-v2-seal/final-signoff.json';s=load(signed);assert sha(signed)=='ad566caef9dbb7d55c1e058f3f68bc43abac0db3f51a1144514400ae22893e9a'
 sealp=resolve(s['source_seal']['path']);assert sha(sealp)==s['source_seal']['sha256'];seal=load(sealp);targets={};groups=collections.defaultdict(list)
 for group,items in seal['files'].items():
  for target,h in items.items():
   assert target not in targets or targets[target]==h;targets[target]=h;groups[target].append(group)
 assert len(targets)==824
 wanted=set(targets.values());archive_hits=collections.defaultdict(list);local_sources=collections.defaultdict(list);archive_reports=[];evidence=[]
 # Exact archived membership is independent of deployed presence and source compilation.
 vp=main/'benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/persistence.json';v=load(vp);manifest=ws/'westlake-inputs/seal-archive-20261013/archive-members.json';assert sha(manifest)==v['archive_members_sha256'];rows=load(manifest)['files'];vmap={r['path'].replace('$WORKSPACES/',''):r for r in rows}
 def inspect_tar(name,path,expected,rowmap,remote_receipt):
  assert sha(path)==expected,(name,'archive SHA');verified={};count=0
  with tarfile.open(path,'r|gz') as tf:
   for ent in tf:
    key=ent.name.removeprefix('./');row=rowmap.get(key)
    if not row or row['sha256'] not in wanted:continue
    h=row['sha256']
    if ent.isfile():actual=hashlib.sha256(tf.extractfile(ent).read()).hexdigest();assert actual==h,(name,key);verified[key]=h
    elif ent.islnk():assert verified.get(ent.linkname.removeprefix('./'))==h,(name,key,'hardlink');verified[key]=h
    else:continue
    count+=1;archive_hits[h].append({'archive_id':name,'member':key})
  archive_reports.append({'id':name,'local_archive':pin(path),'remote_receipt':pin(remote_receipt),'verified_target_members':count,'remote_status':'historical_receipt_until_fresh_receipt_checked'})
 inspect_tar('v1-exact-bytes',resolve(v['local_archive']),v['sha256'],vmap,vp)
 for r in rows:
  if r['sha256'] in wanted:local_sources[r['sha256']].append(r['path'])
 # Final execution archive contains this board's new materialized controls.
 ep=main/'benchmark/2026-10-14-final61b-execution-archive';er=load(ep/'archive.json');em=ep/'.artifacts/source-manifest.jsonl';assert sha(em)==er['source_manifest_sha256'];emrows=[json.loads(x) for x in em.read_text().splitlines()]
 inspect_tar('final61b-execution',ep/'.artifacts/final61b-execution.tar.gz',er['sha256'],{r['path']:r for r in emrows},ep/'archive.json')
 for r in emrows:
  if r['sha256'] in wanted:local_sources[r['sha256']].append(portable(main/r['path']))
 # Small ADC archive contains exact parent, output and the real replay logs.
 ap=main/B/'outer/adc-source-closure';ar=load(ap/'persistence.json');assert sha(ap/ar['archive'])==ar['sha256'];adc_members={}
 with tarfile.open(ap/ar['archive']) as tf:
  for ent in tf:
   if ent.isfile():
    h=hashlib.sha256(tf.extractfile(ent).read()).hexdigest();adc_members[ent.name]=h
    if h in wanted:archive_hits[h].append({'archive_id':'adc-exact-reuse','member':ent.name})
 archive_reports.append({'id':'adc-exact-reuse','local_archive':pin(ap/ar['archive']),'remote_receipt':pin(ap/'persistence.json'),'members':adc_members})
 # Verify all declared f28 material, including original raw build streams and recipe archive.
 fp=ws/'westlake-inputs/generations/boat-v2-runtime-f28bd1b3-20261013';fr=load(fp/'receipt.json');fa=load(main/B/'outer/r6-source-review/artifact-archive.json')
 for r in fa['members']:
  assert sha(fp/r['path'])==r['sha256'];
  if r['sha256'] in wanted:
   archive_hits[r['sha256']].append({'archive_id':'f28-source-and-output','member':r['path']});local_sources[r['sha256']].append(portable(fp/r['path']))
 fm={}
 with tarfile.open(fp/'candidate-source-recipe.tar.gz') as tf:
  for e in tf:
   if e.isfile():fm[e.name]=hashlib.sha256(tf.extractfile(e).read()).hexdigest()
 assert fr['source']['sha256'] in fm.values() and fr['source_patch']['sha256'] in fm.values()
 assert all(x['sha256'] in fm.values() for x in fr['scripts'].values())
 assert all(x['rc']==0 for x in fr['steps'])
 for step in fr['steps']:
  for field in ['stdout','stderr']:assert sha(fp/Path(step[field]['path']).name)==step[field]['sha256']
 # Inspect the complete source dependency archive, not merely its 6347 count.
 base=ws/'westlake-inputs/generations/t2c-runtime-reproduction-20261010';inv=load(base/'input-inventory.json');assert sha(base/'input-inventory.json')==fr['closure_before']['inventory']['sha256'];assert sha(base/'runtime187-inputs.tar.gz')==fr['original_source_archive']['sha256'];base_hashes={}
 with tarfile.open(base/'runtime187-inputs.tar.gz','r|gz') as tf:
  for e in tf:
   if e.isfile():base_hashes[e.name]=hashlib.sha256(tf.extractfile(e).read()).hexdigest()
 missing=[x for x in inv['files'] if x['sha256'] not in set(base_hashes.values())];assert not missing,missing[:2]
 archive_reports.append({'id':'f28-source-and-output','remote_receipt':pin(main/B/'outer/r6-source-review/artifact-archive.json'),'nested_recipe_members':fm,'original_build_rc':0,'raw_stdout':pin(fp/'container-build.stdout.txt'),'raw_stderr':pin(fp/'container-build.stderr.txt'),'base_archive':pin(base/'runtime187-inputs.tar.gz'),'base_inventory':pin(base/'input-inventory.json'),'base_declared_inputs_verified':len(inv['files']),'remote_base_receipt':pin(main/'benchmark/2026-10-10-adapter-buildchain/runtime-persistence.json')})
 # Source locators: deployment indexes and actual generated plan, never assumed from names.
 indices=[main/'benchmark/2026-10-12-toutiao-recovery-readonly/archive-1950/index.json',main/'benchmark/2026-10-14-final61b-v2-collector/routeb487-source.actual.json',main/B/'outer/final61b-approved-execution/boat/plan.disabled.json']
 for ip in indices:
  d=load(ip)
  for row in d.get('files',d.get('members',[])):
   h=row.get('sha256');src=row.get('source');src=src.get('path') if isinstance(src,dict) else src
   if src and h in wanted:local_sources[h].insert(0,src)
  evidence.append(pin(ip))
 # Remote read-only work can be performed by outer where SSH is allowed.
 remote=main/'benchmark/2026-10-14-demo-desktop-ready/remote-repro-readonly';remote_result={'status':'UNKNOWN_NO_FRESH_RECEIPT'}
 if (remote/'receipt.json').is_file():
  rr=load(remote/'receipt.json');rd=load(remote/'stdout.json');assert rr['rc']==0;assert len(rd['results'])==8 and all(x['status']=='MATCH' and x['actual_sha256']==x['expected_sha256'] for x in rd['results']);remote_result={'status':'OUTER_ACTUAL_READONLY_8_MATCH','receipt':pin(remote/'receipt.json'),'stdout':pin(remote/'stdout.json'),'stderr':pin(remote/'stderr.txt'),'archives':[{'path':x['remote_path'],'sha256':x['actual_sha256'],'member_count':len(x.get('members',[]))} for x in rd['results']]}
 # Profiles preserve unknowns; a shared SHA shares a build fact, never another target's deployment fact.
 sp=main/'benchmark/2026-10-14-demo-desktop-ready/remote-repro-supplement';sr=load(sp/'receipt.json')
 assert sr['status']=='REMOTE_SHA_VERIFIED' and len(sr['members'])==4
 assert (sp/'verify.stdout.txt').read_text().split()[0]==sr['sha256']
 assert not (sp/'verify.stderr.txt').read_bytes()
 inspect_tar('final-four-object-supplement',sp/'runtime-supplement.tar.gz',sr['sha256'],{r['member']:r for r in sr['members']},sp/'receipt.json')
 archive_reports[-1].update(remote_status='OUTER_REMOTE_SHA_VERIFIED',remote_stdout=pin(sp/'verify.stdout.txt'),remote_stderr=pin(sp/'verify.stderr.txt'))
 profiles={}
 def profile(h,name,status,refs,gaps,source=None,patch=None,tools=None,scripts=None,logs=None,replay='not_established'):
  profiles[h]={'name':name,'source_build_status':status,'source_snapshot':source,'patch_sequence':patch,'toolchain':tools,'build_scripts':scripts,'original_rc0_logs':logs,'deterministic_replay_status':replay,'evidence':[pin(x) for x in refs],'gaps':gaps}
 fhash=fr['candidate']['sha256'];profile(fhash,'f28 runtime','EXISTING_COLD_SOURCE_BUILD_VERIFIED',[fp/'receipt.json',main/B/'outer/r6-source-review/artifact-archive.json'],['No expensive rebuild performed in this audit; pinned container and author-path layout remain dependencies.'],fr['original_source_archive'],fr['source_patch'],{'clang':fr['clang'],'container_image':fr['container_image']},fr['scripts'],{'receipt':pin(fp/'receipt.json'),'stdout':pin(fp/'container-build.stdout.txt'),'stderr':pin(fp/'container-build.stderr.txt'),'rc':0})
 ac=main/B/'integration/r4-knowledge-closure/evidence/adc-closure.json';ah='adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130';assert adc_members['inputs/candidate.so']==ah and adc_members['inputs/baseline.so']=='9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db'
 profile(ah,'ADC libandroid','BLOCKED_EXACT_PARENT_SOURCE_BUILD_UNKNOWN',[ac,ap/'persistence.json',main/'benchmark/2026-10-10-boat-runtime-jni-gap/README.md'],['9cc baseline original source/compiler/link closure missing.','49-byte patch replay is not source compilation.','0d7b runtime-build.log is a different artifact; f28/947 builds do not replace this libandroid caller.'],patch=load(ac)['patch_sequence'],scripts=load(ac)['replay_script'],logs={'rc':0,'stdout':load(ac)['new_replay'],'stderr':load(ac)['new_replay_stderr'],'kind':'PATCH_REPLAY_NOT_BUILD'},replay='EXISTING_49_BYTE_REPLAY_RC0_VERIFIED')
 prov=ws/'westlake-harness-bms'/B/'static/provenance-closure.json';reg=main/'knowledge/gates/rebuildable-artifacts.json'
 profile('8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e','Boat bridge8ab','BLOCKED_EXACT_SOURCE_TOOLCHAIN_LOGS',[prov,reg,main/'benchmark/2026-10-10-adapter-buildchain/README.md'],['Exact source/patch/link inputs and producing log missing;089b/216d outputs not8ab.'])
 for h,name in [('6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852','Boat JAR633'),('1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac','Boat C7 libunity'),('f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746','Boat C4 libil2cpp'),('7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da','Boat signal box')]:
  profile(h,name,'PARTIAL_RECIPE_NOT_PAIRED_EXACT_SOURCE_BUILD',[prov],['Existing recipe locator is not a pinned complete original build closure; source dependencies/toolchain/original paired streams unresolved.'])
 cp=main/'benchmark/2026-10-12-feed-classifier';ch='0bf966d76e038379af1fa2542746572a2c76a9bf88e17a97869682debfc36eaf';logs=[]
 for n in ['build-03','build-04']:
  d=cp/'evidence'/n;assert load(d/'outputs.json')['screen-gate-feed']==ch and (d/'arm.exit').read_text().strip()=='0';assert sha(d/'screen-gate-feed')==ch;logs.append({'commands':pin(d/'commands.json'),'stdout':pin(d/'arm.stdout'),'stderr':pin(d/'arm.stderr'),'rc':0})
 profile(ch,'ARM feed classifier','EXISTING_TWO_SOURCE_BUILDS_EQUAL',[cp/'candidate-pin.json',cp/'build.py'],['Full DevEco SDK distribution must be obtained separately; three tool/sysroot hashes are pinned, not a complete redistributable SDK archive.'],source=[pin(cp/'src/screen_gate_feed.c'),pin(cp/'src/stb_image.h')],tools=pin(cp/'evidence/build-04/inputs.json'),scripts=pin(cp/'build.py'),logs=logs)
 # Every target gets a status. Data/control files are not inflated into native source build successes.
 output=[];checked={}
 for target,h in sorted(targets.items()):
  source=None
  for loc in dict.fromkeys(local_sources[h]):
   pp=resolve(loc)
   if pp.is_file():
    if str(pp) not in checked:checked[str(pp)]=sha(pp)
    if checked[str(pp)]==h:source={'path':portable(pp),'sha256':h};break
  magic=b''
  if source:
   with resolve(source['path']).open('rb') as stream:magic=stream.read(4)
  kind='binary_or_compiled_data' if magic in [b'\x7fELF',b'dex\n',b'PK\x03\x04'] or Path(target).suffix in ['.so','.jar','.art','.oat','.vdex','.hap'] or target.endswith(('appspawn-x','screen-gate-feed')) else 'data_or_control'
  pr=profiles.get(h)
  if not pr:pr={'name':'retained '+Path(target).name,'source_build_status':'UNKNOWN_EXACT_BUILD_CLOSURE' if kind=='binary_or_compiled_data' else 'NOT_A_COMPILED_SOURCE_CLAIM','source_snapshot':None,'patch_sequence':None,'toolchain':None,'build_scripts':None,'original_rc0_logs':None,'deterministic_replay_status':'not_established','evidence':evidence,'gaps':['Exact producing source/patch/toolchain/build/log chain not established by retained artifact indexes.'] if kind=='binary_or_compiled_data' else ['Exact bytes retained; text/data restoration does not certify native source reproduction.']}
  output.append({'target':target,'sha256':h,'groups':groups[target],'kind':kind,'source_profile':h if h in profiles else None,'source_build_status':pr['source_build_status'],'restore_status':'EXACT_LOCAL_BYTES_AND_ARCHIVE_MEMBER_VERIFIED' if source and archive_hits[h] else 'EXACT_LOCAL_BYTES_ONLY' if source else 'LOCAL_SOURCE_UNKNOWN','artifact_source':source,'archive_members':archive_hits[h],'source_snapshot':pr['source_snapshot'],'patch_sequence':pr['patch_sequence'],'toolchain':pr['toolchain'],'build_scripts':pr['build_scripts'],'original_rc0_logs':pr['original_rc0_logs'],'deterministic_replay_status':pr['deterministic_replay_status'],'gaps':pr['gaps']})
 counts=dict(collections.Counter(x['source_build_status'] for x in output));restores=dict(collections.Counter(x['restore_status'] for x in output))
 write('artifact-inventory.json',{'signed_V2':pin(signed),'seal':pin(sealp),'targets':output,'unique_content_count':len(wanted),'counts':counts,'restore_counts':restores})
 write('source-profiles.json',profiles);write('archive-coverage.json',{'archives':archive_reports,'fresh_remote':remote_result})
 write('results.json',{'status':'AUDIT_COMPLETE_FULL_SOURCE_REBUILD_NOT_ESTABLISHED','signed_V2':pin(signed),'seal':pin(sealp),'file_targets':len(output),'group_assertions':sum(map(len,seal['files'].values())),'unique_contents':len(wanted),'source_status_counts':counts,'restore_status_counts':restores,'whole_stack_source_reproducible':False,'device_calls':0,'builds_executed':0,'fresh_remote':remote_result,'human_review':'pending','scope':'All824 unique signed file objects, including noncompiled data/control.130 application packages remain original signed package inventory; third-party app source builds not asserted.','packages_pin_count':len(seal['packages'])})
 print(json.dumps({'targets':len(output),'restore':restores,'source':counts,'remote':remote_result['status']}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--main',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();run(a.main,a.out)
