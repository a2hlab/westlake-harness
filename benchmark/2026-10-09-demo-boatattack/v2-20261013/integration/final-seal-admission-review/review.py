#!/usr/bin/env python3
"""Offline consumer and actual receipt cross-check only. No deployment or admission grant."""
import copy,hashlib,importlib.util,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file() and (p/'scripts/lab/lab_paths.py').is_file())
WS=Path(os.environ.get('WORKSPACES',str(ROOT.parent))).resolve();MAIN=WS/'westlake-harness'
B=Path('benchmark/2026-10-09-demo-boatattack/v2-20261013');RUN=MAIN/B/'outer/final61b-approved-execution';V1=MAIN/'benchmark/2026-10-12-v1-seal-execution'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return {'path':'$WORKSPACES/'+str(p.resolve().relative_to(WS)),'sha256':sha(p)}
def resolve(p,base=MAIN):return Path(p.replace('$WORKSPACES',str(WS))) if '$WORKSPACES' in p else (base/p).resolve()
def check_pin(p,base=MAIN):
 f=resolve(p['path'],base);assert f.is_file() and sha(f)==p['sha256'],p;return pin(f)
def save(n,o):(HERE/n).write_text(json.dumps(o,indent=2)+'\n')
consumer=MAIN/'benchmark/2026-10-09-demo-baseline/t5/build_seal.py'
spec=importlib.util.spec_from_file_location('original_build_seal',consumer);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
plan_path=RUN/'stage/plan.enabled.json';plan=load(plan_path);disabled=load(RUN/'boat/plan.disabled.json');delta=[k for k in set(plan)|set(disabled) if plan.get(k)!=disabled.get(k)];assert delta==['execution_enabled'],delta
ovpath=RUN/'boat/composed/overlays.pending.json';overlays=load(ovpath);tt,boat=[next(r for r in overlays['items'] if r['id']==key) for key in ['toutiao-route-b','boatattack']]
assert len(tt['files'])==487 and len(boat['files'])==18
boat_map={r['target']:r['sha256'] for r in boat['files']};plan_map={r['target']:r['sha256'] for r in plan['members']+plan['binds']};assert boat_map==plan_map and len(plan_map)==18
assert len(plan['members'])==11 and len(plan['binds'])==7
row=load(RUN/'stage/deployment.enabled.json')['providers'][0];assert set(row['targets'])==set(boat_map)
pins={k:check_pin(row[k]) for k in ('program','common','executor','prepared','authorization')}
txroot=RUN/'stage/boat/transaction';tx=load(txroot/'transaction.json');receipt=load(RUN/'stage/boat/receipt.json');assert tx['plan_sha256']==receipt['plan_sha256']==sha(plan_path) and receipt['executor_rc']==0 and receipt['status']=='PLACED_PENDING_AUTHORIZED_SINGLE_BOOT'
assert len(tx['backups'])==11 and [r['target'] for r in tx['backups']]==[r['target'] for r in plan['members']]
placed=[];backup=[]
for i,r in enumerate(plan['members']):
 p=txroot/('placed-%03d.json'%i);actual=load(p);assert actual['target']==r['target'] and actual['sha256']==r['sha256'];placed.append(pin(p))
 entry=tx['backups'][i];assert entry['before']==r['before'] and entry['candidate_sha256']==r['sha256']
 if entry['backup']:
  # Original executor writes the backup filename, rather than an arbitrary relocation.
  f=txroot/Path(entry['backup']).name;assert sha(f)==r['before']['sha256'];backup.append({'target':r['target'],'before':r['before'],'backup':pin(f)})
 else:assert r['before']['exists'] is False
pres=load(txroot/'preserved-verified.json');assert pres['success'] is True and pres['count']==496 and pres['plan_sha256']==sha(plan_path)
livepath=RUN/'stage/final-selfcheck954.json';live=load(livepath);assert live['status']=='PASS' and live['mode']=='live-readonly' and live['synthetic'] is False and live['file_count']==954 and len(live['checks'])==954
observed={r['target']:r['actual'] for r in live['checks']};assert all(r['equal'] and r['actual']==r['expected'] for r in live['checks'])
assert all(observed[p]==s for p,s in boat_map.items())
ttmap={r['target']:r['sha256'] for r in tt['files']};ttdrift=[{'target':p,'declared':s,'actual':observed[p]} for p,s in ttmap.items() if observed[p]!=s]
oldsource=V1/'seal-final-20261013/route-b-source.json';oldrollback=V1/'seal-final-inputs/rollback-index.61b.json';assert sha(oldsource)==tt['source']['sha256'] and sha(oldrollback)==tt['rollback']['sha256']
routeb_backups=[check_pin(row['backup']) for row in load(oldrollback)['backups']];assert len(routeb_backups)==24
capture=load(RUN/'postinstall-capture/capture.json')
for triplet in capture['boat_identity'].values():
 for reference in triplet.values():check_pin(reference)
assert capture['boat_uid']==plan['boat_uid']==20011207 and capture['boot_before']==capture['boot_after']==plan['boot_id']
oldrows={r['target']:r['sha256'] for r in load(oldsource)['files']};assert set(oldrows)==set(ttmap)
source_drift=[{'target':p,'historical':s,'observed':observed[p]} for p,s in oldrows.items() if observed[p]!=s]
negative=[]
for label,doc in [('actual_pending_admission',overlays),('old_source_mapper_v1_rows',load(WS/'westlake-harness-t0/benchmark/2026-10-14-final61b-seal-command-card/source-map.disabled/overlays.pending.json'))]:
 try:c.overlay_check(doc);result='UNEXPECTED_ACCEPT'
 except Exception as e:result=type(e).__name__+': '+str(e)
 negative.append({'input':label,'result':result})
# This unsigned field-source document is NOT actual admission. It proves the existing
# consumer only checks path/SHA syntax, so final approval must remain external.
admission={'schema':'boat-overlay-admission-field-sources/v1','admitted':False,'approved_by':None,'serial':plan['serial'],'origin_boot_id':plan['boot_id'],'current_boot_id':live['current_boot'],'source_candidate':pin(RUN/'boat/plan.disabled.json'),'executed_plan':pin(plan_path),'enable_only_delta':delta,'provider_pins':pins,'placement_receipt':pin(RUN/'stage/boat/receipt.json'),'transaction':pin(txroot/'transaction.json'),'placed_members':placed,'exact_existing_backups':backup,'preserved_496':pin(txroot/'preserved-verified.json'),'candidate_boot':pin(RUN/'stage/candidate-boot-result.json'),'actual954_pre_final':pin(livepath),'member_count':18,'placement_count':11,'bind_count':7,'expected_members':boat['files'],'boat_uid':plan['boat_uid'],'postinstall_capture':pin(RUN/'postinstall-capture/capture.json'),'preinstall_receipt':pin(RUN/'preinstall/preinstall-receipt.json'),'actual_bms_triplets':capture['boat_identity'],'pending':{'final_snapshot':None,'final_snapshot_complete_505_overlay_member_match':None,'same61b128_collect_and_review':None,'boat_original_plus_resume_image_review':None,'routeb_final_feed_review':None,'outer_admission':None},'claim':'Structural review only; not accepted, not sealed, no execution authority'}
save('boat-admission.field-sources.json',admission)
normalized=copy.deepcopy(overlays)
for r in normalized['items']:
 if r['id']=='toutiao-route-b':r['source']=pin(oldsource);r['rollback']=pin(oldrollback)
 else:r['admission']=pin(HERE/'boat-admission.field-sources.json');r['admission_status']='NOT_ADMITTED_OFFLINE_STRUCTURE_ONLY'
normalized['status']='OFFLINE_STRUCTURE_ONLY_NOT_ADMITTED';save('overlays.structure-only.json',normalized)
effective,packages=c.overlay_check(normalized);assert len(effective)==505 and set(packages)=={'org.westlake.imehost','com.Unity3d.BoatAttackDay'}
# Drop one real Boat target: overlay_check alone still accepts, reinforcing that
# exact actual final membership must be checked against all18 and capture.
incomplete=copy.deepcopy(normalized);next(r for r in incomplete['items'] if r['id']=='boatattack')['files'].pop();assert len(c.overlay_check(incomplete)[0])==504
report={'schema':'final-overlay-consumer-review/v1','status':'OFFLINE_FIELDS_REVIEWED_FINAL_ADMISSION_PENDING','device_calls':0,'consumer':pin(consumer),'actual_overlays':pin(ovpath),'expected_overlay_union':505,'boat18_equals_actual11plus7':True,'all11_placed_and_transaction_backups_verified':True,'enabled_plan_only_delta':delta,'actual954':pin(livepath),'routeb487_declared_vs_actual_drift':ttdrift,'routeb487_historical_source_vs_actual_drift':source_drift,'original_consumer_negative_checks':negative,'unsigned_structural_pin_accepted_by_consumer':True,'dropped_member_still_accepted_by_overlay_check':True,'consequence':'Final admission must enforce exact487+18 and evidence itself; original builder validates schema and snapshot equality, not the semantic truth of admission or member count. Do not alter builder or treat offline structural replay as live/admitted.','routeb_backup24_verified':routeb_backups,'routeb_source':pin(oldsource),'routeb_rollback':pin(oldrollback),'routeb_rollback_scope':{k:load(oldrollback)[k] for k in ['scope','runtime_stage_action','non_init_restored','init_quarantined','board_exercised']},'routeb_claim':'Preserved original61b487 plus fresh observations; not a newly executed487 restore.5cd rehearsal is separate evidence.','package_inventory':'130 expected: original128 + imehost HAP + Boat; embedded Toutiao is hashed within487 and is not a BMS package.'}
save('results.json',report)
print(json.dumps({'boat18':len(boat_map),'routeb487':len(ttmap),'overlay505':len(effective),'placed':len(placed),'backup_files':len(backup),'routeb_sha_drift':len(ttdrift),'source_sha_drift':len(source_drift),'negative':negative,'device_calls':0},indent=2))
