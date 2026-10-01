"""Stop only apps owned by this interrupted smoke run before strict rollback."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if (p/'scripts/lab/u7_executor.py').exists());sys.path.insert(0,str(R/'scripts/lab'))
import u7_executor as u
out=H/'board5cd-a118aca0-r2/recovery-stop';io=u.DeviceIO('5cd1e3dd00000000000000000923012c','cx-t0',out)
rows=[]
for pkg in ['com.ath0.rpn','org.linaro.glmark2','anupam.acrylic']:
 text=io.shell('bm dump -n '+pkg)
 if 'uid' not in text:rows.append({'package':pkg,'not_installed':True});continue
 data=io.b.parse_bundle(text,pkg);dst=out/pkg;dst.mkdir(parents=True,exist_ok=True)
 stopped=io.b.cold_stop(io.board,pkg,data['uid'],dst,'recovery-stop')
 rows.append({'package':pkg,'uid':data['uid'],'stopped':stopped})
 if not stopped:raise RuntimeError('smoke child did not stop: '+pkg)
(out/'result.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
