#!/usr/bin/env python3
"""Read-only local checkpoint. No device operations or exit-cause analysis."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
MAIN=Path(os.environ.get('SOURCE_REPO',str(REPO.parent/'westlake-harness')))
B={f'BASE{d}':Path.home()/f'.local/share/westlake/toutiao-resume-202610{d}' for d in [19,20]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p,alias,base):return {'path':alias+'/'+str(p.relative_to(base)),'sha256':sha(p),'bytes':p.stat().st_size}
def write(n,x):
 p=HERE/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 a=B['BASE19'];b=B['BASE20'];live=a/'video-r13-video-live';children=[]
 for name,pid,birth,seq,event in [('feed-settled',6994,10987,1,129),('reentry-settled',13863,21220,2,246)]:
  d=live/name;rec=json.loads((d/'record.json').read_text());image=d/'screen.jpeg';assert sha(image)==rec['screenshots'][0]['sha256']
  g=d/'guardian-after.txt';lines=g.read_text().splitlines();events=[x for x in lines if f'child={pid} child_birth={birth}' in x];assert any(x.startswith(str(event)+' ') and 'reason=process_exit first_read_exited' in x for x in events)
  ps=d/'processes-after.txt';assert not any(x.split()[:1]==[str(pid)] for x in ps.read_text().splitlines());assert any(x.split()[:1]==['5116'] for x in ps.read_text().splitlines())
  out=HERE/'evidence'/name;out.mkdir(parents=True,exist_ok=True);shutil.copyfile(image,out/'screen.jpeg')
  (out/'guardian-excerpt.txt').write_text('\n'.join(events)+'\n')
  public_rec=json.loads(json.dumps(rec).replace(str(Path.home()),'$HOME'))
  write('evidence/'+name+'/record.json',{'source':pin(d/'record.json','BASE19',a),'record':public_rec})
  children.append({'sequence':seq,'pid':pid,'birth':birth,'parent':5116,'parent_birth':9367,'exit_event':event,'exit_cause':'NOT_INVESTIGATED','final_image_visual_review':'Westlake IME host; no feed visible','guardian_ready_is_not_visual_acceptance':True,'raw':[pin(p,'BASE19',a) for p in [d/'record.json',image,g,ps]],'guardian_READY_event':242 if seq==2 else None})
 assert any('242 '==x[:4] and 'transition_target=READY' in x for x in (live/'reentry-settled/guardian-after.txt').read_text().splitlines())
 write('children.json',children)
 board=MAIN/'.octos/boards/app-lighting.md';lines=board.read_text(errors='replace').splitlines();selected=[{'line':i+1,'text':s} for i,s in enumerate(lines) if ('2026-10-20T06:09:11+0800' in s and s.startswith('LOCK(')) or ('2026-10-20T06:13:21+0800' in s and 'addendum' in s)];assert len(selected)==2
 write('evidence/board-excerpt.json',{'source':pin(board,'MAIN',MAIN),'excerpt':selected,'scope':'point-in-time source hash; canonical board continues to grow'})
 for name in ['apply','rollback']:
  p=a/f'video-r13-video-{name}/result.json';write('evidence/'+name+'.json',{'source':pin(p,'BASE19',a),'result':json.loads(p.read_text())})
 # Point-in-time references only: active restore evidence is not finalized or archived here.
 rows=[];roots=[]
 for alias,base in B.items():
  rr=sorted(base.glob('video-r13-video-*' if alias=='BASE19' else 'r13-video-*'))
  if alias=='BASE20':rr.append(base/'video-tab-readonly')
  for root in rr:
   roots.append(alias+'/'+root.name)
   for f in ([root] if root.is_file() else sorted(root.rglob('*'))):
    if f.is_file():rows.append(pin(f,alias,base))
 write('raw-index.json',{'status':'CHECKPOINT_NOT_FINAL_ARCHIVE','aliases':{k:'$HOME/.local/share/westlake/'+v.name for k,v in B.items()},'roots':roots,'files':rows,'notice':'Only indexed bytes at collection time. Restore roots may still grow; final closure/archive requires a new index.'})
 absent=[b/n for n in ['r13-video-admission.json','r13-video-observation','r13-video-observer','r13-video-server-attach']]
 write('evidence/nonexecution.json',{'server_stage_present':(b/'r13-video-server-stage').exists(),'absent_paths':[str(p).replace(str(Path.home()),'$HOME') for p in absent if not p.exists()],'outer_report':'No video-tab entry, five-module qualification, attach or observer invocation','observer_samples':0,'qualification':'NOT_REACHED','video_playback':'NOT_OBSERVED','absence_scope':'local artifacts plus canonical outer report, not a new device inspection'})
 cmd=[sys.executable,str(MAIN/'scripts/lab/run_facts.py'),str(live)];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
 (HERE/'facts.txt').write_bytes(r.stdout);(HERE/'facts-stderr.txt').write_bytes(r.stderr);write('facts-command.json',{'argv':[x.replace(str(Path.home()),'$HOME') for x in cmd],'rc':r.returncode,'tool':pin(MAIN/'scripts/lab/run_facts.py','MAIN',MAIN)})
 write('results.json',{'token':'r13-video-window-evidence-ready','status':'CANDIDATE_NOT_REACHED_RESTORE_PENDING','candidate_boot':'10478050-e996-43b1-8d96-9c4e2ab99224','locked_at':'2026-10-20T06:09:11+0800','manual_icon_attempts':2,'normal_reentry_addendum':'one additional normal icon launch, same observer gates','children':[{'pid':x['pid'],'birth':x['birth'],'exit_event':x['exit_event']} for x in children],'observed_images':['HOST','HOST'],'observer_started':False,'samples':0,'five_module_check':'NOT_REACHED','video_tab':'NOT_REACHED','playback':'NOT_OBSERVED','rollback_placement_receipt_present':True,'final_restore':'PENDING','unlock':'PENDING','exit_root_cause':'NOT_INVESTIGATED','device_calls_by_reviewer':0})
 print(json.dumps({'children':2,'reviewed_terminal_images':2,'raw_files_indexed':len(rows),'restore':'PENDING','facts':r.stdout.decode().splitlines()[-1]}))
if __name__=='__main__':main()
