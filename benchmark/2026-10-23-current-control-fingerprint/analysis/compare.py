from pathlib import Path,PurePosixPath
import json,hashlib,re,sys,datetime
out=Path(__file__).resolve().parent;workspaces=out.parents[3]
main=workspaces/'westlake-harness';video=workspaces/'westlake-harness-video'
current=video/'benchmark/2026-10-23-current-control-fingerprint/index.json';histpath=main/'benchmark/2026-10-23-launch-policy-provenance/results.json';acceptedpath=histpath.with_name('outer-review.json')
h=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p).replace(str(Path.home()),'$HOME'),'sha256':h(p.read_bytes()),'bytes':p.stat().st_size}
hist=json.loads(histpath.read_text());accepted=json.loads(acceptedpath.read_text());assert h(histpath.read_bytes())==accepted['results_sha256']
currentbytes=current.read_bytes();index=json.loads(currentbytes);history={x['board']:x for x in hist['comparison']}
pins={x['path']:x for x in hist['source_pins']}
historyfiles={};inputpins=[]
name61='.local/share/westlake/61b-demo-current-state-20261023/raw/02-fresh/rootsha_all.stdout';p61=Path.home()/name61
name5='benchmark/2026-10-22-toutiao-diagnostic-package/baseline/members.tsv';p5=main/name5
for name,p in [(name61,p61),(name5,p5)]:assert h(p.read_bytes())==pins[name]['sha256'];inputpins.append(pin(p))
for board,p in [('61b',p61),('5cd',p5)]:
 mapping={}
 for no,line in enumerate(p.read_text().splitlines(),1):
  fields=line.split()
  if len(fields)<2 or not re.fullmatch('[0-9a-f]{64}',fields[0]):continue
  path=fields[1].lstrip('*')
  if '/' not in path:mapping[path]={'sha256':fields[0],'metadata':pin(p),'line':no}
 historyfiles[board]=mapping
historyfiles['5cd']['members.tsv']={'sha256':pins[name5]['sha256'],'metadata':'T115 source_pins','path':name5}
for b in ['61b','5cd']:
 for item in hist['source_pins']:
  if item['path'].endswith('/startup.env') and (('deploy-package-r3-root' in item['path'])==(b=='61b')):
   historyfiles[b]['startup.env']={'sha256':item['sha256'],'metadata':'T115 source_pins','path':item['path']}
 if b=='61b':historyfiles[b]['@init']={'sha256':history[b]['init_cfg_sha'],'metadata':'T115 comparison/61b/init_cfg_sha'}
boards={};excluded=[]
for board,b in index['boards'].items():
 assert b['boot_pre']==b['boot_post'] and b['same_boot'];root=PurePosixPath(b['root']);boot=root/'boots'/b['boot_pre'];assert str(root)==history[board]['historical_root']
 argv=[s['path'] for s in b['init_cfg']['services']];assert any(str(root/'boot-entry.sh') in a for a in argv)
 actual=[];declared={}
 for cfg in b['config_files']:
  if cfg['path']==str(root/'members.tsv'):
   for line in cfg.get('content',[]):
    fields=line.split();assert len(fields)==3 and re.fullmatch('[0-9a-f]{64}',fields[0])
    assert not re.fullmatch('[0-9a-f]{64}',fields[1]);assert '/' not in fields[1]
    declared[fields[1]]=fields[0]
 rows=[dict(b['init_cfg'],where='init',exists=True)]+b['config_files']+b['hash_only_files']
 seen=set()
 for row in rows:
  path=PurePosixPath(row['path']);name=path.name
  if re.fullmatch('[0-9a-f]{64}',name):excluded.append({'board':board,'path':str(path),'reason':'64-hex basename is a parsed digest, not a member filename'});continue
  assert str(path) not in seen;seen.add(str(path))
  where='init' if row.get('where')=='init' else 'root' if path.parent==root else 'boot_copy' if path.parent==boot else 'unbound'
  assert where!='unbound'
  old=historyfiles[board].get('@init' if where=='init' else name)
  match='unknown_missing_current_file' if not row['exists'] else 'unknown_no_historical_pin' if old is None else 'match' if row['sha256']==old['sha256'] else 'different'
  actual.append({'path':str(path),'where':where,'exists':row['exists'],'sha256':row.get('sha256'),'size':row.get('size'),'history':old,'history_match':match,'current_members_declared_sha':declared.get(name),'matches_current_members':row.get('sha256')==declared[name] if row['exists'] and name in declared else None})
 for artifact in b.get('parse_artifact_rows',[]):
  path=PurePosixPath(artifact['queried_path']);assert re.fullmatch('[0-9a-f]{64}',path.name);assert path.parent in [root,boot];assert path.name in declared.values()
  excluded.append({'board':board,'path':str(path),'digest_matches_members_for':[n for n,v in declared.items() if v==path.name],'reported_exists':artifact['exists_reported'],'reason':'Digest field was queried as filename; excluded from file existence and mismatch counts.'})
 pairs=[]
 for row in actual:
  if row['where']!='root':continue
  other=next((x for x in actual if x['path']==str(boot/PurePosixPath(row['path']).name)),None)
  if other:pairs.append({'filename':PurePosixPath(row['path']).name,'root_sha256':row['sha256'],'boot_sha256':other['sha256'],'match':'match' if row['exists'] and other['exists'] and row['sha256']==other['sha256'] else 'unknown_missing_copy' if not other['exists'] else 'different'})
 boards[board]={'boot':b['boot_pre'],'root':str(root),'same_boot':True,'historical_boot':history[board]['hash_binding_boot'],'version_metadata':history[board]['generation_description'],'rows':actual,'root_vs_boot':pairs,'real_rows':len(actual),'history_match_counts':{k:sum(x['history_match']==k for x in actual) for k in ['match','different','unknown_missing_current_file','unknown_no_historical_pin']},'retry_count':'unknown','manual_reentry_runtime_mode':'unknown'}
cross=[]
for a in boards['61b']['rows']:
 if a['where']!='root':continue
 name=PurePosixPath(a['path']).name;other=next((x for x in boards['5cd']['rows'] if x['where']=='root' and PurePosixPath(x['path']).name==name),None)
 cross.append({'filename':name,'61b_sha':a['sha256'],'5cd_sha':other['sha256'] if other else None,'result':'unknown_not_in_5cd_inventory' if other is None else 'match' if a['sha256']==other['sha256'] else 'different'})
result={'task':'T116 independent metadata peer','phase':sys.argv[1],'reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'index':{'path':str(current).replace(str(Path.home()),'$HOME'),'sha256':h(currentbytes),'bytes':len(currentbytes),'started':index.get('started'),'ended':index.get('ended')},'t115':pin(histpath),'t115_acceptance':pin(acceptedpath),'historical_metadata_inputs':inputpins,'boards':boards,'excluded_parse_artifacts':excluded,'excluded_count':len(excluded),'cross_board_root_comparison':cross,'scope':'Metadata inputs only; no implementation file contents opened, no devices or stopped flows.','limits':['Hash/version matches establish observed file bytes only, not running process code or behavior.','Current parameters are unknown unless explicitly declared; event names/counts do not establish configuration.','No causal attribution, fix, cross-board copy or deployment recommendation.','Uninventoried files and missing boot config copies remain unknown, not assumed missing installation.']}
(out/(sys.argv[1]+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'phase':sys.argv[1],'index':result['index'],'boards':{k:{'rows':v['real_rows'],'history':v['history_match_counts']} for k,v in boards.items()},'excluded':len(excluded),'cross_differences':[x['filename'] for x in cross if x['result']=='different']},ensure_ascii=False))
