"""Close the rejected read-only attempt with exact U8 identities; no board writes."""
import json,os,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=Path(os.environ.get('WORKSPACES',R.parent))
sys.path.insert(0,str(R/'scripts/lab'));import u7_executor as u
plan=u.prepare(W/'westlake-generation-n11b-ref-u8-163da805',W/'westlake-generation-u8-j9-t7e/native')
io=u.DeviceIO('61b0657200000000000000000324012c','cx-t0',H/'window-r1/board61b/readonly-final-device')
got,absent=io.snapshot(sorted(plan['baseline']))
diff={p:{'expected':v,'actual':got.get(p)} for p,v in plan['baseline'].items() if got.get(p)!=v}
record={'status':'U8 verified without candidate apply','identity_count':len(got),'boot_id':io.boot,'diff':diff,'absent':absent,'fingerprints':u.fingerprints(got,plan['reference_paths']),'device_writes':False}
(H/'window-r1/board61b/no-write-final-u8.json').write_text(json.dumps(record,indent=2)+'\n')
assert not diff and not absent and len(got)==312
print('U8 all312 exact; no writes; lock can be released')
