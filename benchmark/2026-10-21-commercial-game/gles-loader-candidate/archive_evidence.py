#!/usr/bin/env python3
"""Create and member-verify a local source/raw/artifact archive; never uploads."""
import json, tarfile, io
from pathlib import Path
from prepare_inputs import HERE, REPO, sha, save

def main():
 out=HERE/'.private/archive-01';out.mkdir(exist_ok=False)
 files=[p for p in sorted(HERE.rglob('*')) if p.is_file() and out not in p.parents and '__pycache__' not in p.parts and p.name not in {'archive-receipt.json','landing-paths.txt','SHA256SUMS'}]
 files.append(REPO/'tools/spec-checks/tests/commercial_game_gles_loader_candidate.rs')
 members=[{'path':str(p.relative_to(REPO)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]
 blob=(json.dumps(members,indent=2)+'\n').encode();target=out/'g18-gles-loader-candidate.tar.gz'
 with tarfile.open(target,'w:gz') as tar:
  for p,item in zip(files,members):tar.add(p,arcname=item['path'],recursive=False)
  entry=tarfile.TarInfo('ARCHIVE-MANIFEST.json');entry.size=len(blob);tar.addfile(entry,io.BytesIO(blob))
 import hashlib
 with tarfile.open(target,'r:gz') as tar:
  require={r['path']:r for r in members};seen=set()
  for member in tar:
   if member.name=='ARCHIVE-MANIFEST.json':continue
   row=require[member.name];data=tar.extractfile(member).read();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];seen.add(member.name)
  assert seen==set(require)
 save(HERE/'archive-receipt.json',{'status':'LOCAL_ARCHIVE_MEMBER_VERIFIED_REMOTE_PENDING','archive':'$G18/.private/archive-01/'+target.name,'sha256':sha(target),'bytes':target.stat().st_size,'payload_members':len(members),'total_members':len(members)+1,'member_index_sha256':hashlib.sha256(blob).hexdigest(),'remote_verified':False,'contains_original_build_stdout_stderr':True,'contains_artifacts_sources_helpers_and_pinned_header_library_inputs':True,'sdk_tool_binaries_included':False})
 print(sha(target),target.stat().st_size,'bytes',len(members),'verified payload members')
if __name__=='__main__':main()
