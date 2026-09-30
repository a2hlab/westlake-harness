#!/usr/bin/env python3
"""Audit every declared ELF and reject stale manifests or removed exports."""
from pathlib import Path
import hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent
base=R.parent/'westlake-generation-n1-aa57845c';pkg=R.parent/'westlake-generation-n2-candidate'
nm='/opt/homebrew/opt/llvm/bin/llvm-nm';readelf='/opt/homebrew/opt/llvm/bin/llvm-readelf'
def elf(f):
 if not f.exists():return None
 exports=subprocess.check_output([nm,'-D','--defined-only',str(f)],text=True)
 dynamic=subprocess.check_output([readelf,'-d',str(f)],text=True)
 return {'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'needed':re.findall(r'\(NEEDED\).*?\[(.*?)\]',dynamic),'exports':sorted({x.split()[-1] for x in exports.splitlines() if x.split()})}
rows=[]
for row in json.loads((P/'package-changes.json').read_text()):
 before=elf(base/row['file']);after=elf(pkg/row['file']);assert after['sha256']==row['sha256']
 removed=sorted(set(before['exports'] if before else [])-set(after['exports']))
 rows.append({'file':row['file'],'before':before,'after':after,'removed_exports':removed});assert not removed,removed
(P/'elf-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
obj=R/'bms/src/.work/n2-native/runtime-objects/android_media_AudioSystemCapabilities.o'
syms=subprocess.check_output([nm,'-C',str(obj)],text=True)
assert 'newAudioSessionId' in syms
(P/'audio-session-symbols.txt').write_text(syms)
print('PASS 7 ELFs, no removed exports, exact AudioCapabilities has newAudioSessionId')
