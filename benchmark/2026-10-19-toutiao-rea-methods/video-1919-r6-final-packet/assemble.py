#!/usr/bin/env python3
"""Offline assembly of the closed r6 window, not an execution tool."""
from pathlib import Path
import json,hashlib,shutil,subprocess,tempfile,csv,io,re
from html.parser import HTMLParser
F=Path(__file__).resolve().parent
R=next(p for p in F.parents if (p/'scripts/lab/run_facts.py').is_file())
M=R.parent/'westlake-harness';S=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
B=Path('benchmark/2026-10-19-toutiao-rea-methods');P=R/B/'video-1919-r6-live-review';A=Path('benchmark/2026-10-19-api-progress-update')
assert not (F/'freeze.json').exists(),'frozen packet'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(a.read_bytes())
close=read(S/'video-r6-window-close.json');arc=read(S/'video-r6-window-archive/receipt.json')
assert arc['archive_sha256']=='916ffbe526fc3c289afdef4ddc73abc1ed2f27efed8d7ceb1da79021dafc14ff' and arc['bytes']==10214049 and arc['remote_verified']
public=dict(arc);public['remote']='$HW248_ARTIFACT_ROOT/toutiao-video-r6-20261019/window.tar.gz';public['private_receipt_sha256']=h(S/'video-r6-window-archive/receipt.json');public['path_alias_only_no_raw_rewrite']=True
write(P/'archive/window-archive.json',public);copy(S/'video-r6-window-close.json',P/'archive/window-close.json')
board=(M/'.octos/boards/app-lighting.md').read_text(errors='replace');assert close['unlock_line'] in board
lock=next(l for l in board.splitlines() if l.startswith('LOCK(61b0657200000000000000000324012c)') and '2026-10-19T21:34:50' in l)
(F/'canonical-lock-excerpt.txt').write_text(lock+'\n'+close['unlock_line']+'\n')
copy(M/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r5/retry-r6/admission.json',P/'admission.original.json')
# Screenshot bytes remain exact; derived records use local names and pin originals.
selected=[('video-r6-identity/candidate-before-tap','candidate-feed','Actual news feed before video tap.'),('video-r6-play1','play1','t5/t20/t25 identical cover, NOT_PASSED; audio unknown.'),('video-r6-rollback-live/first-icon','restored-first-icon','IMEhost, not feed; later guardian records child7578 exited.'),('video-r6-rollback-live/second-icon','restored-second-icon','IMEhost at capture; not successful feed yet.'),('video-r6-rollback-live/second-feed','restored-second-feed','IMEhost at this capture; guardian helper read wrong r1 root.'),('video-r6-rollback-identity/baseline-final','restored-baseline-check','IMEhost at this capture; original byte and inode checks only.'),('video-r6-rollback-live/final-feed','restored-feed','Actual feed independently viewed; helper guardian reads wrong r1 root, corrected by separate r2 original.'),('video-r6-rollback-identity/final-guardian','restored-r2-guardian','Explicit r2 identity/READY/process supplemental original; no first-launch stability claim.')]
for srcname,dstname,verdict in selected:
 src=S/srcname;dst=P/dstname;rec=read(src/'record.json')
 for shot in rec['screenshots']:
  image=src/Path(shot['path']).name;assert h(image)==shot['sha256'];copy(image,dst/image.name);shot['path']=image.name
 rec['source_record_sha256']=h(src/'record.json');rec['independent_visual_review']=verdict
 write(dst/'record.json',rec)
 for n in ['guardian-before.txt','guardian-after.txt']:
  if (src/n).exists():copy(src/n,dst/n)
for src,dst in [('video-r6-identity/candidate-before-tap/step-0.txt','candidate-feed/identity.original.txt'),('video-r6-rollback-identity/baseline-final/step-0.txt','restored-baseline-check/identity.original.txt'),('video-r6-rollback-identity/final-guardian/step-0.txt','restored-r2-guardian/identity.original.txt')]:copy(S/src,P/dst)
assert h(P/'restored-feed/screen.jpeg')==close['feed_sha256']
guard=(P/'restored-r2-guardian/identity.original.txt').read_text();assert 'child=15451' in guard and 'birth=105141' in guard and 'parent_birth=6804' in guard and '\nREADY\n' in guard
assert re.search(r'^\s*15451\s+4991\s+20011206\s',guard,re.M)
orig=(P/'restored-baseline-check/identity.original.txt').read_text()
for val in ['d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4','fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9','b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02']:assert orig.count(val)==2
assert 'errNum is:106!' in orig
# Raw action and focused command receipts, with no personal-path normalization of originals.
for mode in ['apply','rollback']:
 for n in ['plan.json','result.json','swap.sh']:copy(S/('video-r6-'+mode)/n,P/mode/n)
assert read(P/'rollback/plan.json')['origin_apply_plan_sha256']==h(P/'apply/plan.json')
for srcname,dst in [('video-r6-log-enabled','parameter-enabled'),('video-r6-param-restored','parameter-restored')]:
 for n in ['result.json','param-before.txt','param-after.txt']:
  if (S/srcname/n).exists():copy(S/srcname/n,P/dst/n)
for srcname,dst in [('video-r6-reboot','candidate-reboot'),('video-r6-ready','candidate-ready'),('video-r6-rollback-reboot','rollback-reboot'),('video-r6-rollback-ready','rollback-ready')]:
 for n in ['result.json','ready.json']:
  if (S/srcname/n).exists():copy(S/srcname/n,P/dst/n)
# Select real remote shell receipts: swap, parameter, explicit r2 guardian and exact baseline checks.
for srcname,dst in [('video-r6-apply','apply'),('video-r6-rollback','rollback'),('video-r6-log-enabled','parameter-enabled'),('video-r6-param-restored','parameter-restored'),('video-r6-rollback-identity/final-guardian','restored-r2-guardian'),('video-r6-rollback-identity/baseline-final','restored-baseline-check')]:
 for f in sorted((S/srcname/'commands').glob('*.json')):
  d=read(f);argv=' '.join(d.get('argv',[]));body=f.read_text()
  select=('shell' in d.get('argv',[]) and (('swap' in argv and 'sh ' in argv) or 'param get debug.ttplayer.log.enable;' in argv or 'param set debug.ttplayer.log.enable true' in argv or ('icon-manual-20261019-r2' in argv and ('stat' in argv or 'instance.txt' in argv))))
  if select and '/Users/' not in body and '/home/' not in body:
   assert d['exit_code']==0
   for q in f.parent.glob(f.stem+'.*'):copy(q,P/dst/'commands'/q.name)
# Close identity and logger coverage on actual before/after captures; no big raw logs public.
for phase in ['before','after-play1']:
 src=S/('video-r6-native-'+phase);dst=P/('native-'+phase)
 for n in ['identity.json','before-child.stat','after-child.stat','before-parent.stat','after-parent.stat','parameter.txt']:copy(src/n,dst/n)
 for f in sorted((src/'commands').glob('*.json')):
  d=read(f);argv=' '.join(d.get('argv',[]))
  if 'hilog -x -P 7085 -L D,I,W,E,F -v monotonic' in argv:
   write(dst/'hilog-invocation.json',{'argv':d['argv'],'exit_code':d['exit_code'],'original_receipt_sha256':h(f),'stdout_sha256':h(f.with_suffix('.stdout.txt')),'stderr_sha256':h(f.with_suffix('.stderr.txt'))})
lines=(S/'video-r6-native-after-play1/child.stderr').read_text(errors='replace').splitlines();line=lines[176134];assert line=='[WESTLAKE-WEBVIEW-BIONIC] property debug.ttplayer.log.enable=true'
(P/'native-after-play1/property-consumer.original-excerpt.txt').write_text(line+'\n')
write(P/'native-after-play1/excerpt-provenance.json',{'raw_path':'$HOME/.local/share/westlake/toutiao-resume-20261019/video-r6-native-after-play1/child.stderr','raw_sha256':h(S/'video-r6-native-after-play1/child.stderr'),'line':176135,'excerpt_exact_line':True,'attribution':'Actual child property read. Nearby player load messages and static JNI_OnLoad path are supporting context; no return-PC/call stack proves this individual caller.'})
copy(S/'video-r6-play1/got.json',P/'play1/got.original.json')
# Snapshot comparison is mechanical and does not equate runtime candidate bytes with baseline.
a=read(S/'video-r6-state-before/snapshot.json');z=read(S/'video-r6-state-restored/snapshot.json')
for x in [a,z]:assert x['capture_status']=='COMPLETE' and x['boot_stable'] and x['complete'] and not x['errors']
for k in ['plan_sha256','collection_sha256','labels','init_configs','selinux_enforce']:assert a[k]==z[k],k
write(P/'snapshot-review.json',{'snapshots':2,'targets_each':62,'labels_each':len(z['labels']),'same_plan':a['plan_sha256'],'same_collection_sha256':a['collection_sha256'],'labels_configs_selinux_equal':True,'before_sha256':h(S/'video-r6-state-before/snapshot.json'),'restored_sha256':h(S/'video-r6-state-restored/snapshot.json')})
# Exact one-off scripts, no new generic execution framework.
for n in ['video_guarded_window_r6.py','video_r5_control.py','board_step.py','live_tools.py','wait_boot_ready.py']:
 src=S/n;assert '/Users/' not in src.read_text() and '/home/' not in src.read_text();copy(src,P/'historical-recipes'/n)
assert h(P/'historical-recipes/video_guarded_window_r6.py')=='b8e9c4b2296bebf91f2364e272f6047cfc494e7f70e719688b73fd0ae695a531'
# Pin every archived original; exact remote location stays private, public alias only.
pins=[]
for member in arc['members']:
 src=S/member
 for f in ([src] if src.is_file() else sorted(x for x in src.rglob('*') if x.is_file())):pins.append({'path':'$HOME/.local/share/westlake/toutiao-resume-20261019/'+str(f.relative_to(S)),'sha256':h(f),'bytes':f.stat().st_size})
write(P/'source-pins.json',{'private_persistent_root':'$HOME/.local/share/westlake/toutiao-resume-20261019','archive_receipt':'archive/window-archive.json','files':pins,'archive_recipe_original_in_archive':True,'not_all_originals_are_public':True})
results={'token':'video-1919-r6-final-packet','status':'CLOSED_STATIC_COVER_RESTORED','candidate_boot':close['candidate_boot'],'candidate_parent':'5130/9571','candidate_child':'7085/11201','playback':'NOT_PASSED_STATIC_COVER','audio':'UNKNOWN','native_property_read':'OBSERVED_TRUE_BRIDGE_LOG_LINE176135','exact_JNI_OnLoad_callsite':'CONSISTENT_WITH_STATIC_PATH_NOT_RUNTIME_STACK_PROVEN','setDataSource_prepare_error':'NOT_OBSERVED_IN_REVIEWED_LOG_TEXT; absence is not proof of non-execution','java_logging_enabled':'UNKNOWN','got_status':'original unknown retained','restored_boot':close['restored_boot'],'restored_parent':'4991/6804','restored_child':'15451/105141 seq2','restored_feed_sha256':close['feed_sha256'],'restored_feed':'INDEPENDENTLY_VISUALLY_CONFIRMED','original_bytes_private_inode_compat_absence_cfg_parameter106':'VERIFIED','parent_maps_unmapped':'NOT_IN_BASELINE_FINAL_COMMAND; no additional claim','preserved_errors':close['preserved_errors'],'snapshots':'same-plan 62 targets/351 labels; collection SHA, labels, init configs, SELinux equal','unlock':close['unlock_line'],'window_seconds':1746,'archive_sha256':arc['archive_sha256'],'archive_bytes':arc['bytes'],'archive_remote_verified':True,'device_calls_by_reviewer':0,'new_builds':0,'API_historical315_changed':False}
write(P/'results.json',results)
(P/'README.md').write_text('''# R6 native-log observation: static cover, restored\n\nThe approved r4 four-file tuple was reused, with the single temporary true parameter. Candidate child7085/b11201 and parent5130/b9571 remained identical across the before/after collections. A real feed preceded one video tap. The three t5/t20/t25 images are byte-identical covers (actual capture completion about6.71/21.77/26.81seconds after tap): no dynamic playback or audio success is established. P1 remains NOT_PASSED.\n\nChild stderr line176135 actually reads `debug.ttplayer.log.enable=true` through the bridge. This exceeds shell set/get evidence and is consistent with the known JNI_OnLoad path, but that line lacks a runtime caller stack/return-PC. No exact setDataSource/prepareAsync text appeared in the reviewed full stderr and explicit all-level same-PID hilog; this does not prove non-execution or enabled Java logs. Original GOT unknown is retained. No random-crash cause was investigated.\n\nRollback binds the original new apply-plan and restores run/media/player SHA and physical/private inode identity; compat absent, cfg91e31 and freshboot parameter106 are checked. Both same-plan snapshots are COMPLETE with62targets/351labels and equal collectionSHA/labels/initconfigs/SELinux. Restored boot66dbabb7 first child7578 exited; second real icon eventually produced child15451/b105141, parent4991/b6804, seq2 READY and the independently viewed final feed. No stable first-launch claim. Parent maps were not part of baseline-final's command, so no new unmapped claim is made.\n\nTwo capture helpers mistakenly read the old r1 guardian root. Their original errors remain under restored-second-feed and restored-feed. Explicit restored-r2-guardian is the separate corrective original; errors were not rewritten. Canonical UNLOCK22:03:56 closes29m06s. Raw archive916ffbe5 is remotely size/SHA verified; exact private destination is replaced only in the public receipt by HW248_ARTIFACT_ROOT. Big stderr/hilog and original command logs remain in that archive; source-pins.json records each original. Screenshot bytes are original; local record paths are portable derivatives with original record hashes.\n\nHistorical recipes are exact one-off sources, not safe blind rerun tools. Earlier checkpoint JSONs/README.draft record intermediate states; results.json is the final scope. The separate final-packet assembler preserves the offline review recipe. facts.txt is the sole screenshot/alive count authority; standard alive-table gaps remain unknown. API adds only observation6, preserving the previous five objects and historical315.\n''')
proc=subprocess.run(['python3',str(M/'scripts/lab/run_facts.py'),str(P)],capture_output=True,text=True);assert proc.returncode==0
(P/'facts.txt').write_text(proc.stdout);(P/'facts.stderr.txt').write_text(proc.stderr);write(P/'facts-command.json',{'argv':['python3','$MAIN/scripts/lab/run_facts.py',str(P.relative_to(R))],'rc':proc.returncode,'tool_sha256':h(M/'scripts/lab/run_facts.py')})
# Add one row, using original MAIN renderer and MAIN inputs for all prior refs.
base=read(M/A/'observations.json');assert len(base['rows'])==5;new=json.loads(json.dumps(base));new['as_of']='2026-10-19T22:03:56+08:00'
def ref(path):
 q=R/path if path.startswith(str(P.relative_to(R))) else M/path
 return {'path':path,'sha256':h(q)}
row={'id':'OBS-20261019-PLAYER-R6','kind':'既有候选补充日志观察（非新增公共API）','name':'TTPlayer参数实际读取与静止封面观察','status':'真实桥接读true；静止封面，P1未通过；已回滚恢复feed','method':'复用r4四件与临时单键true，无新构建；同PID/birth采tap前后stderr及显式-L D,I,W,E,F hilog。','platform':'61b/arm64，candidate bootdf563b46；本条不新增平台版本证明。','apps':'今日头条child7085/11201首启feed后实际tap600,1540；t5/t20/t25同SHA封面，采集前后child与parent身份一致。','limitations':'桥接读true不等于精确JNI_OnLoad调用栈已证；未见setDataSource/prepareAsync日志不等于未执行，Java日志启用unknown。声音unknown，非两轮有声播放；原GOT unknown保留。恢复首child自然退出；不承诺稳定首启。','deployment':'四件按本轮原apply-plan回滚，原SHA/private inode、compat absent、cfg91e31、freshboot66dbabb7参数106及同plan快照已核；第2图标child15451/105141最终真实feed，22:03:56解锁。误读r1的helper错误保留，由显式r2补证。','source':[ref(str(P.relative_to(R)/'historical-recipes/video_guarded_window_r6.py')),ref(str(B/'video-1919-r5-param-recovery/source-final.json')),ref(str(B/'video-1919-r5-param-recovery/provider-final.json'))],'build':[ref(str(B/'video-1919-r4-live-review/archive/build-artifacts-receipt.json'))],'evidence':[ref(str(P.relative_to(R)/x)) for x in ['results.json','admission.original.json','native-after-play1/property-consumer.original-excerpt.txt','native-after-play1/excerpt-provenance.json','native-after-play1/identity.json','after-play-checkpoint.json','play1/record.json','play1/t20.jpeg','restored-feed/screen.jpeg','restored-feed/guardian-after.txt','restored-r2-guardian/identity.original.txt','restored-baseline-check/identity.original.txt','parameter-restored/param-before.txt','snapshot-review.json','archive/window-close.json','archive/window-archive.json']],'frozen':False}
new['rows'].append(row);write(F/'api-row6.json',row)
with tempfile.TemporaryDirectory(prefix='r6-render-') as td:
 root=Path(td);dst=root/A;dst.mkdir(parents=True);copy(M/A/'render.py',dst/'render.py');write(dst/'observations.json',new)
 for rr in new['rows']:
  for group in ['source','build','evidence']:
   for item in rr[group]:
    rel=item['path'];src=R/rel if rel.startswith(str(P.relative_to(R))) else M/rel;assert h(src)==item['sha256'];copy(src,root/rel)
 copy(M/'benchmark/2026-10-14-api-source-delivery/views/index.html',root/'benchmark/2026-10-14-api-source-delivery/views/index.html')
 run=subprocess.run(['python3',str(dst/'render.py')],capture_output=True,text=True);(F/'renderer.stdout.txt').write_text(run.stdout);(F/'renderer.stderr.txt').write_text(run.stderr);assert run.returncode==0,run.stderr
 class Links(HTMLParser):
  def __init__(self):super().__init__();self.links=[]
  def handle_starttag(self,t,a):
   if t=='a':self.links.extend(v for k,v in a if k=='href')
 links=Links();links.feed((dst/'index.html').read_text());assert all((dst/u.split('#')[0]).is_file() for u in links.links)
 csvrows=list(csv.DictReader(io.StringIO((dst/'observations.csv').read_text(encoding='utf-8-sig'))));assert len(csvrows)==6
 for aa,bb in zip(csvrows,new['rows']):
  for k,v in bb.items():assert (json.loads(aa[k]) if isinstance(v,list) else aa[k])==(v if isinstance(v,list) else str(v)),k
 assert new['rows'][:5]==base['rows']
 # Refuse a canonical source unexpectedly different from the accepted previous objects.
 own=read(R/A/'observations.json');assert own['rows']==base['rows']
 for n in ['observations.json','observations.csv','index.html','results.json']:copy(dst/n,R/A/n)
 write(F/'checks.json',{'renderer_rc':run.returncode,'renderer_sha256':h(M/A/'render.py'),'rows':6,'refs_by_row':[sum(len(rr[g]) for g in ['source','build','evidence']) for rr in new['rows']],'html_links':len(links.links),'all_links_resolved':True,'csv_all_fields_equal':True,'first_five_objects_unchanged':True,'historical315_modified':False,'prior_MAIN_observations_sha256':h(M/A/'observations.json'),'device_calls':0,'new_builds':0})
(P/'ACK.md').write_text('video-1919-r6-final-packet: scoped ACCEPT of evidence/restoration. Playback NOT_PASSED, audio unknown. Original helper errors preserved; explicit r2 guardian and actual final feed close restoration. See facts.txt for counts. No device/build calls or push.\n')
print(proc.stdout);print((F/'checks.json').read_text())
