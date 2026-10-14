#!/usr/bin/env python3
"""Add source/build delivery fields to immutable315 records; never run build recipes."""
import argparse,collections,copy,csv,hashlib,importlib.util,json,os,posixpath,re,shutil,subprocess,sys
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent;WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2]))).resolve();MAIN=WS/'westlake-harness'
CORE=MAIN/'benchmark/2026-10-14-api-progress-final61b';PARENT=MAIN/'benchmark/2026-10-13-api-progress-r6-full128'
DELIVERY=('source_entry','source_revision','build_recipe','build_command','build_dependencies','build_outputs','build_verification')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,j):Path(p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git','-C',str(MAIN),*args])
def resolve(name):
 if name.startswith('$REPO/'):name=name.removeprefix('$REPO/')
 local=read(HERE/'historical-aliases.json') if (HERE/'historical-aliases.json').is_file() else {}
 if name in local:
  p=HERE/local[name]['path'];need(p.is_file() and sha(p)==local[name]['sha256'],'new historical evidence alias drift');return p.resolve()
 aliases=read(PARENT/'historical-evidence-aliases.json')
 if name in aliases:
  p=PARENT/aliases[name]['path'];need(p.is_file() and sha(p)==aliases[name]['sha256'],'historical signed evidence alias drift');return p.resolve()
 if Path(name).is_absolute():p=Path(name)
 elif name.startswith('$WORKSPACES/'):p=WS/name.removeprefix('$WORKSPACES/')
 else:need(not Path(name).is_absolute() and '..' not in Path(name).parts,'repository-relative source path required');p=MAIN/name
 need(p.is_file() and not p.is_symlink(),'source missing/nonregular: '+name);return p.resolve()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def master_tree(revision=None):
 revision=revision or git('rev-parse','master').decode().strip();files={}
 need(bool(re.fullmatch('[0-9a-f]{40}',revision)),'full master revision required')
 git('merge-base','--is-ancestor',revision,'master')
 for line in git('ls-tree','-rz','--full-tree',revision).split(b'\0'):
  if line:meta,name=line.split(b'\t',1);files[name.decode()]=meta.decode().split()[2]
 return revision,files
def audit_entry(entry,master,tree,allow_unpublished_missing=False):
 try:p=resolve(entry['path'])
 except ValueError:
  need(allow_unpublished_missing,'actual published source/build entry unavailable: '+entry['path'])
  return {'path':entry['path'],'sha256':entry['sha256'],'git_blob':None,'available':False,'master_commit_checked':master,'master_tracked_exact':False,'master_relative_path':None,'master_url':None,'remote_publication_verified':None}
 need(sha(p)==entry['sha256'],'actual source/build entry SHA drift: '+entry['path']);actual_blob=blob(p.read_bytes())
 if 'git_blob' in entry:need(actual_blob==entry['git_blob'],'source blob drift')
 rel=p.relative_to(MAIN).as_posix() if p.is_relative_to(MAIN) else None
 tracked=rel is not None and tree.get(rel)==actual_blob and not Path(entry['path']).is_absolute()
 return {'path':entry['path'],'sha256':entry['sha256'],'git_blob':actual_blob,'available':True,'master_commit_checked':master,'master_tracked_exact':tracked,'master_relative_path':rel if tracked else None,'master_url':'https://github.com/A2OH/westlake-harness/blob/master/'+rel if tracked else None,'remote_publication_verified':None}
def complete(row,recipe,audit,build_audit):
 entries=row['source_entry'];verification=row['build_verification']
 return (bool(entries) and all(e.get('role')=='implementation' and e.get('exact_expected_match') is True for e in entries)
  and all(x['master_tracked_exact'] for x in audit) and row['source_revision'].get('exact_binding') is True
  and recipe.get('entry') is not None and build_audit is not None and build_audit['master_tracked_exact'] is True
  and isinstance(row['build_command'].get('argv'),list) and bool(row['build_command']['argv'])
  and bool(row['build_outputs'].get('entries')) and not row['build_dependencies'].get('gaps')
  and bool(verification.get('evidence')) and not verification.get('gaps') and not row.get('gaps')
  and row['record_kind']=='api_capability' and row['implementation_status']!='stub')
def mapping_rows(base,mapping):
 old={r['id']:r for r in base};mapped={r['id']:r for r in mapping['rows']}
 need(len(base)==len(mapped)==len(mapping['rows'])==315 and set(old)==set(mapped),'mapping missing/duplicate/unknown IDs')
 for rid,original in old.items():
  item=mapped[rid];need(all(k in item for k in DELIVERY),'mapping delivery field missing: '+rid)
  need(item['implementation_status']==original['implementation_status'] and item['record_kind']==original['record_kind'],'mapping original semantic grade differs')
 return old,mapped
def consume(mapping_path,mapping_sha,master_revision=None):
 need(sha(mapping_path)==mapping_sha,'mapping fullSHA drift');mapping=read(mapping_path)
 need(mapping.get('schema')=='api-source-build-mapping/v1','mapping schema mismatch')
 base_ref=read(HERE/'base-pin.json');base_path=resolve(base_ref['path']);need(sha(base_path)==base_ref['sha256']==mapping['input']['sha256'],'signed315 base drift')
 base=read(base_path)['rows'];old,mapped=mapping_rows(base,mapping)
 recipe_path=mapping_path.parent/mapping['recipes']['path'];need(recipe_path.resolve().is_relative_to(mapping_path.parent.resolve()) and recipe_path.is_file() and sha(recipe_path)==mapping['recipes']['sha256'],'shared recipe pin drift')
 recipes=read(recipe_path);byrecipe={r['id']:r for r in recipes['recipes']};need(len(byrecipe)==len(recipes['recipes']),'duplicate recipe IDs')
 master,tree=master_tree(master_revision);rows=[];known_refs={};unresolved={};source_count=0;complete_count=0;master_refs=0
 for rid,original in old.items():
  mapped_row=mapped[rid];need(all(k in mapped_row for k in DELIVERY),'mapping delivery field missing: '+rid)
  need(mapped_row['implementation_status']==original['implementation_status'] and mapped_row['record_kind']==original['record_kind'],'mapping original semantic grade differs')
  recipe=byrecipe[mapped_row['build_recipe']['id']];need(mapped_row['build_recipe']['sha256']==mapping['recipes']['sha256'],'row recipe pin differs')
  audit=[];row_missing=[]
  for entry in mapped_row['source_entry']:
   item=audit_entry(entry,master,tree,allow_unpublished_missing=entry.get('master_tracked') is False);tracked=item['master_tracked_exact'];audit.append(item)
   if item['available']:known_refs[entry['path']]=entry['sha256']
   else:unresolved[entry['path']]={'sha256':entry['sha256'],'reason':'Unpublished candidate absent from MAIN; no private-tree fallback'};row_missing.append(entry['path'])
   source_count+=1;master_refs+=tracked
  def refs(value):
   if isinstance(value,dict):
    name,digest=value.get('path'),value.get('sha256')
    if isinstance(name,str) and isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest) and not name.startswith('$A2HLAB_WS'):
     try:p=resolve(name)
     except ValueError as exc:
      unresolved[name]={'sha256':digest,'reason':str(exc)};row_missing.append(name)
     else:
      if name not in known_refs:need(sha(p)==digest,'build/source evidence pin drift: '+name)
      else:need(known_refs[name]==digest,'inconsistent reference SHA: '+name)
      known_refs[name]=digest
    for v in value.values():refs(v)
   elif isinstance(value,list):
    for v in value:refs(v)
  for field in ('build_dependencies','build_verification'):refs(mapped_row[field])
  build_audit=audit_entry(recipe['entry'],master,tree) if recipe.get('entry') is not None else None
  if recipe.get('entry') is not None:refs(recipe['entry'])
  refs(recipe.get('recipe_documents',[]))
  is_complete=complete(mapped_row,recipe,audit,build_audit) and not row_missing;need(not mapped_row.get('complete_delivery_claim') or is_complete,'mapper claims complete despite missing/stub/master/build gap')
  row=copy.deepcopy(original);row.update({key:copy.deepcopy(mapped_row[key]) for key in DELIVERY})
  row.update(source_delivery_status=mapped_row['coverage_status'],source_delivery_gaps=copy.deepcopy(mapped_row.get('gaps',[]))+['Pinned dependency/output unavailable locally: '+name for name in sorted(set(row_missing))]+(['Build entry is not an exact MAIN/master tracked repository file'] if build_audit is not None and not build_audit['master_tracked_exact'] else []),source_master_audit=audit,source_delivery_complete=is_complete,build_entry=recipe.get('entry'),build_entry_master_audit=build_audit,build_recipe_documents=recipe.get('recipe_documents',[]))
  complete_count+=is_complete;rows.append(row)
 return rows,recipes,{'schema':'api-source-delivery/v1','mapping_sha256':mapping_sha,'base_sha256':base_ref['sha256'],'master_commit_checked':master,'mapping_master_commit':mapping['master_commit'],'rows':315,'original_semantic_rows_unchanged':315,'source_file_refs':source_count,'master_exact_source_refs':master_refs,'complete_api_delivery_rows':complete_count,'all315_complete':complete_count==315,'coverage_counts':dict(collections.Counter(r['source_delivery_status'] for r in rows)),'known_source_build_refs':known_refs,'unresolved_source_build_refs':unresolved,'device_calls':0,'builds_executed':0,'remote_master_publication_verified':None}
def ref_paths(value):
 names=[]
 if isinstance(value,dict):
  if isinstance(value.get('path'),str):names.append(value['path'])
  for v in value.values():names.extend(ref_paths(v))
 elif isinstance(value,list):
  for v in value:names.extend(ref_paths(v))
 return sorted(set(names))
def source_href(name):
 root=PurePosixPath('/WORKSPACES/westlake-harness');origin=root/'benchmark/2026-10-14-api-source-delivery/views'
 if name=='recipes/recipes.json':return name
 if Path(name).is_absolute():return name
 local=read(HERE/'historical-aliases.json') if (HERE/'historical-aliases.json').is_file() else {}
 if name in local:return '../'+local[name]['path']
 aliases=read(PARENT/'historical-evidence-aliases.json')
 if name in aliases:target=root/'benchmark/2026-10-13-api-progress-r6-full128'/aliases[name]['path']
 elif name.startswith('$WORKSPACES/'):target=PurePosixPath('/WORKSPACES')/name.removeprefix('$WORKSPACES/')
 elif name.startswith('$REPO/'):target=root/name.removeprefix('$REPO/')
 else:target=root/name
 return posixpath.relpath(str(target),str(origin))
def shell(view,rows,summary):
 sys.path.insert(0,str(CORE));spec=importlib.util.spec_from_file_location('signed315_atlas',CORE/'increment.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
 native=next(r for r in rows if r['id']=='NATIVE-173');atlas=core.setup(view,native);oldcollect=atlas.collect_rows
 def collect():
  try:shards,_=oldcollect()
  finally:atlas.HERE=view
  byid={r['id']:r for r in rows}
  for shard in shards.values():shard['rows']=[copy.deepcopy(byid[r['id']]) for r in shard['rows']]
  return shards,copy.deepcopy(rows)
 atlas.collect_rows=collect;atlas.CSV_FIELDS=atlas.CSV_FIELDS+DELIVERY+('source_delivery_status','source_delivery_gaps','source_master_audit','source_delivery_complete','build_entry','build_entry_master_audit','build_recipe_documents')
 original_resolve=atlas.resolve
 def evidence_resolve(name):
  local=read(HERE/'historical-aliases.json') if (HERE/'historical-aliases.json').is_file() else {}
  return resolve(name) if name in local else original_resolve(name)
 atlas.resolve=evidence_resolve
 atlas.source_link=lambda name,label=None:'['+(label or Path(name).name)+'](<'+source_href(name)+'>)'
 oldmd=atlas.markdown;oldhtml=atlas.html_atlas
 def markdown(records,metadata):
  text=oldmd(records,metadata)+'\n## 实际源码与构建入口（交付覆盖单独判定）\n\n'
  for row in records:
   text+='### '+row['id']+' source/build\n\n'+row['source_delivery_status']+'\n\n'
   for entry,audit in zip(row['source_entry'],row['source_master_audit']):text+='- '+(atlas.source_link(entry['path']) if audit['master_tracked_exact'] else 'Unpublished candidate; no user source entry')+' `'+entry['sha256']+'`；role='+entry['role']+'\n'
   text+='- revision: `'+json.dumps(row['source_revision'],ensure_ascii=False)+'`\n- recipe: '+atlas.source_link('recipes/recipes.json',row['build_recipe']['id'])+'\n'
   if row['build_entry'] and row['build_entry_master_audit']['master_tracked_exact']:text+='- build entry: '+atlas.source_link(row['build_entry']['path'])+'\n'
   for key in ('build_command','build_dependencies','build_outputs','build_verification'):
    text+='- '+key+': `'+json.dumps(row[key],ensure_ascii=False)+'`\n'
    for name in ref_paths(row[key]):
     if name in summary['known_source_build_refs']:text+='- '+atlas.source_link(name)+'\n'
   text+='- 交付缺口：'+'；'.join(row['source_delivery_gaps'])+'\n\n'
  return text
 atlas.markdown=markdown
 def html(records,metadata):
  text=oldhtml(records,metadata);names={e['path'] for r in records for e in r['evidence']}|{e['path'] for e in read(view/'platform-context.json')}|set(summary['known_source_build_refs'])|{'recipes/recipes.json'}
  mapping=json.dumps({name:source_href(name) for name in sorted(names)},ensure_ascii=False).replace('<','\\u003c')
  text,n=re.subn(r'const evidenceLinks=\{[^\n]*\};',lambda m:'const evidenceLinks='+mapping+';',text);need(n==1,'original HTML link seam changed')
  extension="""d.append(el('h4','实际源码 / Source and build delivery','section'),el('p',r.source_delivery_status));const src=el('ul');for(const e of r.source_entry){const li=el('li'),audit=r.source_master_audit.find(x=>x.path===e.path);if(audit&&audit.master_tracked_exact){const a=el('a',e.path);a.href=link(e.path);li.append(a);}else{li.append(el('span','Unpublished candidate; no user source entry'));}li.append(el('code',' SHA256 '+e.sha256+' / '+e.role));if(audit&&audit.master_url){const master=el('a',' master');master.href=audit.master_url;li.append(master);}src.append(li);}if(!r.source_entry.length)src.append(el('li','缺实际实现源码 / Actual implementation source missing'));d.append(src);const recipe=el('a','Build recipe '+r.build_recipe.id);recipe.href=link('recipes/recipes.json');d.append(recipe);if(r.build_entry&&r.build_entry_master_audit&&r.build_entry_master_audit.master_tracked_exact){const entry=el('a',' · Direct build entry');entry.href=link(r.build_entry.path);d.append(entry);}for(const key of ['source_revision','build_command','build_dependencies','build_outputs','build_verification']){d.append(el('h5',key),el('pre',JSON.stringify(r[key],null,2)));const walk=v=>{if(v&&typeof v==='object'){if(v.path&&Object.prototype.hasOwnProperty.call(evidenceLinks,v.path)){const a=el('a',v.path);a.href=link(v.path);d.append(a,el('br'));}for(const child of Object.values(v))walk(child);}};walk(r[key]);}d.append(el('p',r.source_delivery_gaps.join(' / ')));"""
  token="$('rows').append(d);";need(text.count(token)==1,'original card seam changed');text=text.replace(token,extension+token)
  return text.replace('2026.10.14 · FINAL61B SCOPED128','2026.10.14 · SOURCE DELIVERY').replace('<div class="metrics"','<p>源码交付覆盖与API实现/板测等级分开；缺项不签完整交付。Source coverage is separate from API functionality. Missing items prevent complete delivery.</p><div class="metrics"',1)
 atlas.html_atlas=html
 return atlas,core
def build(mapping,mapping_sha,view,require_complete=False):
 rows,recipes,summary=consume(mapping,mapping_sha);need(not require_complete or summary['all315_complete'],'full315 source/build delivery remains incomplete')
 need(not view.exists(),'fresh views required');view.mkdir(parents=True);(view/'recipes').mkdir()
 for name in ('row-template.json','curation.json','platform-context.json'):shutil.copy2(CORE/'views'/name,view/name)
 write(view/'recipes/recipes.json',recipes);atlas,core=shell(view,rows,summary);metadata=atlas.build();metadata.update(source_delivery={k:v for k,v in summary.items() if k!='known_source_build_refs'})
 data=read(view/'api-progress.json');data['metadata']=metadata;write(view/'api-progress.json',data);write(view/'results.json',metadata)
 (view/'API-PROGRESS.zh.md').write_text(atlas.markdown(rows,metadata));zh=atlas.html_atlas(rows,metadata);(view/'index.html').write_text(zh)
 binding=read(MAIN/'benchmark/2026-10-14-api-progress-final61b-publication/actual/binding.json')
 (view/'index.en.html').write_text(core.english_html(zh,next(r for r in rows if r['id']=='NATIVE-173'),binding))
 write(view/'source-delivery.json',summary);return check(mapping,mapping_sha,view)
def check(mapping,mapping_sha,view):
 recorded=read(view/'source-delivery.json')
 rows,recipes,summary=consume(mapping,mapping_sha,recorded['master_commit_checked']);need(summary==recorded,'source delivery summary drift');atlas,core=shell(view,rows,summary)
 extended=atlas.CSV_FIELDS;atlas.CSV_FIELDS=tuple(k for k in extended if k not in DELIVERY and k not in ('source_delivery_status','source_delivery_gaps','source_master_audit','source_delivery_complete','build_entry','build_entry_master_audit','build_recipe_documents'))
 try:result=atlas.check()
 finally:atlas.CSV_FIELDS=extended
 data=read(view/'api-progress.json')
 check_csv(view/'api-progress.csv',data['rows'],extended)
 base={r['id']:r for r in read(resolve(read(HERE/'base-pin.json')['path']))['rows']}
 need(all(all(row[key]==value for key,value in base[row['id']].items()) for row in data['rows']),'old315 semantic field drift')
 need(read(view/'recipes/recipes.json')==recipes,'shared recipe regeneration drift')
 zh=(view/'index.html').read_text();en=(view/'index.en.html').read_text();binding=read(MAIN/'benchmark/2026-10-14-api-progress-final61b-publication/actual/binding.json')
 need(en==core.english_html(zh,next(r for r in rows if r['id']=='NATIVE-173'),binding),'English HTML drift')
 marker='<script id="data" type="application/json">';need(zh.split(marker,1)[1].split('</script>',1)[0]==en.split(marker,1)[1].split('</script>',1)[0],'bilingual canonical data drift')
 summary.update(original_generator_check=result,semantic_rows_unchanged=315,views_checked=True,delivery_complete_claim=summary['all315_complete']);return summary
def check_csv(path,rows,fields):
 with Path(path).open(encoding='utf-8-sig',newline='') as stream:exported=list(csv.DictReader(stream))
 need(len(exported)==len(rows),'CSV membership drift')
 for row,record in zip(rows,exported):
  for key in fields:
   value=row[key];expected=json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else ('' if value is None else str(value))
   need(record[key]==expected,row['id']+': additive CSV field drift '+key)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build','check']);parser.add_argument('--mapping',type=Path,required=True);parser.add_argument('--mapping-sha256',required=True);parser.add_argument('--out',type=Path,default=HERE/'views');parser.add_argument('--require-complete',action='store_true');a=parser.parse_args()
 try:
  need(a.out.resolve().is_relative_to(HERE),'output must remain in this T0 delivery packet')
  result=build(a.mapping,a.mapping_sha256,a.out,a.require_complete) if a.command=='build' else check(a.mapping,a.mapping_sha256,a.out)
  print(json.dumps({k:v for k,v in result.items() if k!='known_source_build_refs'},ensure_ascii=False));return 0
 except (ValueError,AssertionError,OSError,KeyError,TypeError) as exc:print('REJECT '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
