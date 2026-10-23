#!/usr/bin/env python3
"""Extract only approved ordinary stage/time fields; never copy private raw log."""
from pathlib import Path
import argparse,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path.home()/'.local/share/westlake/success-startup-log-20261023');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
raw=(a.input/'head.stdout').read_bytes();lines=raw.decode().splitlines();receipt=json.loads((a.input/'head.json').read_text());outer=json.loads((a.input/'results.json').read_text())
sha=hashlib.sha256(raw).hexdigest()
assert sha==outer['head_sha256']=='3eabb43dff55b5f6ca31569a25131ba7f8474487f9daf29c5c21f4621407202d'
assert len(raw)==21154 and len(lines)==300 and receipt['rc']==0
assert lines[0]=='[AppSpawnX] [CHILD] native stderr redirected to /data/service/el1/public/appspawnx/adapter_child_6291.stderr'
assert (a.input/'boot.stdout').read_text().strip()=='61aa5791-fd69-4bbb-a7b5-333b5d913c81'
# Select harmless exact stage text only. Untimed lines stay explicitly untimed.
selected=[(31,'post-fork initialization complete'),(82,'JNI registration complete'),(150,'startReg return'),(151,'child registration rc'),(160,'adapter initialization complete'),(186,'Java adapter initialization checkpoint'),(195,'activity-manager install checkpoint'),(201,'window-manager install checkpoint'),(206,'input-manager install checkpoint'),(216,'service-manager install checkpoint'),(239,'settings initialization checkpoint'),(242,'adapters installed'),(243,'target application armed'),(244,'ActivityThread main invocation before'),(249,'main invocation before'),(256,'direct launch started'),(262,'package parse metadata'),(264,'ApplicationInfo built'),(265,'ensureBindApplication entry'),(279,'providers populated'),(280,'compat configuration'),(281,'AppBindData constructed'),(284,'archive missing .dm message'),(289,'archive classes22.dex absent message'),(300,'archive scan result')]
stages=[]
for num,label in selected:
 text=lines[num-1]
 assert not re.search(r'token|password|credential|https?://|cookie|ssid',text,re.I)
 stages.append({'line':num,'stage':label,'excerpt':text,'timestamp':None,'duration':None,'identity':'same supplied ordinary-log fragment; no explicit per-line PID/boot'})
# Timestamp anchor: expose prefix fields only, not session metadata or other payload.
anchors=[]
for i,l in enumerate(lines,1):
 m=re.match(r'nullptr\s+\w\s+(\d\d-\d\d)\s+(\d\d:\d\d:\d\d)\s+(\d+)\s+(\d+)\s+',l)
 if m:anchors.append({'line':i,'month_day':m[1],'wall_time':m[2],'pid':int(m[3]),'tid':int(m[4]),'precision':'one second','message_omitted':True})
counters=[]
for i,l in enumerate(lines,1):
 if l.startswith(('[TOUCH21-POLL]','[TOUCH21-WAKE]')):
  m=re.search(r'now=(\d+) tid=(\d+)',l)
  if m:counters.append({'line':i,'event':l.split('now=')[0].strip(),'now_raw':int(m[1]),'tid':int(m[2]),'unit':'unknown','clock_domain':'unknown','pointer_fields_omitted':True})
result={'task':'T93 successful startup prefix','status':'UNKNOWN_NO_TIMED_OPTIMIZATION','executor':'outer collected four read-only receipts; Codex only offline extraction','input_sha256':sha,'bytes':len(raw),'lines':len(lines),'collection_rc':receipt['rc'],'collector_validation':'Expected prefix, SHA, rc and bounds independently checked. Empty transport stderr validation is attributed to outer; no extra receipt/path fetched. Application No such file text is not transport failure.','boot':(a.input/'boot.stdout').read_text().strip(),'identity_limit':'Collection boot and explicit PID6291 at10-23 17:22:00 corroborate the T87 launch; log lines do not carry birth142694 or boot IDs. Filename/mtime alone are not used as identity proof.','wall_clock_pid_anchors':anchors,'raw_time_counters':counters,'untimed_stage_sequence':stages,'trace_comparison':{'accepted_T92_first_marker':{'uptime':1461.881765,'pid':6291,'tid':6311,'line':2229,'operation':'content::Start'},'wall_anchor_approx_relation':'T92 accepted clock mapping places first marker near17:22:35.31. The17:22:00 PID anchor precedes it by about35s at second-level precision; this is not a measured startup-operation duration.','now_counter_delta_to_trace':None,'limit':'Counter unit/domain unbound. No timestamps bound the adapter/Java/bindApplication stages, and this prefix does not span the whole interval to feed.'},'file_metadata_limit':'stat mtime19:09:08 is later collection-era modification, not startup stage time; atime17:22:00 is not a creation timestamp.','optimization_candidate':None,'one_gap':'No clock-bound start/end pair for the ordinary startup stages between the17:22:00 anchor and first child trace marker. The300-line prefix ends during APK archive scanning, so no phase receives a fabricated duration.','privacy':'Raw prefix remains private. Only allowlisted non-sensitive stage excerpts and timestamp fields are exported; tokens/session IDs/network data are omitted.','actions':{'device_calls':0,'source_reads':0,'deployments':0,'T91_actions':0}}
a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sha256':sha,'anchors':len(anchors),'raw_counters':len(counters),'untimed_stages':len(stages),'status':result['status']}))
