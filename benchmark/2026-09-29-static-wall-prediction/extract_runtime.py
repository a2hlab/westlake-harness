#!/usr/bin/env python3
import json,re,subprocess,tempfile,zipfile
from pathlib import Path
from scan_jni import PACKAGES,R8,HERE,DEXDUMP,sha
classes=['adapter.activity.LocalServiceBinders','adapter.activity.B8BindExtras','adapter.activity.UserManagerProjectionProxy','adapter.core.OHServiceManager','android.os.OHServiceManager','android.app.SystemServiceRegistry','adapter.activity.AppSchedulerBridge','adapter.activity.ManifestJsonFallback']
seen={};out=[]
for name,package in PACKAGES.items():
 for jar in list((package/'payload/android/framework').glob('*.jar'))+[R8]:
  if jar.name=='oh-adapter-runtime.jar' and jar!=R8:continue
  h=sha(jar)
  if h in seen:continue
  seen[h]=str(jar)
  with zipfile.ZipFile(jar) as z,tempfile.TemporaryDirectory(prefix='b10-runtime-') as td:
   for entry in z.namelist():
    if not re.fullmatch(r'classes\d*\.dex',entry):continue
    p=Path(td)/entry;p.write_bytes(z.read(entry))
    proc=subprocess.Popen([str(DEXDUMP),'-d',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
    selected=False;method=''
    for lineno,line in enumerate(proc.stdout,1):
     m=re.search(r'\|\[[0-9a-f]+\] (.+)',line)
     if m:
      method=m[1];selected=any(method.startswith(c+'.') for c in classes) or 'OHServiceManager.' in method
     if selected and '|' in line:out.append({'jar':str(jar),'jar_sha256':h,'dex':entry,'line':lineno,'method':method,'text':line.rstrip()})
    err=proc.stderr.read()
    if proc.wait():raise RuntimeError(err)
  print(jar.name,len(out),flush=True)
(HERE/'evidence/runtime-disassembly.json').write_text(json.dumps(out,indent=2)+'\n')
