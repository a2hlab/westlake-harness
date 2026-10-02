"""Read-only bounded-depth window status, never descend diagnostic fault trees."""
from pathlib import Path
import json,time,datetime
H=Path(__file__).resolve().parent;W=H.parents[3]
for board,d in [('5ea',H),('5cd',H),('61b',H.parent/'window2-61b')]:
 p=json.loads((d/f'plan-{board}.json').read_text());out=Path(p['out'].replace('$WORKSPACES',str(W)));root=out.parent
 result=out/'board-run-result.json';smoke=out/'smoke/smoke-result.json';finish=root/'finish.json'
 phase='apply' if (out/'after-lock.log').exists() else 'waiting'
 if (out/'smoke').is_dir():phase='activation-smoke'
 if smoke.exists():phase='shards';s=json.loads(smoke.read_text());phase+=' smoke='+str(s.get('passed',s.get('status',s.get('verdict'))))
 if (out/'before-unlock.log').exists():phase='restore'
 if result.exists():phase='ended '+str(json.loads(result.read_text()).get('before_unlock'))
 records=[]
 for f in out.glob('*/*/*/*/record.json'):
  r=json.loads(f.read_text());records.append({'key':f.parent.name,'status':r.get('status'),'finished':bool(r.get('finished_at'))})
 aux=list((out/'additional').glob('*/*/*/*/record.json'))
 print(json.dumps({'board':board,'phase':phase,'main_records':len(records),'wrapped':sum(x['finished'] for x in records),'latest':records[-2:],'aux_records':len(aux),'finish':json.loads(finish.read_text()) if finish.exists() else None},ensure_ascii=False))
