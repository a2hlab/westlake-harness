from pathlib import Path
import json
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/hollow48'
rows=[]
for i in range(1,6):
 d=r/('final-r'+str(i));j=json.loads((d/'strict-review.json').read_text());s=json.loads((d/'summary.json').read_text());e=json.loads((d/'crash-events.json').read_text()) if (d/'crash-events.json').exists() else []
 rows.append(dict(round=d.name,child=j['child'],parent=j['parent'],seconds=j['observed_seconds'],stable=j['stability_pass'],article=bool(j['body_pass'] and s['detail_resumed']),feed=j['feed_pass'],mapping=j['combo_mapping'],ule=len(j['ule_lines']),exit_one=j['parent_exit_one'],r3=any(x['addresses'].get('pc',{}).get('elf_vaddr')=='0xd6e20' for x in e),r5=any(x['thread']=='npth-worker' and x['addresses'].get('pc',{}).get('elf_vaddr')=='0x111974' for x in e),faults=[dict(thread=x['thread'],signal=x['signal'],pc=x['addresses'].get('pc'),event=x['event']) for x in e],latency=s['click_to_resumed_s'],fatal_headers=s['fatal_headers'],main_exception=s['main_exception'],npth_worker_samples=[f.name for f in d.glob("*-threads.txt") if "npth-worker" in f.read_text()]))
passed=all(x['stable'] and all(x['mapping'].values()) and not x['ule'] and not x['exit_one'] for x in rows) and sum(x['article'] for x in rows)>=3
out=dict(rows=rows,stable=sum(x['stable'] for x in rows),articles=sum(x['article'] for x in rows),acceptance_pass=passed)
(r/'final-acceptance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
