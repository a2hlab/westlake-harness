#!/usr/bin/env python3
"""Add reviewed source resolutions to the immutable v1 mapping; offline only."""
import argparse,collections,copy,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
V1='6e65f6fdcd06efb7a8cc8630b2cdd9f0b9de49631d9f5f0b2894e20589d4458e'
CODE={'.java','.c','.cpp','.cc','.h','.hpp','.inc','.py','.js','.smali','.rs','.S','.patch','.sh'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def generate(main,out,revision,resolutions,native155):
 main=main.resolve();assert sha(HERE/'release/source-build-mapping.json')==V1
 subprocess.run(['git','-C',str(main),'merge-base','--is-ancestor',revision,'master'],check=True)
 tree={}
 for line in subprocess.check_output(['git','-C',str(main),'ls-tree','-rz',revision]).split(b'\0'):
  if line:
   meta,path=line.split(b'\t');tree[path.decode()]=meta.decode().split()[2]
 def pin(path):
  p=main/path;return {'path':path,'sha256':sha(p)}
 def metadata(p):
  return {'path':str(p.resolve().relative_to(main)) if p.resolve().is_relative_to(main) else str(p.resolve().relative_to(HERE.parents[1])),'sha256':sha(p)}
 def source(e):
  p=main/e['path'];raw=p.read_bytes();assert sha(p)==e['sha256'],p
  blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert tree.get(e['path'])==blob,p
  return {**e,'git_blob':blob,'master_blob':blob,'master_tracked':True,'role':'implementation_patch' if p.suffix=='.patch' else e.get('role','source_candidate'),'expected_sha256':e['sha256'],'exact_expected_match':True,'license_status':e.get('license_status','original_headers_preserved_not_independent_license_audit')}
 d=load(HERE/'release/source-build-mapping.json');recipe_doc=load(HERE/'release/recipes/recipes.json');recipes={r['id']:r for r in recipe_doc['recipes']};rows={r['id']:r for r in d['rows']};updated=[]
 def install(rid,entries,recipe,gaps):
  assert entries and all(e['master_tracked'] for e in entries)
  row=rows[rid];row['source_entry']=entries;row['coverage_status']='MASTER_SOURCE_LOCATED_BINDING_PARTIAL';row['gaps']=gaps;row['native_delivery']=recipe['verification']['evidence'][0];row['complete_delivery_claim']=False
  row['source_revision']={'master_commit':revision,'expected_source_sha256':sorted({x['sha256'] for x in entries}),'exact_binding':True,'binding_scope':'source_evidence_pins_not_automatic_current_deployment','status':'exact_pins_match'}
  recipes[recipe['id']]=recipe;row['build_recipe']={'id':recipe['id'],'path':'recipes/recipes.json','sha256':None,'status':recipe['status']};updated.append(rid)
 for path in resolutions:
  for item in load(path)['rows']:
   entries=[source(e) for e in item['source_entry'] if Path(e['path']).suffix in CODE]
   docs=[pin(e['path']) for e in item['source_entry'] if Path(e['path']).suffix not in CODE]
   builds=[p for p in item['build_recipe'] if Path(p).suffix in ['.py','.sh']];entry=pin(builds[0]) if builds else None
   if entry:source(entry) # Every executable entry must be exact master code.
   recipe={'id':'supplement-'+item['id'],'status':'REVIEWED_IMPLEMENTATION_AND_RECIPE_SCOPE_PARTIAL','entry':entry,'recipe_documents':docs+[pin(p) for p in item['build_recipe']],'command':item.get('build_command',{'status':'unknown','argv':None}),'dependencies':{**item.get('build_dependencies',{'entries':[]}), 'gaps':item['limits']},'outputs':{'status':'unknown_new_build','entries':[]},'verification':{'status':'SOURCE_REVIEW_ONLY_NO_NEW_BUILD','evidence':[metadata(path)],'executed_this_audit':False,'gaps':item['limits']}}
   if item['id'] in ['JAVA-044','JAVA-047']:
    actual=copy.deepcopy(recipes[rows['JAVA-101']['build_recipe']['id']]);assert entries[0]['sha256'] in [x['sha256'] for x in rows['JAVA-101']['source_entry']]
    for field in ['command','dependencies','outputs','verification']:recipe[field]=actual[field]
    recipe['verification']['evidence'].insert(0,metadata(path));recipe['verification']['gaps']+=item['limits'];recipe['status']='NEW_ADAPTER_JAVA_BUILD_PASS_LIMITED_SERVICE_SEMANTICS'
   if item['id']=='JAVA-089':recipe['command']={'status':'ORIGINAL_SCRIPT_INTERFACE','argv':['bash',entry['path'],'$PINNED_DEPLOYED_STUB_JAR','$FRESH_OUT_JAR','$FRESH_WORK'],'working_directory':'$REPO','notes':'Preserves resources and allowlisted stub signatures. Requires original Android34/D8/smali dependency pins; no build executed.'}
   if item['id']=='NATIVE-137':recipe['command']={'status':'ORIGINAL_SCRIPT_INTERFACE','argv':['python3',entry['path'],'--workspace','$RESTORED_SOURCE_WORKSPACE','--out','$FRESH_OUT','--target','ohos'],'working_directory':'$REPO','notes':'Full original dependency graph required. This is compiler-option source delivery, not historical ICU byte reproduction.'}
   if item['id']=='JAVA-042':recipe['command']={'status':'DELIVERED_ISOLATED_NINJA_ENTRY','argv':['python3',entry['path'],'--archive','$PINNED_ARCHIVE','--out','$NEW_SCRATCH'],'preflight_argv':['python3',entry['path'],'--archive','$PINNED_ARCHIVE','--check-only'],'working_directory':'$REPO','notes':'Verifies archive/toolchain, recompiles actual source, preserves raw logs; not executed by this mapper.'}
   if item['id']=='NATIVE-138':
    recipe['command']={'status':'OFFLINE_INTERPRETED_COMPOSITION_STAGING','argv':['python3',entry['path'],'--out','$NEW_PAYLOAD'],'working_directory':'$REPO','notes':'Stages verified script/config bytes only; never invokes historical device scripts or compiles the five binaries.'}
    recipe['outputs']={'status':'HISTORICAL_SCRIPT_CONFIG_PAYLOAD_NOT_BINARY_REBUILD','entries':[]}
   if item['id']=='NATIVE-122':
    for e in entries:
     if e['path'].endswith('.patch'):e['role']='proposal_patch_not_deployed'
    recipe['verification']['status']='OWNER_REFERENCE_AND_UNEXECUTED_PROPOSAL_ONLY'
   install(item['id'],entries,recipe,item['limits'])
   if item['id']=='NATIVE-122':rows[item['id']]['coverage_status']='OWNER_REFERENCE_PROPOSAL_NOT_HISTORICAL_IMPLEMENTATION'

 n=load(native155);entries=[source(e) for k,e in n['sources'].items() if k!='tests']+rows['NATIVE-155']['source_entry'];entry=pin('harness/westlake_gap/cli.py');source(entry)
 recipe={'id':'supplement-NATIVE-155','status':'INTERPRETED_ROUTING_PRODUCER_AND_CONSUMER_DELIVERED','entry':entry,'command':{'status':'INTERPRETED_PROJECT_ENTRY','argv':['westlake-apk-gap','--help'],'environment':{'PYTHONPATH':'harness'},'working_directory':'$REPO','notes':'Installed pyproject.toml entry westlake_gap.cli:main; interface only, no device launch.'},'dependencies':{'status':'PYTHON_PROJECT_DEPENDENCIES','entries':[pin('pyproject.toml')],'gaps':['androguard unavailable in original reviewer environment; no tests were executed.']},'outputs':{'status':'INTERPRETED_SOURCE_NO_COMPILED_ARTIFACT','entries':[]},'verification':{'status':n['verification']['status'],'actual_exit_code':n['verification']['actual_exit_code'],'tests_executed':0,'evidence':[metadata(native155),n['sources']['tests']],'executed_this_audit':False,'gaps':n['scope']}}
 install('NATIVE-155',entries,recipe,n['scope'])
 # Member-level resolutions must not hide the already delivered full-overlay recipe.
 full=copy.deepcopy(recipes[rows['REG-006']['build_recipe']['id']]);full['id']='supplement-FZ-006-full-jar'
 full['command']['preparation_argv']=['python3','sources/api-implementations/FZ-006/full-jar/fetch-dependencies.py','--out','$PINNED_JAR_INPUTS']
 full.setdefault('recipe_documents',[]).append(pin('sources/api-implementations/FZ-006/full-jar/README.md'))
 recipes[full['id']]=full;lock=load(main/'sources/api-implementations/FZ-006/full-jar/sources.lock.json')
 for rid in ['JAVA-006','JAVA-007','JAVA-008','JAVA-009','JAVA-010','JAVA-011']:
  for e in rows[rid]['source_entry']:
   assert any(Path(x['path']).name==Path(e['path']).name and x['sha256']==e['sha256'] for x in lock['sources']),rid
  rows[rid]['build_recipe']={'id':full['id'],'path':'recipes/recipes.json','sha256':None,'status':full['status']};updated.append(rid)
 for row in d['rows']:
  row['source_revision']['master_commit']=revision
  for e in row['source_entry']:source(e)
 out.mkdir(parents=True,exist_ok=False);(out/'recipes').mkdir();p=out/'recipes/recipes.json';p.write_text(json.dumps({'schema':'api-build-recipes/v1','recipes':list(recipes.values())},ensure_ascii=False,indent=2)+'\n')
 for row in d['rows']:
  r=recipes[row['build_recipe']['id']];row['build_recipe']['sha256']=sha(p)
  for field,key in [('build_command','command'),('build_dependencies','dependencies'),('build_outputs','outputs'),('build_verification','verification')]:row[field]=r[key]
 d['master_commit']=revision;d['recipes']['sha256']=sha(p);d['supplement']={'base_mapping_sha256':V1,'updated_rows':updated,'historical_equivalence_upgraded':False};d['summary'].update(source_file_refs=sum(len(r['source_entry']) for r in d['rows']),master_exact_refs=sum(len(r['source_entry']) for r in d['rows']),coverage_counts=dict(collections.Counter(r['coverage_status'] for r in d['rows'])))
 (out/'source-build-mapping.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps(d['summary']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--main',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--master-revision',required=True);p.add_argument('--resolutions',type=Path,action='append',required=True);p.add_argument('--native155',type=Path,required=True);a=p.parse_args();generate(a.main,a.out,a.master_revision,a.resolutions,a.native155)
