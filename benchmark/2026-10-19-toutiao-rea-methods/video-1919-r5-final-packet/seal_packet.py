#!/usr/bin/env python3
"""Freeze this evidence delivery after offline checks; never runs device tools."""
from pathlib import Path
import hashlib,json,re,subprocess
F=Path(__file__).resolve().parent; R=next(p for p in F.parents if (p/'scripts/lab/run_facts.py').is_file());M=R.parent/'westlake-harness';B=F.parent;P=B/'video-1919-r5-live-review';U=B/'video-1919-r5-review';G=B/'video-1919-review-generator-archive';A=R/'benchmark/2026-10-19-api-progress-update'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def w(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert not (F/'freeze.json').exists()
checks=json.loads((F/'checks.json').read_text());assert checks['first_four_objects_unchanged']
# Every public copy of a raw shell result has an actual transport and remote result.
verified=[]
for sub in ['apply','rollback','restored-identity','parameter-restored']:
 for p in (P/sub/'commands').glob('*.json'):
  d=json.loads(p.read_text());assert d['exit_code']==0
  text=p.with_suffix('.stdout.txt').read_text();assert re.search(r'__BMS_REMOTE_RC_[a-f0-9]+__0',text),p
  verified.append(str(p.relative_to(R)))
for line in (G/'SHA256SUMS').read_text().splitlines():
 digest,path=line.split(None,1); p=R/path.strip()
 if not p.exists():p=G/path.strip()
 assert h(p)==digest,p
checks['raw_command_triplets_verified']=len(verified);w(F/'checks.json',checks)
facts=(P/'facts.txt').read_text();assert 'screenshots_captured=8/8' in facts and 'alive_unknown=8' in facts
(F/'README.md').write_text('''# R5 final packet\n\nDiagnostic evidence accepted; playback NOT_OBSERVED. Three exits occurred before video tap. The parameter was set/read true, but player consumption was not observed. Audio remains unknown. Exact original files, parameter error106 after freshboot, unchanged snapshot labels/config/SELinux, restored feed and canonical UNLOCK are bound. First restored baseline child exited; second icon restored a news list with a gray video card, not video playback.\n\n## Landing\n\nUse landing-paths.txt from this producer worktree, verify SHA256SUMS and freeze.json, then review the four canonical API successor files. The first4 row objects remain exactly equal to MAIN input; the signed315 table and source15 are not included. Three public metadata files from MAIN are included unchanged at video-1919-r5-review. No private large raw log, full crash or tar is included; public archive receipt pins the remote1949217-byte archive. No runtime, device or build tool was executed by the reviewer.\n\nThe separate review-generator archive preserves earlier useful scripts; it is not a replay instruction. finalize.py and seal_packet.py record this offline assembly. Draft api-preview and api-row5.draft.json are excluded from landing because they were superseded, not rewritten into final evidence. Historical execution sources are recipes for the original guarded window only. Renderer stdout/stderr and checks.json document the original consumer run and links/CSV checks. Root may integrate this exact narrow list; do not copy unrelated dirty files.\n''')
(F/'ACK.md').write_text('video-1919-r5-final-packet\n\nScoped ACCEPT: diagnostic P1 NOT_OBSERVED; no consumer true or audio claim. Restoration/feed/parameter106 and UNLOCK verified. API5 preserves the first4 objects and historical315; no new verified API grade. No device calls, builds, staging retry or push. SOURCE15 already MAIN and excluded.\n\n'+facts+'\nAPI: 5 rows / 68 exact references (10+10+12+19+17), 71 HTML links resolved; CSV all fields match.\n')
# Preserve original archive recipe privately; publish an explicitly labelled portable derivative.
orig=P/'historical-recipes/archive_video_r5.py'
text=orig.read_text(); line=next(x for x in text.splitlines() if ";remote=" in x)
portable=text.replace('import hashlib,json,subprocess,tarfile,shlex','import hashlib,json,subprocess,tarfile,shlex,os').replace(line,line.split(';remote=')[0]+";remote=os.environ['HW248_ARTIFACT_ROOT'].rstrip('/')+'/toutiao-video-r5-20261019'")
portable='# Portable archival derivative, NOT the byte-exact executed original. See archive-recipe-provenance.json.\n'+portable
(P/'historical-recipes/archive_video_r5.portable.py').write_text(portable)
w(P/'historical-recipes/archive-recipe-provenance.json',{'original_sha256':h(orig),'original_archive_member':'archive_video_r5.py','original_remote_archive_sha256':'998a94b131c6174ff2bd4e2a56ea4513f03c42a5e9859db9299202c0d7bda23e','public_derivative_sha256':h(P/'historical-recipes/archive_video_r5.portable.py'),'change':'Only replace private remote root with required HW248_ARTIFACT_ROOT environment variable, add os import and explicit derivative header. Not executed.'})
pins=json.loads((P/'source-pins.json').read_text())
if not pins.get('command_index_summary'):
 command_rows=[x for x in pins['files'] if '/commands/' in x['path']]
 pins['files']=[x for x in pins['files'] if '/commands/' not in x['path']]
 pins['command_index_summary']={'file_count':len(command_rows),'sorted_rows_json_sha256':hashlib.sha256(json.dumps(sorted(command_rows,key=lambda x:x['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),'encoding':'JSON sorted by path, sort_keys=True, separators=(comma,colon), UTF-8','scope':'All original command triplets remain in the verified raw archive. Public selected triplets are additionally pinned in delivery SHA256SUMS.'}
 w(P/'source-pins.json',pins)
exclude={'api-row5.draft.json','archive_video_r5.py'}
paths=[p for p in P.rglob('*') if p.is_file() and 'api-preview' not in p.parts and p.name not in exclude and '__pycache__' not in p.parts]
paths += [p for p in U.iterdir() if p.is_file()]
paths += [R/line for line in (G/'landing-paths.txt').read_text().splitlines()]
paths += [A/n for n in ['observations.json','observations.csv','index.html','results.json']]
paths += [p for p in F.iterdir() if p.is_file() and p.name not in ['landing-paths.txt','SHA256SUMS','freeze.json','path-gate.stdout.txt','path-gate.stderr.txt','path-gate.json']]
paths=sorted(set(paths)); assert all(p.is_file() and not p.is_symlink() for p in paths)
for p in paths:
 if p.suffix not in ['.jpeg','.png']:
  data=p.read_bytes();assert not re.search(rb'/(?:Users|home)/[A-Za-z0-9_.-]+/',data),p
 assert p.stat().st_size<1000000,(p,p.stat().st_size)
run=subprocess.run(['python3',str(M/'scripts/lab/check_user_paths.py'),'--root',str(R),*[str(p.relative_to(R)) for p in paths]],capture_output=True,text=True)
(F/'path-gate.stdout.txt').write_text(run.stdout);(F/'path-gate.stderr.txt').write_text(run.stderr);assert run.returncode==0,run.stdout+run.stderr
w(F/'path-gate.json',{'rc':run.returncode,'tool_sha256':h(M/'scripts/lab/check_user_paths.py'),'scope':'exact payload list','files':len(paths)})
paths += [F/n for n in ['path-gate.stdout.txt','path-gate.stderr.txt','path-gate.json']]
paths=sorted(set(paths)); controls=[F/n for n in ['landing-paths.txt','SHA256SUMS','freeze.json']]
landing=sorted(paths+controls);(F/'landing-paths.txt').write_text(''.join(str(p.relative_to(R))+'\n' for p in landing))
(F/'SHA256SUMS').write_text(''.join(h(p)+'  '+str(p.relative_to(R))+'\n' for p in paths))
w(F/'freeze.json',{'token':'video-1919-r5-final-packet','status':'FROZEN_EVIDENCE_NOT_PLAYBACK_ACCEPTANCE','payload_count':len(paths),'landing_count':len(landing),'landing_sha256':h(F/'landing-paths.txt'),'sha_manifest_sha256':h(F/'SHA256SUMS'),'api_rows':5,'api_references':68,'new_row_references':17,'html_links':71,'previous_four_objects_unchanged':True,'historical315_changed':False,'remote_archive_sha256':'998a94b131c6174ff2bd4e2a56ea4513f03c42a5e9859db9299202c0d7bda23e','source15_redelivered':False,'facts_total':facts.strip().splitlines()[-1]})
print(json.dumps({'freeze_sha256':h(F/'freeze.json'),'landing_sha256':h(F/'landing-paths.txt'),'sums_sha256':h(F/'SHA256SUMS'),'files':len(landing),'payload':len(paths)},indent=2))
