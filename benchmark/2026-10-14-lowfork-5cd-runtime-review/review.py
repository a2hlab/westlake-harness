from pathlib import Path
import json,re,hashlib,collections,datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
RUN=ROOT/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/metadata-lowfork-5cd-20261014T011836'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
plan=read(RUN/'plan.enabled.json');auth=read(RUN/'authorization.json');result=read(RUN/'compare/result.json')
assert result['status'] in ['METADATA_AB_PASS_ONLY','FAILED_READONLY_EVIDENCE_RETAINED']
assert plan['serial']=='5cd1e3dd00000000000000000923012c' and plan['boot_id']=='c9436daa-b3ca-44dc-985f-9ee03445567a'
assert auth['plan_sha256']==sha(RUN/'plan.enabled.json') and (RUN/'authorization.sha256').read_text().strip()==sha(RUN/'authorization.json')
assert result['status']=='METADATA_AB_PASS_ONLY', result
expected={**plan['files'],**plan['directories']};phases={};raw_pins=[]
def body(p):
 b=p.read_bytes();m=re.search(rb'\n__BOAT_PRESENCE_RC_[0-9a-f]+__0\s*$',b);assert m,p
 stderr=p.with_name(p.name.replace('.stdout.txt','.stderr.txt'));assert stderr.read_bytes()==b'',stderr
 raw_pins.extend([{'path':str(q.relative_to(RUN)),'sha256':sha(q),'bytes':q.stat().st_size} for q in [p,stderr]])
 return b[:m.start()].strip().decode()
for phase in ['original','candidate']:
 p=RUN/'compare'/phase;calls=read(p/'calls.json');metadata=[x for x in calls if x['name']=='metadata'];assert len(calls)==27 and len(metadata)==23
 allrows={};bodies=[]
 for q in sorted(p.glob('presence-*-metadata.stdout.txt')):
  t=body(q);bodies.append(t)
  for line in t.splitlines():
   target,mode,uid,gid,label=line.split('|');assert target not in allrows
   allrows[target]={'mode':mode,'uid':int(uid),'gid':int(gid),'label':label}
 assert allrows==expected and len(allrows)==512
 for when in ['before','after']:
  boot=next(p.glob('presence-*-boot-'+when+'.stdout.txt'));assert body(boot)==plan['boot_id']
  shafile=next(p.glob('presence-*-sha-'+when+'.stdout.txt'));rows={}
  for line in body(shafile).splitlines():
   h,target=line.split();assert target not in rows;rows[target]=h
  assert rows==plan['candidate_sha256'] and len(rows)==18
  held=read(RUN/'compare'/(phase+'-'+when+'-held.json'));assert held['rc']==0 and not held['stderr'] and held['stdout'].strip()==auth['holder']
 timing=next(x for x in result['phases'] if x['name']==phase)
 measured=sum(x['seconds'] for x in metadata)
 assert 0<=timing['metadata_seconds']-measured<1
 phases[phase]={'bodies':bodies,'metadata_seconds':timing['metadata_seconds'],'call_seconds_sum':measured,'per_call_min':min(x['seconds'] for x in metadata),'per_call_max':max(x['seconds'] for x in metadata),'calls':27,'metadata_batches':23,'objects':512,'bookend_reads':4,'expected_match':True}
assert phases['original']['bodies']==phases['candidate']['bodies']
for v in phases.values():v.pop('bodies')
a=phases['original']['metadata_seconds'];b=phases['candidate']['metadata_seconds']
report={'status':'INDEPENDENT_METADATA_AB_PASS_ONLY','at':datetime.datetime.now().astimezone().isoformat(),'serial':plan['serial'],'boot_id':plan['boot_id'],'source_result_sha256':sha(RUN/'compare/result.json'),'phases':phases,'metadata_speed_ratio':a/b,'metadata_seconds_saved':a-b,'metadata_time_reduction_percent':100*(a-b)/a,'raw_receipts':len(raw_pins),'source_pins':{'plan':sha(RUN/'plan.enabled.json'),'authorization':sha(RUN/'authorization.json'),'original_helper':plan['pins']['original']['sha256'],'candidate_helper':plan['pins']['candidate']['sha256']},'scope':'One old-then-new5cd run; only metadata timing excludes bookends/holder. Cache/order/load confounded; not full954/full128 validation or authorization to replace current61b pins.','device_calls_by_reviewer':0,'archive_pending_closed_directory':True}
(OUT/'raw-receipt-pins.json').write_text(json.dumps(raw_pins,indent=2)+'\n');(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','phases','metadata_speed_ratio','metadata_seconds_saved','metadata_time_reduction_percent']},indent=2))
