"""Read-only check: one actual mapping instance, not merely one pathname."""
from pathlib import Path
import json,sys
p=Path(sys.argv[1]);gen=sys.argv[2]
text=p.read_text();names=['libart.so','libopenjdkjvm.so','libjavacore.so','libopenjdk.so'];found={n:[] for n in names}
for line in text.splitlines():
 f=line.split()
 if len(f)<6:continue
 n=Path(f[-1]).name
 if n in found and int(f[2],16)==0:found[n].append({'address':f[0],'path':f[-1]})
prefix='/system/lib64/westlake/route-a/'+gen+'/'
ok=all(len(found[n])==1 and found[n][0]['path']==prefix+n for n in names[:2])
report={'passed':ok,'maps':str(p),'offset_zero_instances':found,'required_generation':gen}
print(json.dumps(report,indent=2));sys.exit(0 if ok else 1)
