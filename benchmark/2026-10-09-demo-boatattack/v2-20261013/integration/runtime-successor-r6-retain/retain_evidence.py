"""Check actual original HW/ZZ output; no visual acceptance is synthesized."""
import hashlib,json,os
from pathlib import Path
SERIAL='5ea34a4500000000000000001123012c'
RUNTIME='f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0'
def need(ok,msg):
 if not ok:raise ValueError(msg)
def resolve(p):return Path(os.path.expandvars(str(p))).resolve()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def pin(p):
 p=resolve(p);ws=resolve(os.environ['WORKSPACES'])
 return dict(path='$WORKSPACES/'+str(p.relative_to(ws)),sha256=sha(p))
def smoke(path,spec,started,runtime=RUNTIME):
 path=resolve(path);d=read(path)
 need(path.stat().st_mtime>=started and d.get('passed') is True and d.get('serial')==SERIAL and resolve(d.get('spec',''))==resolve(spec),'fresh actual HW/ZZ result')
 need(d.get('checks') and all(x.get('ok') is True for x in d['checks']),'all smoke predicates')
 need({x.get('key') for x in d['checks'] if x.get('check')=='controls' and x.get('alive_t20')=='yes'}=={'helloworld','zigzag'},'both t20 controls')
 need(d['probe']['view']['/system/android/lib64/liboh_android_runtime.so']==runtime,'actual f28 child view/runtime pin')
 return d
