#!/usr/bin/env python3
"""Review completed local recovery receipts; zero device/network calls."""
from pathlib import Path
import json,hashlib,re,shutil,subprocess,sys
D=Path(__file__).resolve().parent;R=next(p for p in D.parents if (p/'scripts/lab/run_facts.py').is_file());B=Path.home()/'.local/share/westlake/toutiao-resume-20261019';refs=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def bind(n):
 p=B/n;refs.append({'path':'BASE19/'+n,'sha256':sha(p),'bytes':p.stat().st_size});return p
def read(n):return json.loads(bind(n).read_text())
a=read('video-r10-apply/plan.json');z=read('video-r10-rollback/result.json');close=read('video-r10-window-close.json')
assert z['origin_apply_plan_sha256']==sha(B/'video-r10-apply/plan.json') and z['origin_apply_boot']==a['boot'] and z['origin_apply_wid']==a['wid']
for k in ['dso_sha','cfg_sha','media_before_sha','media_after_sha','player_before_sha','player_after_sha']:assert z[k]==a[k]
for k in ['backup','media_backup','player_backup']:assert z[k].endswith('.ttvideo-before-'+a['boot'][:8])
rc=read('video-r10-rollback/commands/command-00071.json');assert rc['exit_code']==0
out=bind('video-r10-rollback/commands/command-00071.stdout.txt').read_text();assert 'VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED' in out and re.search(r'__BMS_REMOTE_RC_\w+__0',out)
assert read('video-r10-restore-reboot/result.json')['completed'] is True
ready=read('video-r10-restore-ready/ready.json');assert ready['ready'] and ready['boot']==close['restored_boot'] and ready['boot']!=z['boot']
param=bind('video-r10-restored-metadata/param-before.txt').read_text();assert 'errNum is:106!' in param
record=read('video-r10-restored-identity/baseline-final/record.json');rc=read('video-r10-restored-identity/baseline-final/commands/command-00007.json');assert rc['exit_code']==0
raw=bind('video-r10-restored-identity/baseline-final/commands/command-00007.stdout.txt').read_text();assert re.search(r'__BMS_REMOTE_RC_\w+__0',raw)
command='\n'.join(record['commands']);assert 'stat -L -c %d:%i' in command and command.count('test ! -e')==2 and a['cfg_sha'] in command
for h in [a['before_sha'],a['media_before_sha'],a['player_before_sha']]:assert raw.count(h)==2
assert 'errNum is:106!' in raw
first=bind('video-r10-restored-live/settled-first/step-0.txt').read_text();assert 'AWAITING_REENTRY' in first and 'child=8471' in first
last=bind('video-r10-restored-live/second-feed-check/step-0.txt').read_text();assert last.startswith('READY\n')
for s in ['parent=5711','parent_birth=6931','child=14878','birth=17281','seq=2']:assert s in last
stat=next(s for s in last.splitlines() if s.startswith('14878 ('));f=stat.split(') ',1)[1].split();assert f[0]=='S' and f[1]=='5711' and f[19]=='17281'
ref=read('video-r10-state-before/snapshot.json');cur=read('video-r10-state-restored/snapshot.json');diff=read('video-r10-state-diff.json')
for s in [ref,cur]:assert s['capture_status']=='COMPLETE' and s['complete'] and s['collection_complete'] and s['boot_stable'] and not s['errors'] and s['plan_target_count']==64 and len(s['labels'])==351
for k in ['plan_sha256','collection_sha256','bind_targets','init_configs','labels','sha','params','selinux_enforce']:assert ref[k]==cur[k],k
assert diff['comparable'] and diff['coverage_complete'] and diff['plan_comparable']
feed=bind('video-r10-restored-live/second-feed-check/screen.jpeg');assert sha(feed)==close['feed_sha256']=='8dca98534fdf9f316e4ec3ebe0241b1d8d2e4f8fc5fbdd4ad0ecdac7ae51bda3'
assert close['lock_released'] and close['closed_at']=='2026-10-20T03:39:55.386376+08:00'
archive=read('video-r10-window-archive/receipt.json');assert archive['remote_verified'] and archive['archive_sha256']=='5f51ca3255acaed29e84bda57c89fa24ea88a2a95f8387fa7475abbd9fcd958e' and archive['bytes']==10302633
archive['remote']='HW248_ARTIFACT_ROOT/toutiao-video-r10-20261020/window.tar.gz';(D/'archive-receipt.public.json').write_text(json.dumps(archive,indent=2)+'\n')
for n,dest in [('video-r10-window-close.json','window-close.json'),('video-r10-rollback/result.json','rollback-result.json'),('video-r10-apply/plan.json','original-apply-plan.json'),('video-r10-restored-metadata/param-before.txt','parameter-restored.txt'),('video-r10-restored-live/second-feed-check/step-0.txt','final-guardian.txt'),('video-r10-restored-live/settled-first/step-0.txt','first-baseline-exit.txt')]:shutil.copyfile(B/n,D/dest)
(D/'baseline-excerpt.txt').write_text(raw.split('  PID  PPID',1)[0]);(D/'rollback-command.stdout.txt').write_text(out)
view=D/'facts-layout/restored-feed';view.mkdir(parents=True,exist_ok=True);shutil.copyfile(feed,view/'screen.jpeg');fr=read('video-r10-restored-live/second-feed-check/record.json')
for shot in fr['screenshots']:shot['path']=Path(shot['path']).name
(view/'record.json').write_text(json.dumps(fr,indent=2)+'\n')
summary={k:cur[k] for k in ['boot_id','plan_sha256','collection_sha256','plan_target_count','capture_status','selinux_enforce']};summary.update(labels=len(cur['labels']),actual_bind_targets=len(cur['bind_targets']),invariant_fields_equal=True,raw_proc_mount_string_equality_required=False)
(D/'snapshot-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
res={'token':'video-2020-r10-restore-review','status':'SCOPED_RESTORATION_ACCEPT','origin_apply_plan_sha256':z['origin_apply_plan_sha256'],'restored_boot':ready['boot'],'parent':5711,'parent_birth':6931,'child':14878,'child_birth':17281,'first_baseline_child':8471,'first_baseline_outcome':'AWAITING_REENTRY, exit cause not investigated','second_normal_icon':'READY_AND_REAL_FEED','restored_originals':'run/media/player exact source/private SHA and inode checks rc0; CFG check; compat source/private absence','parameter':'ABSENT_ERR106','snapshot':'COMPLETE same plan64targets/351labels and collection/invariant fields','feed_visual_review':'Independently viewed real news feed; not video playback','lock_released':True,'closed_at':close['closed_at'],'archive_sha256':archive['archive_sha256'],'archive_remote_verification':'outer receipt; no new remote query by reviewer','playback':'NOT_PASSED','audio':'UNKNOWN','device_calls':0}
(D/'results.json').write_text(json.dumps(res,indent=2)+'\n');(D/'private-source-index.json').write_text(json.dumps(refs,indent=2)+'\n')
r=subprocess.run([sys.executable,str(R/'scripts/lab/run_facts.py'),str(D/'facts-layout')],capture_output=True);assert r.returncode==0;(D/'facts.txt').write_bytes(r.stdout)
print(json.dumps(res,indent=2));print(r.stdout.decode())
