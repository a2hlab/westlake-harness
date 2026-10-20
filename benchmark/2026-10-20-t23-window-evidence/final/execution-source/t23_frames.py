from pathlib import Path
import subprocess,time,json,sys
base=Path(__file__).parent;w=base/'t23-5cd-window-01';c=json.loads((w/'context.json').read_text());out=w/sys.argv[1];out.mkdir(exist_ok=False);start=time.monotonic();r=[]
for offset in [0,5,10,20]:
 time.sleep(max(0,start+offset-time.monotonic()));assert time.time()-c['start']<1150
 x=subprocess.run([sys.executable,str(base/'t23_outer.py'),'capture','af001b38-659a-4f1f-9dd7-b85960587a2c'],capture_output=True,timeout=20);(out/(str(offset)+'.stdout')).write_bytes(x.stdout);(out/(str(offset)+'.stderr')).write_bytes(x.stderr);r.append(dict(offset=offset,rc=x.returncode,elapsed=time.monotonic()-start));assert x.returncode==0
(out/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
