#!/usr/bin/env python3
"""Collect a separate final supplement from completed local receipts; no device calls."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
BASE={f'BASE{d}':Path.home()/f'.local/share/westlake/toutiao-resume-202610{d}' for d in [19,20]}
MAIN=Path(os.environ.get('SOURCE_REPO',str(REPO.parent/'westlake-harness')))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alias(p):
 for k,v in [*BASE.items(),('MAIN',MAIN)]:
  if p.is_relative_to(v):return k+'/'+str(p.relative_to(v))
 return str(p).replace(str(Path.home()),'$HOME')
def pin(p):return {'path':alias(p),'sha256':sha(p),'bytes':p.stat().st_size}
def main():
 p=argparse.ArgumentParser();p.add_argument('--close',required=True);p.add_argument('--restore-run',required=True,help='actual directory containing record.json and screen.jpeg');p.add_argument('--out',required=True);a=p.parse_args()
 close=Path(a.close).expanduser().resolve();run=Path(a.restore_run).expanduser().resolve();out=Path(a.out).resolve()
 # No default successful status and no synthesized close time.
 c=json.loads(close.read_text());assert c.get('closed_at') or c.get('unlocked_at'),'missing actual terminal timestamp'
 b=BASE['BASE20'];before=b/'r13-video-before-snapshot/snapshot.json';after=b/'r13-video-restored-snapshot/snapshot.json'
 x=json.loads(before.read_text());y=json.loads(after.read_text());iv=b/'r13-video-restored-invariants.json'
 keys=['plan_sha256','collection_sha256','bind_targets','init_configs','labels','sha','params','selinux_enforce']
 eq={k:x[k]==y[k] for k in keys};assert all(eq.values());assert all(z['capture_status']=='COMPLETE' and z['plan_target_count']==64 and len(z['labels'])==351 for z in [x,y])
 r=json.loads((run/'record.json').read_text());im=run/'screen.jpeg';assert r['boot_id']==y['boot_id'];assert any(s['captured'] and s['sha256']==sha(im) for s in r['screenshots'])
 if c.get('restored_boot'):assert c['restored_boot']==r['boot_id']
 if c.get('feed_screenshot_sha256'):assert c['feed_screenshot_sha256']==sha(im)
 out.mkdir(parents=True,exist_ok=False)
 def put(n,d):(out/n).write_text(json.dumps(d,indent=2)+'\n')
 shutil.copyfile(close,out/'window-close.json');shutil.copyfile(iv,out/'restored-invariants.json');shutil.copyfile(im,out/'restored-screen.jpeg')
 s=json.dumps(r).replace(str(Path.home()),'$HOME');put('restored-record.json',{'source':pin(run/'record.json'),'record':json.loads(s)})
 put('snapshot-review.json',{'before':pin(before),'after':pin(after),'equal':eq,'targets':64,'labels':351,'do_not_compare':['raw proc/mount strings','PID','uptime']})
 cmd=[sys.executable,str(MAIN/'scripts/lab/run_facts.py'),str(run.parent)];v=subprocess.run(cmd,capture_output=True);(out/'facts.txt').write_bytes(v.stdout);(out/'facts-stderr.txt').write_bytes(v.stderr);put('facts-command.json',{'argv':[alias(Path(t)) if t.startswith('/') else t for t in cmd],'rc':v.returncode,'tool':pin(MAIN/'scripts/lab/run_facts.py')});assert v.returncode==0
 refs=[]
 for k,base in BASE.items():
  roots=sorted(base.glob('video-r13-video-*' if k=='BASE19' else 'r13-video-*'))
  if k=='BASE20':roots.append(base/'video-tab-readonly')
  for root in roots:
   for f in ([root] if root.is_file() else sorted(root.rglob('*'))):
    if f.is_file():refs.append(pin(f))
 put('raw-index.final.json',{'files':refs,'source':'completed local evidence; private raw retained'})
 put('results.json',{'token':'r13-video-window-evidence-ready','status':'FINAL_RECEIPTS_COLLECTED_REVIEW_PENDING','samples':0,'video_tab':'NOT_REACHED','observer_started':False,'exit_cause':'NOT_INVESTIGATED','prior_checkpoint':'../checkpoint-01/results.json','baseline_first_child':{'pid':8654,'birth':18108,'outcome':'exited before feed, original host image retained'},'close':pin(close),'restored_record':pin(run/'record.json'),'visual_review':'PENDING_INDEPENDENT_IMAGE_READ','cleanup_identity_review':'PENDING_EXACT_RAW_REVIEW','device_calls':0})
 print(json.dumps({'out':alias(out),'status':'COLLECTED_REVIEW_PENDING','indexed_files':len(refs)}))
if __name__=='__main__':main()
