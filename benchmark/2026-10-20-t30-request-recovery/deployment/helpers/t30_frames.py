from pathlib import Path
import subprocess,time,json,sys
from window_paths import HELPERS,WINDOW,context,budget,tag
base=HELPERS;w=WINDOW;c=context();tag(sys.argv[1]);out=w/sys.argv[1];out.mkdir(exist_ok=False);start=time.monotonic();deadline=start+budget(c);r=[]
for offset in [0,5,10,20]:
 time.sleep(max(0,start+offset-time.monotonic()));assert time.monotonic()<deadline
 x=subprocess.run([sys.executable,str(base/'t30_outer.py'),'capture','candidate',sys.argv[2]],capture_output=True,timeout=min(20,deadline-time.monotonic()));(out/(str(offset)+'.stdout')).write_bytes(x.stdout);(out/(str(offset)+'.stderr')).write_bytes(x.stderr);r.append(dict(offset=offset,rc=x.returncode,elapsed=time.monotonic()-start));(out/'result.json').write_text(json.dumps(r,indent=2));assert x.returncode==0
(out/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
