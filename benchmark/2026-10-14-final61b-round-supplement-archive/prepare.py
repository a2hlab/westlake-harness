#!/usr/bin/env python3
"""Prepare a regular-file supplement after original round closure; no device calls."""
import datetime, hashlib, json, os, shutil, stat, subprocess, tarfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WINDOWS = ROOT/'benchmark/2026-10-14-final61b-full128-window-archive'
ROUND = ROOT.parent/'westlake-harness-t0/benchmark/2026-10-14-final61b-next-binding/actual-running-086db6c7/identity128/round'
SERIAL = '61b0657200000000000000000324012c'
STAGE = HERE/'.artifacts/staging'
BOOT = '086db6c7-a7e7-40ce-a336-9608adc05afc'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def portable(p):return '$WORKSPACES/'+str(p.relative_to(ROOT.parent))
def regular(p):
 # All source descendants must have literal regular/directory ancestry, not links.
 base=ROUND if p.is_relative_to(ROUND) else WINDOWS
 assert p.is_relative_to(base)
 cur=base
 assert stat.S_ISDIR(cur.lstat().st_mode)
 for part in p.relative_to(base).parts[:-1]:
  cur=cur/part;assert stat.S_ISDIR(cur.lstat().st_mode),portable(cur)
 s=p.lstat();assert stat.S_ISREG(s.st_mode),portable(p)
 return s
def entry(p):
 s=regular(p)
 return dict(path=portable(p),bytes=s.st_size,sha256=digest(p),mode=stat.S_IMODE(s.st_mode),mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,inode=s.st_ino)
def shape():
 rows=[];files=[];links={};base=ROUND/'final'/SERIAL
 assert stat.S_ISDIR((ROUND/'final').lstat().st_mode)
 assert stat.S_ISDIR(base.lstat().st_mode)
 assert sorted(p.name for p in (ROUND/'final').iterdir())==[SERIAL]
 for p in sorted(ROUND.iterdir()):
  mode=p.lstat().st_mode
  if stat.S_ISREG(mode):files.append(p)
  else:
   assert stat.S_ISDIR(mode) and (p.name=='final' or p.name in {f'window-{n:02}' for n in range(1,9)}),p.name
 for p in sorted(base.iterdir()):
  s=p.lstat()
  if stat.S_ISREG(s.st_mode):
   assert p.name in {'runtime-fingerprint.txt','boot-image-fingerprint.txt','plan.json'}
   files.append(p)
  else:
   assert stat.S_ISLNK(s.st_mode)
   links[p.name]={'link':str(p.relative_to(ROUND)),'text':os.readlink(p),'mode':s.st_mode,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'inode':s.st_ino}
 return files,links

def main():
 assert not STAGE.exists(),'refuse staging overwrite'
 done=read(ROUND/'round-complete.json');assert done['recorded_keys']==128
 # Original detached invocation never captured an OS exit code; do not invent it.
 ps=subprocess.run(['ps','-p','24226','-o','pid=,command='],capture_output=True,text=True)
 assert not ps.stdout.strip(),'original driver PID still present; wait for closure'
 (HERE/'driver-absence.stdout.txt').write_text(ps.stdout)
 (HERE/'driver-absence.stderr.txt').write_text(ps.stderr)
 save(HERE/'driver-absence.json',{'pid':24226,'command':['ps','-p','24226','-o','pid=,command='],'rc':ps.returncode,'stdout_sha256':digest(HERE/'driver-absence.stdout.txt'),'stderr_sha256':digest(HERE/'driver-absence.stderr.txt'),'observed_at':datetime.datetime.now().astimezone().isoformat(),'driver_exit_code':None})
 expected=read(WINDOWS/'final-aggregate-plan/results.json')['planned_members'];assert len(expected)==128
 files,links=shape();assert set(links)==set(expected),'aggregate key mismatch'
 before=[entry(p) for p in files]
 # No recursive unknown-link traversal: only regular files and literal link metadata.
 opened=subprocess.run(['lsof','-n','-P',*[str(p) for p in files]],capture_output=True,text=True,timeout=60)
 (HERE/'open-files.stdout.txt').write_text(opened.stdout.replace(str(ROOT.parent),'$WORKSPACES'))
 (HERE/'open-files.stderr.txt').write_text(opened.stderr.replace(str(ROOT.parent),'$WORKSPACES'))
 assert opened.returncode in (0,1) and not opened.stderr
 assert not [l for l in opened.stdout.splitlines()[1:] if len(l.split())>3 and l.split()[3].endswith(('w','u'))]
 time.sleep(5)
 files2,links2=shape();assert files==files2 and links==links2 and before==[entry(p) for p in files2]
 STAGE.mkdir(parents=True)
 for name in ['driver-absence.json','driver-absence.stdout.txt','driver-absence.stderr.txt']:
  shutil.copy2(HERE/name,STAGE/name)
 source_rows=list(before);mappings=[];archive_pins=[]
 for n in range(1,9):
  window=f'window-{n:02}';report=WINDOWS/window;receipt=read(report/'archive.json');result=read(report/'results.json')
  assert result['status']=='complete' and receipt['verified_remote'] and receipt['archive_members_verified'] and receipt['source_unchanged']
  identity=read(ROUND/window/'after-identity/identity.json');board=read(ROUND/window/'runner/board-run-result.json')
  assert identity['passed'] and identity['diff']=={} and identity['candidate_paths']==954 and identity['boot_before']==identity['boot_after']==BOOT
  assert board['before_unlock']==board['smoke']==0
  manifest=report/'.artifacts/source-manifest.jsonl';archive=report/'.artifacts/full128-window.tar.gz'
  assert digest(manifest)==receipt['source_manifest_sha256']
  assert digest(archive)==receipt['sha256'] and archive.stat().st_size==receipt['bytes']
  rows={r['path']:r for r in map(json.loads,manifest.read_text().splitlines())};selected={}
  for key,plan in expected.items():
   if plan['window']!=window:continue
   prefix=window+'/runner/'+plan['original_shard']+'/'
   candidates=[]
   for name,row in rows.items():
    if name.startswith(prefix) and name.endswith('/record.json'):
     p=ROUND/name;s=entry(p);assert s['sha256']==row['sha256'] and s['bytes']==row['bytes']
     r=read(p)
     if r.get('key') and not r.get('install_only'):candidates.append((name,row,p,r))
   assert len(candidates)==1 and candidates[0][3]['key']==key,key
   name,row,p,r=candidates[0]
   assert links[key]['text']==str(p.parent),'link target differs from known canonical record'
   selected[name]=row
   shots=[]
   for shot in r.get('screenshots') or []:
    if not shot.get('captured'):continue
    image=p.parent/Path(shot.get('path') or ('t'+str(shot['scheduled_seconds']).removesuffix('.0')+'.jpeg')).name
    iname=str(image.relative_to(ROUND));ir=rows[iname];actual=entry(image)
    assert actual['sha256']==ir['sha256']==shot['sha256'] and actual['bytes']==ir['bytes']
    selected[iname]=ir;shots.append({'tar_member':iname,'sha256':ir['sha256'],'bytes':ir['bytes'],'scheduled_seconds':shot.get('scheduled_seconds')})
   mappings.append({'key':key,'aggregate_link_relative_path':links[key]['link'],'original_link_text_exact':links[key]['text'],'original_link_text_sha256':hashlib.sha256(links[key]['text'].encode()).hexdigest(),'resolved_record_path_from_admitted_source':portable(p),'record_tar_member_path':name,'resolved_record_sha256':row['sha256'],'resolved_record_bytes':row['bytes'],'window':window,'window_archive_receipt_sha256':digest(report/'archive.json'),'window_archive_remote':receipt['archive'],'window_archive_sha256':receipt['sha256'],'window_archive_bytes':receipt['bytes'],'required_screenshot_tar_members':shots})
  seen=set()
  with tarfile.open(archive,'r:gz') as tar:
   for member in tar:
    if member.name not in selected:continue
    assert member.isfile() and member.name not in seen
    data=tar.extractfile(member).read();r=selected[member.name]
    assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256'];seen.add(member.name)
  assert seen==set(selected)
  for filename in ['archive.json','results.json','source-readiness.json','completed-source-gates.json']:
   p=report/filename;source_rows.append(entry(p));dest=STAGE/'window-archive-receipts'/window/filename;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
  archive_pins.append({'window':window,**receipt,'receipt_sha256':digest(report/'archive.json'),'bound_members':len(selected)})
 for p in files:
  dest=STAGE/'original-round'/p.relative_to(ROUND);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 assert len(mappings)==128
 save(STAGE/'aggregate-link-map.raw.json',{'links':sorted(mappings,key=lambda r:r['key'])})
 save(STAGE/'window-archive-pins.json',archive_pins)
 save(STAGE/'source-snapshot.json',source_rows)
 save(STAGE/'source-link-snapshot.raw.json',links)
 files3,links3=shape();assert files3==files and links3==links and before==[entry(p) for p in files3]
 for row in source_rows:
  p=ROOT.parent/row['path'].removeprefix('$WORKSPACES/');assert entry(p)==row
 summary={'status':'STAGING_COMPLETE_NOT_YET_ARCHIVED','device_calls':0,'source_unchanged':True,'original_round_recorded_keys':128,'original_driver_pid_absent':True,'driver_exit_code':None,'driver_exit_code_reason':'Original --detach invocation did not capture final OS exit status; original completion and per-window receipts are preserved.','link_count':128,'window_archives':8,'selected_original_regular_files':len(files),'source_snapshot_sha256':digest(STAGE/'source-snapshot.json'),'raw_link_map_sha256':digest(STAGE/'aggregate-link-map.raw.json'),'source_links_sha256':digest(STAGE/'source-link-snapshot.raw.json'),'all_selected_archive_members_verified':True,'regular_sources':before,'absent_conditional_final_files':sorted({'runtime-fingerprint.txt','boot-image-fingerprint.txt','plan.json'}-{p.name for p in files if p.parent==ROUND/'final'/SERIAL}),'comparison_jpeg_scope':'Peer comparison JPEGs and maps are not in this round supplement. Original captured screenshots and exact key/record/member mapping are preserved in the linked eight archives. Closed peer products may be archived separately.','final_signoff_included':False,'active_index_included':False,'staged_at':datetime.datetime.now().astimezone().isoformat()}
 save(HERE/'prepared.json',summary)
 print(json.dumps({k:summary[k] for k in ['status','link_count','window_archives','selected_original_regular_files']}))
if __name__=='__main__':main()
