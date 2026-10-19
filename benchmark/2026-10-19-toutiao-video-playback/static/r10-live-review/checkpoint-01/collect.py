#!/usr/bin/env python3
"""Read completed local r10 files; no device commands. Public URL-free excerpt."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
D=Path(__file__).resolve().parent
ROOT=next(p for p in D.parents if (p/'scripts/lab/run_facts.py').is_file())
B=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=[]
def bind(p):
 refs.append({'path':'BASE19/'+str(p.relative_to(B)),'sha256':sha(p),'bytes':p.stat().st_size})
 return p
identity={'boot':'34309d1e-48b0-47c7-b8b1-732cdd7bce02','parent':5160,'parent_birth':7985,'child':7080,'child_birth':9491}
for folder,checks in [('video-r10-logger-binding',['player_mirror_GOT','compat_vprint_GOT']),('video-r10-network-binding',['media_getaddrinfo_GOT','media_freeaddrinfo_GOT'])]:
 p=B/folder;obj=json.loads(bind(p/'reads.json').read_text())
 assert all(obj[k]==v for k,v in identity.items())
 assert obj['identity_after_reads']=='same guarded boot/parent/child births'
 assert all(obj['binding_checks'][n]['match'] is True and obj['binding_checks'][n]['actual']==obj['binding_checks'][n]['expected'] for n in checks)
 bm=bind(p/'maps-before.txt').read_text().splitlines();am=bind(p/'maps-after.txt').read_text().splitlines()
 for f in sorted(p.glob('before-*-identity.txt')):
  z=p/f.name.replace('before-','after-',1);bind(f);bind(z);assert f.read_bytes()==z.read_bytes()
  lines=f.read_text().splitlines();path=lines[0].split()[1].split('/root',1)[1];dev,ino=map(int,lines[1].split(':'))
  rows=[s for s in bm if s.split()[-1]==path];assert rows and rows==[s for s in am if s.split()[-1]==path]
  major=((dev>>8)&0xfff)|((dev>>32)&~0xfff);minor=(dev&0xff)|((dev>>12)&~0xff)
  assert all(tuple(int(t,16) for t in s.split()[3].split(':'))==(major,minor) and int(s.split()[4])==ino for s in rows)
 shutil.copyfile(p/'reads.json',D/(folder+'.json'))
P=B/'video-r10-play1';record=json.loads(bind(P/'record.json').read_text());assert len(record['screenshots'])==5
view=D/'facts-layout/play1';view.mkdir(parents=True,exist_ok=True)
for shot in record['screenshots']:
 f=P/Path(shot['path']).name;bind(f);assert sha(f)==shot['sha256'] and shot['captured']
 shutil.copyfile(f,view/f.name);shot['path']=f.name
(view/'record.json').write_text(json.dumps(record,indent=2)+'\n')
for name in ['child-before.stat','child-after.stat']:
 f=bind(P/name);s=f.read_text();fields=s.split(') ',1)[1].split();assert int(s.split()[0])==7080 and fields[0]!='Z' and int(fields[1])==5160 and int(fields[19])==9491
raw=bind(P/'child-full.stderr');rawsha=sha(raw);lines=raw.read_text(errors='replace').splitlines();base=record['stderr_baseline_lines']
mirrors=[(i+1,s) for i,s in enumerate(lines) if '[WL-TTLOG ' in s]
selected=[68026,68027,68033,69593,69778,69799,69801,69832,69833,69864,69865,69869,69895,69896,156125,270126]
ex=[]
for n in selected:
 s=lines[n-1];assert '[WL-TTLOG ' in s and not re.search(r'https?://|token|authorization|/Users/',s,re.I)
 ex.append(str(n)+': '+s)
(D/'decoder-render-excerpt.txt').write_text('\n'.join(ex)+'\n')
feed=bind(B/'video-r10-live/settled-guardian/screen.jpeg');shutil.copyfile(feed,D/'initial-feed.jpeg');bind(B/'video-r10-live/settled-guardian/step-0.txt')
res={'token':'video-2020-r10-live-review','status':'CHECKPOINT_NOT_WINDOW_CLOSE','identity':identity,'logger_two_hops':'MATCHED','network_get_free_pair':'MATCHED','reader_object_sha_inode_and_maps':'BEFORE_AFTER_EQUAL_FOR_RELEVANT_OBJECTS','child_before_after_stat':'S_SAME_BIRTH_PPID','full_stderr_sha256':rawsha,'full_stderr_lines':len(lines),'captured_mirror_markers':sum(s.count('[WL-TTLOG ') for s in lines),'captured_mirror_lines':len(mirrors),'baseline_lines':base,'post_baseline_mirror_lines':sum(i>base for i,s in mirrors),'attempt_cap':4096,'attempt_counter':'NOT_READ','exhaustion':'NOT_ESTABLISHED: captured count is below cap; formatting/write losses can consume reservations','window_lock_failure_lines':sum('Unable to lock window buffer' in s for i,s in mirrors),'first_hw_failure_line':68026,'bytevc_created_line':69778,'video_opened_line':69801,'frame_parameter_line':69832,'first_lock_failure_line':69895,'visual':'Initial feed confirmed. t0/t20/t25 independently viewed; all five shots show the same woman cover with play triangle. No demonstrated video motion. Other shot bytes match those viewed.','playback':'NOT_PASSED','audio':'UNKNOWN','causal_limit':'Decoder open/712x360 output parameter and render attempts follow hardware failure; no terminal whole-codec failure established. ret -19 is not yet attributed to a provider. Initialization precedes tap baseline. first-frame message does not prove display.','rollback':'PENDING_NEW_EVIDENCE','device_calls':0}
(D/'results.json').write_text(json.dumps(res,indent=2)+'\n');(D/'private-source-index.json').write_text(json.dumps(refs,indent=2)+'\n')
assert sha(raw)==rawsha,'source changed during review'
r=subprocess.run([sys.executable,str(ROOT/'scripts/lab/run_facts.py'),str(D/'facts-layout')],capture_output=True)
(D/'facts.txt').write_bytes(r.stdout);assert r.returncode==0
print(json.dumps(res,indent=2));print(r.stdout.decode())
