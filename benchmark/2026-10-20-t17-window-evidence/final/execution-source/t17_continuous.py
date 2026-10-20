from pathlib import Path
import json,time,subprocess,sys
base=Path(__file__).parent;out=base/'t17-5cd-window-01';c=json.loads((out/'context.json').read_text())
for i in range(3):
 assert time.time()-c['start']<1200
 a=[sys.executable,str(base/'t17_outer.py'),'capture','5807db3d-32f6-4d16-a98a-0baad7352fb9'];r=subprocess.run(a,capture_output=True,timeout=25);(out/f'continuous-{i}.stdout').write_bytes(r.stdout);(out/f'continuous-{i}.stderr').write_bytes(r.stderr);(out/f'continuous-{i}.rc').write_text(str(r.returncode));print(r.stdout.decode(),flush=True);assert r.returncode==0
 if i<2:time.sleep(5)
