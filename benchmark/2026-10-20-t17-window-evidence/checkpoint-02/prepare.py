#!/usr/bin/env python3
"""Local evidence checkpoint. Explicit --write; no device, archive or network calls."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--write',action='store_true'); a=ap.parse_args()
 if not a.write: print('Read-only default; --write creates a fresh checkpoint.'); return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020'; w=base/'t17-5cd-window-01'; mainrepo=ROOT.parent/'westlake-harness'; out=HERE/'packet'; out.mkdir(exist_ok=False); refs=[]
 def clean(s):
  for x,y in [(str(base),'BASE20'),(str(mainrepo),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]: s=s.replace(x,y)
  return s
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
 def ref(p): return dict(path='BASE20/'+str(p.relative_to(base)),sha256=sha(p),bytes=p.stat().st_size)
 def cp(p,n,binary=False):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True)
  if binary:q.write_bytes(p.read_bytes())
  else:q.write_text(clean(p.read_text()))
  refs.append(dict(**ref(p),public_path=n,public_sha256=sha(q),byte_exact=q.read_bytes()==p.read_bytes()))
 bd=w/'candidate-retry-profile-bindings'; bind=json.loads((bd/'result.json').read_text()); profile=w/'candidate-retry-profile/profile.json'
 assert bind['profile_sha256']==sha(profile) and bind['files_before']==bind['files_after']
 assert [r['label'] for r in bind['reads']]==['getaddrinfo','freeaddrinfo']
 for r in bind['reads']:
  p=bd/(r['label']+'.txt'); s=p.read_text(); assert '_DD_RC:0' in s
  row=next(x for x in s.splitlines() if re.fullmatch(r'(?: [0-9a-f]{2}){8}',x)); val=int.from_bytes(bytes.fromhex(row),'little')
  assert val==int(r['value'],16)==int(r['expected'],16) and r['match'] is True
  cp(p,'binding/'+p.name)
 for n in ['result.json']+[f'{phase}-{obj}.txt' for phase in ['before','after'] for obj in ['media','player','netcompat','libc']]:cp(bd/n,'binding/'+n)
 cp(profile,'binding/profile.json')
 dump('binding/maps-source-index.json',[ref(bd/n) for n in ['maps-before.txt','maps-after.txt']])
 for suffix in ['argv.json','rc','stdout','stderr']:cp(w/('candidate-retry-profile-reader-exec.'+suffix),'binding/reader-exec.'+suffix+'.txt')
 assert (w/'candidate-retry-profile-reader-exec.rc').read_text().strip()=='0'
 rg=w/'candidate-video-log-range'; rr=json.loads((rg/'result.json').read_text()); raw=rg/'selected.raw'
 assert raw.stat().st_size==rr['selected_bytes']==rr['source_end']-rr['source_start']==31631741
 assert sha(raw)==rr['sha256']=='4c4893c463f2074619ef580c7b1179afbcaade65b9d3f03d8f8a1e7884c289eb'
 cp(rg/'result.json','log-range/result.json'); dump('log-range/private-index.json',[ref(p) for p in sorted(rg.iterdir()) if p.is_file()])
 rel='benchmark/2026-10-20-t17-network-reuse/actual-video-log-review'; commit=subprocess.check_output(['git','-C',str(mainrepo),'rev-parse','15171a8271'],text=True).strip(); pins=[]
 for p in sorted((mainrepo/rel).rglob('*')):
  if not p.is_file():continue
  rp=str(p.relative_to(mainrepo)); blob=subprocess.check_output(['git','-C',str(mainrepo),'show',commit+':'+rp]); assert blob==p.read_bytes()
  pins.append(dict(path=rp,sha256=sha(p),bytes=p.stat().st_size))
 dump('log-range/main-excerpt-pins.json',dict(commit=commit,files=pins,interpretation='26 technical excerpts remain in MAIN; no media URL/token copied here. 254 mirror rows in this interval are subject to the 256-row cap. Zero literal matches in the selected interval do not prove global network-error absence.'))
 images=[]
 for i,name in enumerate(['capture-1792458744923711000','capture-1792458751704795000','capture-1792458758312352000']):
  d=w/name;p=d/'screen.jpeg';meta=json.loads((d/'screenshot.json').read_text());assert sha(p)==meta['sha256']
  cp(p,f'images/continuous-{i}.jpeg',True);cp(d/'screenshot.json',f'images/continuous-{i}.source.json');images.append(dict(source=ref(p),judgment='News feed; not continuous video playback evidence.'))
 dump('images/visual-review.json',dict(actual_images_read=True,images=images,scope='These captures follow guardian relaunches; do not attribute continuity to original child 7906. Video/audio remain unproven.'))
 event=w/'shell-1792458887115240000.stdout';lines=[x for x in event.read_text().splitlines() if 'boot=5807db3d' in x and ('seq=2' in x or 'seq=3' in x)]
 assert lines; (out/'guardian-events.txt').write_text('\n'.join(lines)+'\n');dump('guardian-source.json',ref(event))
 obs=w/'observer-stage/commands';cmd=json.loads((obs/'command-00009.json').read_text());shell=cmd['argv'][-1];err=(obs/'command-00009.stdout.txt').read_text()
 assert shell.index('cat /proc/7906/stat')<shell.index('mkdir /data/local/tmp/t17-lldb-') and 'No such file or directory' in err and '__BMS_REMOTE_RC_7db990d2b02841a39bd692c7b3da4443__1' in err
 for p in sorted(obs.iterdir()):cp(p,'observer/'+p.name)
 dump('observer/verdict.json',dict(transport_rc=cmd['exit_code'],remote_rc=1,first_fatal='Old child 7906 proc stat absent before stage mkdir',stage_reached=False,attach_reached=False,forward_reached=False,samples=0,scope='No observer samples; this is not an observer execution failure.'))
 assert (w/'rollback-exec.rc').read_text().strip()=='0'
 for n in ['rollback/result.json','rollback-exec.rc','rollback-exec.stdout','rollback-exec.stderr','restored-readiness-retry-boot.json']:cp(w/n,'restore/'+n.replace('/','--')+'.txt')
 waits=[]
 for name in ['restored-boot-wait','restored-readiness-retry-boot-wait']:
  for p in sorted((w/name).glob('*')):
   if p.is_file():waits.append(ref(p))
  stdout='\n'.join(p.read_text() for p in sorted((w/name).glob('*.stdout')));(out/('restore/'+name+'.stdout.txt')).write_text(stdout)
 dump('restore/wait-source-index.json',waits)
 dump('results.json',dict(token='t17-window-evidence',checkpoint=2,status='NOT_CLOSED',candidate_boot='5807db3d-32f6-4d16-a98a-0baad7352fb9',binding='PAIRED_BINDING_MATCH',log_range=dict(start=rr['source_start'],end=rr['source_end'],bytes=rr['selected_bytes'],sha256=rr['sha256']),mirror_rows=254,mirror_cap=256,global_network_error_absence='NOT_ESTABLISHED',later_log_findings='Three AudioTrack.native_get_buffer_size_frames error groups and ANW CPU-path diagnostics; see pinned MAIN excerpts, not a unique playback-root-cause conclusion.',continuous_images='RELAUNCHED_NEWS_FEED_NOT_VIDEO_CONTINUITY',video='NOT_PROVEN',audio='UNKNOWN',observer='OLD_PID_GUARD_REFUSED_BEFORE_STAGE',observer_samples=0,rollback_rc=0,restored_boot='04564c50-0d6e-4420-8db4-b9581b3658f7',readiness='Initial wait false/timeout retained; later retry true',restoration='PENDING_FINAL_IDENTITY_SNAPSHOT_FEED_AND_CLOSE',unlock='PENDING',whole_archive='NOT_CREATED',device_calls_by_lane=0))
 dump('public-source-index.json',refs)
 print(json.dumps(dict(status='CHECKPOINT_02_NOT_CLOSED',copied=len(refs),device_calls=0)))
if __name__=='__main__':main()
