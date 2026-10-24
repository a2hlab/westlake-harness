#!/usr/bin/env python3
"""Offline bounded ordinary evidence index; no device/source/controller access."""
from pathlib import Path
import hashlib,json,re
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[2];WS=REPO.parent
H=Path.home()/'.local/share/westlake';V=WS/'westlake-harness-video/benchmark';M=WS/'westlake-harness'
refs=[]
def ref(p,lines,claim):
 raw=p.read_bytes();n=len(raw.splitlines());assert all(0<i<=n for i in lines)
 s=str(p)
 for root,alias in [(H,'$HOME/.local/share/westlake'),(V,'$VIDEO/benchmark'),(M,'$MAIN')]:
  if p.is_relative_to(root):s=alias+'/'+str(p.relative_to(root));break
 x={'path':s,'lines':lines,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'claim':claim};refs.append(x);return len(refs)
def locate(p,needle):return [i for i,l in enumerate(p.read_text().splitlines(),1) if needle in l]
case={}
for task,topic in [('T103','spare-board-icon-observation'),('T104','complete-desktop-launch'),('T108','spare-board-boot-entry'),('T109','spare-board-reboot-repeat'),('T112','after-reboot-icon-recovery')]:
 pub=V/('2026-10-23-'+topic);r=pub/'run'/ (task.lower()+'-5cd')/'record.json';rd=json.loads(r.read_text());rr=ref(r,locate(r,'"status"'),'Recorded outcome and screenshot capture entries; visual classification reused from accepted review, not newly inferred from hashes')
 p=pub/'results.json';d=json.loads(p.read_text());pr=ref(p,locate(p,'"verdict"'),'Collector summary; subordinate to original raw/record')
 case[task]={'record_ref':rr,'summary_ref':pr,'record_status':rd.get('status'),'role':'NO_TAP_NOT_SUCCESS' if task=='T103' else 'success_control' if task in ['T104','T108'] else 'failure','identity':{'boot':d.get('boot',d.get('reboot',{}).get('new_boot',d.get('precheck_20_14_37',{}).get('boot')))}}
 if task in ['T108','T109']:
  root=H/(topic+'-20261023');case[task]['raw_refs']={}
  for t in [10,30,60,90,120]:
   p=root/f'raw/05/p{t}.stdout';case[task]['raw_refs'][str(t)]=ref(p,list(range(1,len(p.read_text().splitlines())+1)),'Ordinary ps/WMS sample; sampled PID/focus, not exact process creation or continuous coverage')
  for n in ['click.argv','click.rc','click.start','click.end']:
   p=root/'raw/05'/n;ref(p,[1],'Single ordinary click command receipt; host clock not calibrated against device wall clock')
 if task=='T112':
  root=H/(topic+'-20261023')
  for t in [5,10,20,40,60,90]:
   p=root/f'raw/03/p{t}.stdout';ref(p,list(range(1,len(p.read_text().splitlines())+1)),'Sampled host5074 and appspawn5201; no article child at these samples, not continuous absence proof')
  for n in ['click.argv','click.rc','click.start','click.end']:ref(root/'raw/03'/n,[1],'T112 single ordinary click receipt')
p=H/'host-lifecycle-after-retry-limit-20261023/raw/hilog.stdout'
ref(p,[196],'T109 initial host5074 foreground at device wallclock22:41:56.696')
ref(p,[901,904,917],'T112 interval host5074 foreground22:48:56.912 and stage-event1/2; no exact cross-machine click latency claim')
p=H/'host-lifecycle-after-retry-limit-20261023/index.json';ref(p,locate(p,'"boot_pre"')+locate(p,'"birth_pre"')+locate(p,'"host_pid"')+locate(p,'"birth_post"'),'T114 collection bound to bootecb84d86, host5074 birth9930 before/after')
failures={}
for pid,lines,size,end in [('7011',[87,199,211,423,1184,1193],368251,1596),('9860',[87,199,211,426,708,759],314796,1518)]:
 p=H/f'spare-board-reboot-repeat-20261023/raw/06/log{pid}.stdout';r=ref(p,[1,4,6,*lines,end-2,end],'Sameboot collector/stat plus explicit JNI completion, Application-ready, feature-published and scheduleTransaction OK; prefix endpoint truncated')
 failures[pid]={'ref':r,'source_bytes':size,'captured_payload_bytes':131072,'uncaptured_bytes':size-131072,'identity':'bootecb84d86 + contemporaneous ps PID/PPID/UID + filename/log PID and stable stat inode/size/mtime; child birth ticks not captured','stage':'scheduleTransaction dispatched; Activity completion/first frame not established'}
 p=H/f'spare-board-reboot-repeat-20261023/raw/06/log{pid}.argv';ref(p,[1],'Collector command binds exact ordinary adapter_child stderr path and bounded head, not whole file')
# Metadata-only inventory of named task archives, excluding all tool/source trees.
inventory=[]
for task,topic in [('T103','spare-board-icon-observation'),('T104','complete-desktop-launch'),('T108','spare-board-boot-entry'),('T109','spare-board-reboot-repeat'),('T112','after-reboot-icon-recovery'),('T114','host-lifecycle-after-retry-limit')]:
 for root,alias in [(H/(topic+'-20261023')/'raw','$HOME/.local/share/westlake/'+topic+'-20261023/raw'),(V/('2026-10-23-'+topic)/'raw','$VIDEO/benchmark/2026-10-23-'+topic+'/raw')]:
  candidates=[]
  if root.exists():
   for p in root.rglob('*'):
    if p.is_file() and re.search(r'(log\d+|tail|head|hilog|startup|adapter_child)',p.name,re.I) and p.suffix in ['.stdout','.log','.txt']:
     candidates.append({'path':alias+'/'+str(p.relative_to(root)),'bytes':p.stat().st_size})
  inventory.append({'task':task,'root':alias,'exists':root.exists(),'ordinary_named_candidates':candidates})
d={'task':'T113-R2','ack':'partially/unverified','status':'NO_CAUSAL_API_CANDIDATE','sample_correction':'T103 has no click and no startup baseline; success controls are T104/T108. T114 is a later ordinary host-log collection, not another launch.','cases':case,'earliest_proven_boundary':{'reboot_first_launch':'T108 andT109 both host at t10 and child at t30. By t60 success retains7111/feed while failure shows9860/white after7011 at t30. Divergence demonstrated at child/visible-content stage by sampled t60, not precise onset or root cause.','same_boot_reopen':'T112/T114 host foreground and stage callbacks present, but no new child in subsequent samples. Request emission/acceptance remains unobserved; do not infer missing foreground or exact request failure.','not_same_stage':'T112 is an existing host after previous unsuccessful attempts, unlike first launch T108/T109; lack of success host lifecycle logs prevents callback-level matched comparison.'},'failure_prefixes':failures,'tail_inventory':inventory,'coverage':'No additional named ordinary startup tails found within these existing task raw directories. This is bounded inventory, not proof of global archive absence. SuccessT104/T108 have screenshots/ps, not matched full child startup logs in this inventory. T95 success6291 is a different board/run and only secondary shared-stage context; do not substitute it for7111/21639 logs.','excluded_claims':['T103 success baseline rejected','T109/T112 click never reached host contradicted by positive host foreground records','Failure before all Java/Application initialization contradicted by explicit successful stage markers in both failed-child prefixes','Shared warnings alone do not establish the cause; they do not rule out timing/state interactions or unseen tail errors','Focus/window reuse is not PID identity; sampled ps is not exact birth/exit timing'],'filter_limit':'Original compare.py normalized-unmatched screening excludes broad connect/ssl/cert/errno keywords (outer clarification). Empty result means no hit inside retained filter categories, not that all ordinary network/API errors were examined. No repeat of this screening or old warning/clock analysis.','remaining_gap':'Matched success/failure ordinary child log coverage from scheduleTransaction dispatch through Activity completion/first content frame is missing; host foreground-to-request also lacks direct request evidence.','next_minimal_observation':{'object':['/data/service/el1/public/appspawnx/adapter_child_7011.stderr bytes131072..368250','/data/service/el1/public/appspawnx/adapter_child_9860.stderr bytes131072..314795'],'binding':'T122 separately collecting each <=512KiB with old-prefix equality plus boot/stat/inode/mtime identity; only after outer validates, compare newly obtained suffix ordinary API/class/service/initialization failures.','current_action':'Do not wait for or consume T122 here. No new device collection is requested by this review.','cannot_prove':'Even complete failure tails alone will not provide matched successful7111 startup or a direct request marker.'},'evidence':refs,'actions':{'device':0,'REA':0,'source_implementation_reads':0,'stopped_objects_or_executor_reads':0,'old_warning_rescreen':0,'clock_reanalysis':0,'candidate_changes':0}}
(OUT/'results.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':d['status'],'ack':d['ack'],'refs':len(refs),'uncaptured_bytes':{k:v['uncaptured_bytes'] for k,v in failures.items()}},ensure_ascii=False))
