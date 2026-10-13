"""Read pinned original final61b receipts; never contact a board or sign acceptance."""
import hashlib,json,os,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2]))).resolve()
SERIAL='61b0657200000000000000000324012c'
BOOT='086db6c7-a7e7-40ce-a336-9608adc05afc'
RUNTIME='f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0'
FIELDS={'oh_tested','route_generation','validations','gaps','evidence'}
BMS_SCHEMA='61b-full128-independent-observation/v1'

def need(ok,message):
 if not ok:raise ValueError(message)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(value):
 need(isinstance(value,str) and value,'missing evidence path')
 p=WS/value.removeprefix('$WORKSPACES/') if value.startswith('$WORKSPACES/') else Path(value)
 need(p.is_absolute() and '..' not in p.parts,'use absolute or $WORKSPACES evidence path')
 need(p.is_file() and not p.is_symlink(),'missing/nonregular evidence: '+value)
 need(p.resolve().is_relative_to(WS),'evidence outside WORKSPACES')
 return p.resolve()
def pin(ref):
 need(isinstance(ref,dict) and isinstance(ref.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',ref['sha256']),'complete fullSHA pin required')
 p=resolve(ref.get('path'));need(sha(p)==ref['sha256'],'evidence SHA drift: '+str(p));return p
def ref_pair(ref):return {k:ref[k] for k in ('path','sha256')}
def base():
 refs=read(HERE/'base-pins.json');paths=[pin(r) for r in refs]
 manifest=read(paths[4]);tiers=read(paths[5]);apps={r['key']:r for r in manifest['apps']}
 need(len(apps)==len(manifest['apps'])==128,'original manifest128 drift')
 tier={r['key']:r['screenshot_seconds'] for r in tiers['apps']}
 need(set(tier)==set(apps) and list(tier.values()).count(10)==121 and list(tier.values()).count(20)==7,'original121/7 tiers drift')
 return apps,tier
def actual_rows(doc):
 need(isinstance(doc,dict) and doc.get('synthetic',False) is False and doc.get('fixture',False) is False,'synthetic/fixture is not actual evidence')
 rows=doc.get('rows');need(isinstance(rows,list) and rows,'missing original rows')
 return rows
def row_objects(rows,apps,tiers,verify_pin=pin):
 keys=set();images=0;records={}
 for row in rows:
  key=row.get('key');need(key in apps and key not in keys,'duplicate/unknown key');keys.add(key)
  rec=read(verify_pin(row.get('record')))
  need(rec.get('synthetic',False) is False and rec.get('fixture',False) is False,'non-actual record')
  need(rec.get('serial')==SERIAL and rec.get('boot_id')==BOOT and rec.get('key')==key,'record board/boot/key differs')
  need(rec.get('apk_sha256')==apps[key]['apk_sha256'] and rec.get('package')==apps[key]['package'],'record APK identity differs')
  need(row.get('record_status',rec['status'])==rec['status'],'original app status relabeled')
  shots=row.get('actual_images',row.get('shots'))
  need(isinstance(shots,list) and len(shots)==2 and sorted(x.get('scheduled_seconds',-1) for x in shots)==[5,tiers[key]],'original shot tier differs')
  rawshots=rec.get('screenshots',[])
  need(len(rawshots)==2,'record missing actual shots')
  for shot in shots:
   verify_pin(shot)
   matches=[r for r in rawshots if r.get('scheduled_seconds')==shot['scheduled_seconds'] and r.get('sha256')==shot['sha256']]
   need(len(matches)==1 and matches[0].get('captured') is True,'record/screenshot pin differs')
  records[key]=ref_pair(row['record']);images+=2
 return keys,images,records
def validate_facts(text,tiers):
 totals=re.findall(r'^TOTAL keys=(\d+) screenshots_captured=(\d+)/(\d+)(?:\s|$)',text,re.M)
 need(totals==[('128','256','256')],'incomplete original aggregate facts')
 rows=re.findall(r'^(\S+)\s+shots\s+2/2\s+alive\s+t5=\S+\s+t(10|20)=\S+',text,re.M)
 need(len(rows)==128 and len({k for k,t in rows})==128,'facts missing/duplicate canonical keys')
 need({k:int(t) for k,t in rows}==tiers,'facts key/tier differs')
 return text.splitlines()[-1]
def detached_completion(records):
 # The original --detach writes PID/log only. Never invent a global wait() rc.
 driver=pin(read(HERE/'base-pins.json')[6])
 need(sha(driver)=='4938bcf88c572af5cead2cbb73b8f1d66f9b38d44afbe8306b097d76197f7caa','original detached driver drift')
 windows=set()
 for ref in records.values():
  ancestors=[p for p in resolve(ref['path']).parents if re.fullmatch(r'window-0[1-8]',p.name)]
  need(len(ancestors)==1,'record original window path ambiguous');windows.add(ancestors[0])
 need(len(windows)==8 and len({p.parent for p in windows})==1,'actual eight-window chain differs')
 root=next(iter(windows)).parent
 def actual_ref(path):
  ref={'path':'$WORKSPACES/'+path.relative_to(WS).as_posix(),'sha256':sha(path)}
  return ref,read(pin(ref))
 complete_ref,complete=actual_ref(root/'round-complete.json')
 need(type(complete.get('recorded_keys')) is int and complete['recorded_keys']==128,'original round completion missing128')
 receipts=[]
 for window in sorted(windows):
  ref,result=actual_ref(window/'runner/board-run-result.json')
  need(all(type(result.get(k)) is int and result[k]==0 for k in ('smoke','after_lock','before_unlock')),'original window rc failed/unknown: '+window.name)
  identities=[]
  for phase in ('pre-lock-identity','before-identity','after-identity'):
   identity_ref,identity=actual_ref(window/phase/'identity.json')
   need(identity.get('synthetic') is False and identity.get('passed') is True and identity.get('diff')=={},'original identity failed: '+window.name+'/'+phase)
   need(identity.get('serial')==SERIAL and identity.get('boot_before')==identity.get('boot_after')==BOOT,'identity board/boot differs')
   identities.append(identity_ref)
  receipts.append({'window':window.name,'original_result':ref,'identity_receipts':identities})
 return {'completion':complete_ref,'driver_source':ref_pair(read(HERE/'base-pins.json')[6]),'windows':receipts,'driver_exit_code':None,'driver_exit_code_basis':'NOT_CAPTURED_BY_ORIGINAL_DETACH; outer observed process exit; normal terminal path writes round-complete'}
def peer_rows(doc,apps,tiers,records):
 need(str(doc.get('status','')).startswith('ACCEPT_SCOPED'),'original peer scoped window review incomplete')
 rows=actual_rows(doc);keys=set();preserved=[]
 for row in rows:
  key=row.get('key');need(key in apps and key in records and key not in keys,'peer duplicate/unknown key');keys.add(key)
  need(row.get('record_sha256')==records[key]['sha256'] and row.get('boot_id')==BOOT,'peer actual record SHA/boot differs')
  rec=read(pin(records[key]))
  need(rec.get('apk_sha256')==apps[key]['apk_sha256'],'canonical APK differs')
  if 'apk_sha256' in row:need(row['apk_sha256']==rec['apk_sha256'],'peer APK differs')
  image={'path':row.get('actual_image'),'sha256':row.get('actual_image_sha256')};pin(image)
  matches=[s for s in rec['screenshots'] if s.get('scheduled_seconds')==tiers[key] and s.get('sha256')==image['sha256'] and s.get('captured') is True]
  need(len(matches)==1,'peer last-tier image differs from canonical actual record')
  for field in ('reviewed_scheduled_seconds','demo_capture_seconds'):
   if field in row:need(type(row[field]) in (int,float) and row[field]==tiers[key],'peer scheduled tier differs')
  if 'shot_tiers_sha256' in row:need(row['shot_tiers_sha256']==read(HERE/'base-pins.json')[5]['sha256'],'peer tier source differs')
  need(isinstance(row.get('verdict'),str) and row['verdict'] and isinstance(row.get('observation'),str) and row['observation'],'peer original verdict/observation missing')
  need(row.get('raw_record_modified',False) is False,'peer relabeled raw record')
  preserved.append({'key':key,'verdict':row['verdict'],'observation':row['observation'],'actual_image':image,'record_sha256':row['record_sha256'],'apk_basis':'explicit original peer field' if 'apk_sha256' in row else 'same pinned canonical record; original peer field absent','tier_basis':'original field checked' if 'reviewed_scheduled_seconds' in row else 'original last-tier image matched; original peer field absent'})
 return keys,preserved
def review_route(refs,apps,tiers,records,kind='bms',complete=True):
 need(isinstance(refs,list) and refs,'missing review route')
 need(kind in ('bms','nativepeer'),'known independent reviewer provenance required')
 seen=set();receipt_pairs=[];preserved=[]
 for ref in refs:
  path=pin(ref);doc=read(path);receipt_pairs.append(ref_pair(ref))
  if kind=='nativepeer':
   need(path.parent.name=='2026-10-14-final61b-full128-peer' and re.fullmatch(r'window0[1-8]-review\.json',path.name),'nativepeer original receipt path required; BMS closeout is same BMS route')
   keys,original=peer_rows(doc,apps,tiers,records);preserved.extend(original)
   need(not(seen&keys),'peer duplicate canonical key');seen.update(keys);continue
  if 'observer_checkpoint' in doc:
   observer=read(pin(doc['observer_checkpoint']));rows=actual_rows(observer)
   need(observer.get('schema')==BMS_SCHEMA,'original BMS observer schema required')
   result=doc.get('visual_result',{})
   need(result.get('reviewed_keys')==len(rows) and result.get('reviewed_actual_images')==2*len(rows),'incomplete original closeout review')
   need('new_visible_regressions' in result and isinstance(result.get('limitations'),list),'missing closeout disposition/limits')
  else:
   rows=actual_rows(doc)
   need(doc.get('schema')==BMS_SCHEMA,'original BMS observer required; nativepeer has its own route')
   for row in rows:
    shots=row.get('actual_images',row.get('shots',[]))
    need(len(shots)==2 and all(s.get('personally_viewed') is True for s in shots),'review images not actually reviewed')
    need(any(row.get(k) for k in ('visual','independent_visual','comparison','visual_note','note')),'missing original per-key review')
  keys,_,refs_by_key=row_objects(rows,apps,tiers)
  need(not(seen&keys),'review duplicate canonical key');seen.update(keys)
  need(all(records[k]==refs_by_key[k] for k in keys),'review is from another actual run')
 if complete:need(seen==set(apps),'review route does not cover actual128')
 return {'kind':kind,'receipts':receipt_pairs,'keys':sorted(seen),'original_peer_rows':preserved,'scope':'complete128' if complete else 'static available subset; not full128 acceptance'}
def consume(request):
 need(request.get('schema')=='api-final61b-evidence-request/v1' and request.get('execution_enabled') is False,'disabled request required')
 authority=read(pin(request.get('authority')))
 need(authority.get('fixture',False) is False and authority.get('synthetic',False) is False,'fixture acceptance forbidden')
 need(str(authority.get('status','')).startswith('ACCEPT'),'actual scoped outer acceptance missing')
 need(authority.get('reviewer',authority.get('actual_reviewer'))=='outer(codex)','actual outer reviewer missing')
 need(authority.get('serial',authority.get('board'))==SERIAL and authority.get('boot_id')==BOOT,'outer board/boot differs')
 need(authority.get('candidate_runtime_sha256')==RUNTIME,'outer runtime differs')
 need(type(authority.get('canonical_keys')) is int and authority['canonical_keys']==128,'actual complete128 required')
 need(authority.get('driver_exited') is True,'outer actual driver-exit observation missing')
 need(authority.get('driver_exit_code') in (None,'unknown','UNKNOWN'),'original detached global rc was not captured')
 need(isinstance(authority.get('scope'),str) and 'startup' in authority['scope'].lower(),'startup-limited scope required')
 need(isinstance(authority.get('limitations'),list) and authority['limitations'] and all(isinstance(x,str) and x.strip() for x in authority['limitations']),'actual limitations required')
 apps,tiers=base();allkeys=set();records={};images=0
 refs=request.get('comparison');need(isinstance(refs,list) and refs,'missing original comparison')
 for ref in refs:
  keys,count,bykey=row_objects(actual_rows(read(pin(ref))),apps,tiers)
  need(not(allkeys&keys),'comparison duplicate canonical key');allkeys.update(keys);records.update(bykey);images+=count
 need(allkeys==set(apps) and images==256,'incomplete actual128/256 comparison')
 completion=detached_completion(records)
 facts=pin(request.get('facts'));total=validate_facts(facts.read_text(),tiers)
 routes=request.get('review_routes');need(isinstance(routes,list) and len(routes)==2 and len({r.get('name') for r in routes})==2,'two named original review routes required')
 kinds=[r.get('kind',r.get('name')) for r in routes]
 need(set(kinds)=={'bms','nativepeer'},'BMS observer and BMS closeout cannot count as two independent reviewers')
 checked=[review_route(r.get('receipts'),apps,tiers,records,kind=kind) for r,kind in zip(routes,kinds)]
 need(not({(r['path'],r['sha256']) for r in checked[0]['receipts']}&{(r['path'],r['sha256']) for r in checked[1]['receipts']}),'one receipt cannot impersonate two reviewers')
 evidence=[('实际outer同61b128受限接受；原限制保留，不是功能全可用',request['authority']),('原同61b128总facts；alive与失败原值保留',request['facts'])]
 evidence += [('原同61b逐key比较与256截图pins',r) for r in refs]
 evidence += [('原同61b独立逐key审定：'+route['name'],r) for route in routes for r in route['receipts']]
 unique={}
 for text,ref in evidence:
  portable='$WORKSPACES/'+resolve(ref['path']).relative_to(WS).as_posix()
  unique[portable]={'path':portable,'sha256':ref['sha256'],'supports':text}
 return {'authority':authority,'authority_pin':ref_pair(request['authority']),'keys':128,'screenshots':256,'tiers':{'10':121,'20':7},'facts_total':total,'evidence':list(unique.values()),'detached_completion':completion,'review_routes':checked,'device_calls':0}
