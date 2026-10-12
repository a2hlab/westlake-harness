"""Record manual before/after image review; never contacts a device."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[2];M=ROOT.parent/'westlake-harness';BASE=M/'benchmark/2026-10-12-v1-seal-execution/game-interactions';OUT=Path(__file__).parent
p=argparse.ArgumentParser();p.add_argument('key');p.add_argument('status');p.add_argument('attempt');p.add_argument('detail');a=p.parse_args();attempt=BASE/a.key/a.attempt
rec=attempt/'record.json';d=json.loads(rec.read_text());assert d['boot_id']=='9f5af7c8-d359-4c25-99c6-63206b50cf0a'
def ref(f):return {'path':f.relative_to(M).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
row={'key':a.key,'status':a.status,'detail':a.detail,'boot_id':d['boot_id'],'control':d.get('control'),'record':ref(rec),'before':ref(attempt/'before.jpeg') if (attempt/'before.jpeg').exists() else None,'after':ref(attempt/'screen.jpeg'),'review':'actual images independently viewed by cx-t0; no seal signature','causality':'Temporal before/after only; no unsupported crash-cause claim.'}
f=OUT/'interactions.json';r=json.loads(f.read_text()) if f.exists() else {'schema':1,'scope':10,'rows':[]};r['rows']=[x for x in r['rows'] if x['key']!=a.key]+[row];f.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');print(a.key,a.status)
