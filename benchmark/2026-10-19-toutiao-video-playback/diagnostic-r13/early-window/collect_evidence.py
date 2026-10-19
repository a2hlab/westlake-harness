#!/usr/bin/env python3
"""Offline evidence collection only; never executes archived device scripts."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
MAIN=Path(os.environ.get('SOURCE_REPO',str(REPO.parent/'westlake-harness'))).resolve()
BASE=Path.home()/'.local/share/westlake'
ROOTS={'BASE19':BASE/'toutiao-resume-20261019','BASE20':BASE/'toutiao-resume-20261020','MAIN':MAIN}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):
 for alias,root in ROOTS.items():
  if p.is_relative_to(root):return alias+'/'+str(p.relative_to(root))
 raise ValueError('unaliased source')
def pin(p):return {'path':ref(p),'sha256':sha(p),'bytes':p.stat().st_size}
def dump(n,x):
 p=HERE/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def copy(p,n):
 q=HERE/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);return pin(p)
def js(p):return json.loads(p.read_text())
def public(x):
 s=json.dumps(x)
 for a,r in sorted(ROOTS.items(),key=lambda x:len(str(x[1])),reverse=True):s=s.replace(str(r),a)
 s=s.replace(str(Path.home()),'$HOME')
 return json.loads(s)
def main():
 b=ROOTS['BASE20'];a=ROOTS['BASE19'];refs=[]
 for src,dst in [(b/'r13-early-close.json','evidence/window-close.json'),(b/'r13-early-restored-invariants.json','evidence/restored-invariants.json'),(b/'r13-early-readiness/failure.json','evidence/readiness-first-failure.json'),(b/'r13-early-readiness-r2/failure.json','evidence/readiness-r2-failure.json'),(a/'video-r13-early-apply/result.json','evidence/apply-result.json'),(a/'video-r13-early-rollback/result.json','evidence/rollback-result.json')]:refs.append(copy(src,dst))
 for name in ['early_acquire.first.py','early_acquire.py','early_acquire_r2.py','r13_early_outer.py','reboot_early.py']:
  p=b/name;assert str(Path.home()) not in p.read_text();refs.append(copy(p,'sources/'+name))
 # Source identity, not an assertion that the template was an executable admission.
 for name in ['core.py','identity.py','observer.py','observe.py']:
  refs.append(pin(MAIN/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13'/name))
 template=js(b/'r13-admission-template.json');refs.append(pin(b/'r13-admission-template.json'))
 audit=js(b/'early-readiness-module-audit.json');assert len(audit)==9
 audit_verified=[]
 for row in audit:
  cmd=b/'r13-early-readiness-r2/commands'/row['receipt'];out=cmd.with_suffix('.stdout.txt');d=js(cmd);text=out.read_text()
  roles={k:any(line.split()[-1:]==[m['remote_path']] for line in text.splitlines()) for k,m in template['modules'].items()}
  assert d['exit_code']==0 and roles==row['roles']=={'player':False,'android':True,'shim':True,'bridge':True,'hwui':True}
  audit_verified.append({'command':pin(cmd),'stdout':pin(out),'time':row['time'],'roles':roles})
 dump('evidence/maps-audit.json',{'source':pin(b/'early-readiness-module-audit.json'),'exact_path_recheck':audit_verified,'scope':'path availability only; not GOT/provider/ABI or playback proof'})
 # Name mismatch is supported by both actual ps and proc stat, not guessed from failure alone.
 ps_sources=[]
 for p in sorted((b/'r13-early-readiness/commands').glob('*.json')):
  d=js(p)
  if 'ps -A -o PID,PPID,UID,NAME' in ' '.join(d.get('argv',[])):
   out=p.with_suffix('.stdout.txt');rows=[s for s in out.read_text().splitlines() if s.split()[:3]==['7462','5602','20011206']]
   if rows:ps_sources.append({'receipt':pin(p),'stdout':pin(out),'rows':rows})
 assert ps_sources
 correction=b/'early-readiness-correction/stdout.txt';ct=correction.read_text();statline=next(x for x in ct.splitlines() if x.startswith('7462 ('))
 assert '(id.article.news)' in statline
 dump('evidence/name-correction.json',{'first_predicate':'ps NAME == id.article.news','actual_ps':ps_sources[0],'actual_proc_stat':{'source':pin(correction),'line':statline},'r2_predicate':'ps NAME == com.ss.android.article.news','r2_fixed_identity':[5602,12828,7462,14456],'no_child_restart_between_readiness_attempts':'same identity evidenced; not a new observer attempt'})
 missing=[b/'r13-early-admission.json',b/'r13-early-observer',b/'r13-early-server-attach']
 assert all(not p.exists() for p in missing)
 dump('evidence/nonexecution.json',{'absent_paths':[ref(p) for p in missing],'stage_present':(b/'r13-early-server-stage').is_dir(),'readiness_ready_files_present':[ (b/n/'ready.json').exists() for n in ['r13-early-readiness','r13-early-readiness-r2']],'samples':0,'observer_started':False,'interpretation':'No observer result was fabricated; both readiness branches stopped before attach.'})
 before=js(b/'r13-early-before-snapshot/snapshot.json');after=js(b/'r13-early-restored-snapshot/snapshot.json');iv=js(b/'r13-early-restored-invariants.json')
 eq={k:before[k]==after[k] for k in iv['equal']};assert all(eq.values());assert all(x['capture_status']=='COMPLETE' and x['plan_target_count']==64 and len(x['labels'])==351 for x in [before,after])
 dump('evidence/snapshot-review.json',{'before':pin(b/'r13-early-before-snapshot/snapshot.json'),'restored':pin(b/'r13-early-restored-snapshot/snapshot.json'),'equal':eq,'targets':64,'labels':351,'collection_sha256':after['collection_sha256'],'excluded_from_equality':['boot_id','pids','uptime','raw mount strings']})
 close=js(b/'r13-early-close.json');rd=b/'r13-early-close-readonly';raw=(rd/'1.stdout').read_text();fw=(rd/'0.stdout').read_text()
 assert js(rd/'0.json')['rc']==js(rd/'1.json')['rc']==0
 assert 'TracerPid:\t0' in raw and 'State:\tS (sleeping)' in raw and 'errNum is:106!' in raw and close['restored_boot'] in raw
 assert fw.strip()=='[Empty]'
 tcp=[line.split() for line in raw.splitlines() if len(line.split())>=4 and line.split()[0].rstrip(':').isdigit() and ':' in line.split()[1]]
 assert not any(r[1].endswith(':13AF') and r[3]=='0A' for r in tcp)
 dump('evidence/cleanup-review.json',{'references':[pin(p) for p in sorted(rd.iterdir()) if p.is_file()],'tracer_pid':0,'child_state':'S','forward5039_absent':True,'listener5039_absent':True,'parameter_absent_rc_text':106,'network_rows_not_published':True})
 private=a/'video-r13-early-restored-private-check';pplan=js(private/'plan.json');checks=[]
 for stem,key in [('00011','before_sha'),('00027','media_before_sha'),('00039','player_before_sha')]:
  p=private/'commands'/('command-'+stem+'.stdout.txt');assert p.read_text().split()[0]==pplan[key];checks.append({'expected_sha256':pplan[key],'stdout':pin(p)})
 p=private/'commands/command-00051.stdout.txt';assert p.read_text().strip().endswith('__0');d=js(private/'commands/command-00051.json');assert d['exit_code']==0
 dump('evidence/private-restore-review.json',{'plan':pin(private/'plan.json'),'originals':checks,'private_inode_and_compat_absence_command':pin(private/'commands/command-00051.json'),'stdout':pin(p),'remote_rc':0,'meaning':'Exact original hashes; guarded shell checks source/private inode equality and compat absence.'})
 for label,src in [('candidate-feed',a/'video-r13-early-live/after-readiness'),('restored-feed',a/'video-r13-early-restore-live/restored-feed')]:
  refs.append(copy(src/'screen.jpeg','images/'+label+'.jpeg'));r=js(src/'record.json');assert r['screenshots'][0]['sha256']==sha(src/'screen.jpeg');dump('evidence/'+label+'-record.json',{'raw_source':pin(src/'record.json'),'record':public(r),'visual_review':'feed visible, reviewed independently; no playback claim'})
 assert sha(HERE/'images/restored-feed.jpeg')==close['feed_screenshot_sha256']
 cmd=[sys.executable,str(MAIN/'scripts/lab/run_facts.py'),str(a/'video-r13-early-restore-live')];r=subprocess.run(cmd,capture_output=True)
 assert r.returncode==0
 (HERE/'evidence/facts.txt').write_bytes(r.stdout);(HERE/'evidence/facts.stderr.txt').write_bytes(r.stderr)
 total=r.stdout.decode().splitlines()[-1];assert total=='TOTAL keys=2 screenshots_captured=2/2 alive_t5=0 alive_last=0 alive_unknown=2'
 dump('evidence/facts-command.json',{'argv':public(cmd),'rc':r.returncode,'tool':pin(MAIN/'scripts/lab/run_facts.py')})
 dump('references.json',{'aliases':{'BASE19':'$HOME/.local/share/westlake/toutiao-resume-20261019','BASE20':'$HOME/.local/share/westlake/toutiao-resume-20261020','MAIN':'$WORKSPACES/westlake-harness'},'files':refs})
 dump('results.json',{'token':'r13-early-evidence-ready','status':'RESTORED_NO_ATTACH_NO_SAMPLES','readiness_first':'NAME_MISMATCH_CHOSEN_NULL','readiness_r2':'SAME_CHILD_PLAYER_UNMAPPED_AT_DEADLINE','maps_checks':9,'other_four_roles_present':True,'observer_started':False,'admission_created':False,'samples':0,'playback':'NOT_PASSED','exit_cause_investigated':False,'restored_boot':close['restored_boot'],'restored_identity':{'parent':5455,'parent_birth':7496,'child':8221,'child_birth':9117},'restoration':'VERIFIED_WITH_FEED','locked_at':close['locked_at'],'closed_at':close['closed_at'],'elapsed_seconds':694,'facts_total':total,'review_device_calls':0,'remote_archive':'see archive/receipt.json'})
 print(json.dumps({'status':'PASS','maps_checks':9,'snapshot_targets':64,'labels':351,'facts':total}))
if __name__=='__main__':main()
