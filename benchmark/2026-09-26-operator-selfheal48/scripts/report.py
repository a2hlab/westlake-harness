"""Describe observations; UI reviews remain explicit and are never inferred from substring hits."""
from pathlib import Path
import json,re
R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/selfheal48'
events=(R/'board-archive/events.log').read_text(); actions=[json.loads(s) for s in (R/'validation/actions.jsonl').read_text().splitlines()]
rows={}
for l in events.splitlines():
 m=re.search(r'^(\d+) START seq=(\d+) child=(\d+) parent=(\d+)',l)
 if m: rows[int(m[2])]=dict(seq=int(m[2]),child=int(m[3]),parent=int(m[4]),start_uptime=int(m[1]))
 m=re.search(r'^(\d+) READY seq=(\d+)',l)
 if m:rows[int(m[2])]['ready_uptime']=int(m[1])
 m=re.search(r'^(\d+) EXIT seq=(\d+) pid=\d+ elapsed=(\d+) reason=(\S+)',l)
 if m:rows[int(m[2])].update(exit_uptime=int(m[1]),observed_seconds=int(m[3]),exit_reason=m[4])
for a in actions:
 if a['op'] in ('kill-test','crash-test'):
  seq=int(a['instance']['seq']);t=float(a['output'].split()[0]);rows[seq]['manual_kill_uptime']=t;rows[seq]['manual_trigger']=a['op']
  nextrow=rows.get(seq+1,{})
  if 'ready_uptime' in nextrow:nextrow['from_manual_kill_to_ready_seconds']=round(nextrow['ready_uptime']-t,2)
metrics=[]
for l in (R/'board-archive/metrics.log').read_text().splitlines():
 m=re.match(r'(\d+) seq=(\d+).*apps=(\d+) parents=(\d+) rss_kib=(\d*) available_kib=(\d+)',l)
 if m:metrics.append(dict(uptime=int(m[1]),seq=int(m[2]),apps=int(m[3]),parents=int(m[4]),rss_kib=int(m[5]) if m[5] else None,available_kib=int(m[6])))
for seq,row in rows.items():
 samples=[m for m in metrics if m['seq']==seq]
 if samples:row['samples']=len(samples);row['max_apps']=max(m['apps'] for m in samples);row['max_parents']=max(m['parents'] for m in samples);row['available_kib_range']=[min(m['available_kib'] for m in samples),max(m['available_kib'] for m in samples)]
 if seq<=4:row['classification']='invalid guardian-revision1 abort; not application crash'
 elif seq==6:row['classification']='feed visible but revision2 false-negative; manually stopped for fix'
 else:row['classification']='see forced-kill/live evidence; not a no-guardian reliability trial'
result={'rounds':list(rows.values()),'clean_events':[l for l in events.splitlines() if ' CLEANED ' in l], 'limitations':['READY timestamps have one-second resolution and are sampled pixel-gate events, not first-pixel latency','initial stale recovery_s is excluded; recovery uses explicit kill action uptime','ppid1 cleanup count includes expected detached appspawn parent, not just orphan applications','revision2 RSS fields empty; use proc/status audit or revision3 metrics','two article classes verified manually against saved body screenshots and anchored lifecycle records']}
(R/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
