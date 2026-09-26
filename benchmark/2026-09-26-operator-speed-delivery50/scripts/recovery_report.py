from pathlib import Path
import json,re
R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/speed-delivery50'
events=(R/'board-archive/events.log').read_text().splitlines();actions=[json.loads(l) for l in (R/'validation/actions.jsonl').read_text().splitlines()]
rows=[]
for a in actions:
 if a['op'] not in ('kill-test','crash-test'):continue
 up=float(a['output'].split()[0]);seq=int(a['instance']['seq']);matches=[]
 for l in events:
  if ' READY ' in l and int(re.search(r'seq=(\d+)',l)[1])>seq and float(l.split()[0])>up:matches.append(l)
 row={'action':a,'first_ready':matches[0] if matches else None}
 if matches:row['seconds_to_ready_log']=round(float(matches[0].split()[0])-up,2)
 rows.append(row)
(R/'recovery-summary.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
