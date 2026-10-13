import json, hashlib, pathlib, tarfile, datetime
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
B=ROOT/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer'
S=B/'final61b-v2-seal/final-signoff.pending.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def resolve(s,base=ROOT):
 p=pathlib.Path(s.replace('$WORKSPACES',str(ROOT.parent)))
 return p if p.is_absolute() else base/p
checks=[]; pins=[]
def ck(name,ok,detail=None): checks.append({'check':name,'passed':bool(ok),'detail':detail})
def refs(d,base,label):
 if isinstance(d,dict):
  if isinstance(d.get('path'),str) and isinstance(d.get('sha256'),str):
   p=resolve(d['path'],base)
   actual=sha(p) if p.is_file() else None
   pins.append({'location':label,'path':d['path'],'expected':d['sha256'],'actual':actual,'equal':actual==d['sha256']})
  for k,v in d.items(): refs(v,base,label+'.'+k)
 elif isinstance(d,list):
  for i,v in enumerate(d): refs(v,base,label+'['+str(i)+']')
s=read(S); source_sha=sha(S); refs(s,S.parent,'signoff')
sealpath=resolve(s['source_seal']['path']); seal=read(sealpath); sealsha=sha(sealpath)
primary=s['primary_demo_61b']; boot=primary['candidate_boot']; proofpath=resolve(primary['new_seal_realization']['path']); proof=read(proofpath)
live=read(resolve(primary['final_live954']['path'])); dyn=live['dynamic_receipt']
ck('proof_source_seal_is_current_unsigned',proof['source_seal']['sha256']==sealsha and proof['source_identity']['sha256']==sealsha)
ck('live954_newproof_boot_all_equal',live['status']=='PASS' and live['passed'] and live['file_count']==len(live['checks'])==954 and all(c['equal'] and c['actual']==c['expected'] for c in live['checks']) and len({c['target'] for c in live['checks']})==954 and dyn['placement_proof_sha256']==sha(proofpath)==live['realization']['sha256'] and dyn['source_seal']['sha256']==sealsha and all(live[k]==boot for k in ['current_boot','boot_before','boot_after']) and dyn['current_boot']==proof['parameters']['boot_id']==boot)
capref=s['dynamic_evidence']['capture']; cappath=resolve(capref['path']); cap=read(cappath)
snapshot=read(B/'final61b-v2-realization/bound/snapshot.actual-adapter.json')
flat={}; conflicts=[]
for group in seal['files'].values():
 for target,h in group.items():
  if target in flat and flat[target]!=h: conflicts.append(target)
  flat[target]=h
raw={}; raw_receipts=[]
for key in cap['hash_receipts']:
 rec=cap['receipts'][key]; p=cappath.parent/rec['stdout']; ok=sha(p)==rec['sha256'] and rec['host_rc']==0;raw_receipts.append(ok)
 for line in p.read_text().splitlines():
  parts=line.split(None,1)
  if len(parts)==2 and len(parts[0])==64: raw[parts[1].lstrip('*')]=parts[0]
pkgs={p['apk_path']:p['apk_sha256'] for p in seal['packages']}
expected={**flat,**pkgs}; actual={c['target']:c['expected'] for c in live['checks']}
ck('capture_exact824_unique_files_130_packages',len(flat)==824 and not conflicts and len(pkgs)==len(seal['packages'])==130 and set(cap['package_names'])=={p['package'] for p in seal['packages']} and all(set(cap['groups'][k])==set(v) for k,v in seal['files'].items()) and snapshot['files']==seal['files'] and sorted(snapshot['packages'],key=lambda x:x['package'])==sorted(seal['packages'],key=lambda x:x['package']) and snapshot['collection_provenance']['capture_sha256']==sha(cappath),{'unique_files':len(flat),'group_entries':sum(map(len,seal['files'].values())),'packages':len(pkgs)})
ck('capture_raw_hashes_equal_954_and_live',all(raw_receipts) and raw==expected==actual,{'raw_receipts':len(raw_receipts),'raw_unique_paths':len(raw)})
ck('proof824_matches_seal_source_and_live',len(proof['files'])==824 and {f['target']:f['source_snapshot_sha256'] for f in proof['files']}==flat and all(f['source_seal_sha256']==sealsha and actual.get(f['target'])==f['sha256'] for f in proof['files']))
rootpath=resolve(primary['final_128_comparison_and_review']['path']); root=read(rootpath); refs(root,rootpath.parent,'root128')
for name,count in [('routeb487_admission',487),('boat18_admission',18)]:
 p=resolve(s['dynamic_evidence'][name]['path']);a=read(p);refs(a,p.parent,name)
 ck(name+'_actual_capture_review_binding',a['admitted'] and a['actual_reviewer']=='outer(codex)' and a['boot_id']==boot and len(a['exact_members'])==count and a['snapshot_capture']['sha256']==sha(cappath) and a['same61b128_review']['sha256']==sha(rootpath),{'members':len(a['exact_members']),'UI_review':a['UI_review'],'root_scoped_UI_acceptance':a.get('root_scoped_UI_acceptance')})
identities=[];windows=[];shard_rcs=[]
for w in root['completion_chain']['windows']:
 result=read(resolve(w['original_result']['path']));windows.append({k:result[k] for k in ['smoke','after_lock','before_unlock']});shard_rcs.extend(x['rc'] for x in result['shards'])
 for ref in w['identity_receipts']:
  d=read(resolve(ref['path']));identities.append(d['passed'] is True and d['diff']=={} and d['boot_before']==d['boot_after']==boot)
exitobs=read(resolve(root['driver_exit_observation']['path']));complete=read(resolve(root['round_complete']['path']))
ck('root128_original24identity_and8windows',len(identities)==24 and all(identities) and len(windows)==8 and all(all(x==0 for x in w.values()) for w in windows) and complete['recorded_keys']==128,{'identity_receipts':len(identities),'window_rcs':windows,'shard_rcs_preserved':{str(rc):shard_rcs.count(rc) for rc in sorted(set(shard_rcs))}})
ck('exit_observation_preserves_unknown_global_rc',root['driver_exited'] and root['driver_exit_code'] is None and root['completion_chain']['driver_exit_code'] is None and exitobs['driver_exited'] and exitobs['driver_exit_code'] is None and exitobs['ps_rc']==1,exitobs)
A=ROOT/'benchmark/2026-10-14-final61b-final-evidence-archive';ar=read(A/'archive.json');manifest=A/'.artifacts/source-manifest.jsonl';rows=[json.loads(x) for x in manifest.read_text().splitlines()];mi={x['path']:x for x in rows};tar=A/'.artifacts/final61b-final-evidence.tar.gz'
ck('second_archive_R_pin',sha(A/'archive.json')=='374b57b0d4fffaf504ad6608a9d37decd957fe49d9d7d8d89e4fd4fc03f3df43')
ck('second_archive_local_tar_manifest_pins',sha(tar)==ar['sha256'] and sha(manifest)==ar['source_manifest_sha256'] and len(rows)==ar['files']==2320)
with tarfile.open(tar,'r:gz') as tf:
 members={m.name.removeprefix('./'):m for m in tf.getmembers() if m.isfile()}
 docs=[]
 for name,ref in s['documentation'].items():
  p=resolve(ref['path']);rel=str(p.relative_to(ROOT));h=hashlib.sha256(tf.extractfile(members[rel]).read()).hexdigest();docs.append({'name':name,'sha256':h,'equal':h==ref['sha256']==mi[rel]['sha256']==sha(p)})
 ck('three_operation_documents_signoff_manifest_tar_equal',len(docs)==3 and all(x['equal'] for x in docs),docs)
 ck('signoff_S_excluded_from_A',str(S.relative_to(ROOT)) not in mi and str(S.relative_to(ROOT)) not in members)
ck('all_explicit_local_reference_pins',all(x['equal'] for x in pins),{'checked':len(pins),'mismatches':[x for x in pins if not x['equal']]})
ck('reviewed_unsigned_source_unchanged',sha(S)==source_sha)
report={'schema':'final61b-final-dynamic-peer-review/v1','status':'ACCEPT' if all(c['passed'] for c in checks) else 'BLOCKER','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_signoff':{'path':str(S.relative_to(ROOT)),'sha256':source_sha,'status':s['status']},'scope':'Independent local mechanical cross-check of filled unsigned final signoff dynamic evidence. No device calls, remote calls, source edits, new gates or historical test reruns. Signature remains root authority.','device_calls':0,'source_edits':0,'checks':checks,'reference_pins':pins,'limitations':['Global driver OS exit code remains unknown/null; shard return codes are not upgraded.','Existing startup-only/partial/excluded UI grades and function limitations remain unchanged.','Remote archive was not freshly contacted; local bytes and existing pinned archive receipt were checked.']}
(OUT/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':report['status'],'checks':len(checks),'pin_count':len(pins),'failed':[c for c in checks if not c['passed']]},ensure_ascii=False))
