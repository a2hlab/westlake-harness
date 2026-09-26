"""Summarize the five formal rounds without pooling the mixed preliminary round."""
from pathlib import Path
import json
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/npthpatch48'
rows=[]
for n in range(1,6):
 d=r/f'pure-r{n}';j=json.loads((d/'strict-review.json').read_text());s=json.loads((d/'summary.json').read_text())
 hashes=dict(line.split(None,1)[::-1] for line in (d/'component-hashes.txt').read_text().splitlines())
 assert any(v.startswith('85c789f4') for k,v in hashes.items() if k.endswith('/libwebview_bionic_shim.so'))
 assert any(v.startswith('4f7cc3a6') for k,v in hashes.items() if k.endswith('/libnpth.so'))
 if rows:assert hashes==rows[0]['component_hashes']
 row={k:j[k] for k in ['round','child','parent','observed_seconds','last_alive_sample_s','stability_pass','parent_exit_one','npth_mapping_pass','ule_lines','body_pass','feed_pass','native_sig11_snapshots','uncaught']}
 row.update(detail_entry=s['detail_entry'],detail_resumed=s['detail_resumed'],click_to_resumed_s=s['click_to_resumed_s'],component_hashes=hashes)
 rows.append(row)
summary=dict(formal_count=5,stability_pass_count=sum(j['stability_pass'] for j in rows),body_lifecycle_pass_count=sum(j['body_pass'] and j['detail_entry'] and bool(j['detail_resumed']) for j in rows),npth_mapping_pass_count=sum(j['npth_mapping_pass'] for j in rows),ule_rounds=sum(bool(j['ule_lines']) for j in rows),exit1_rounds=sum(j['parent_exit_one'] for j in rows),rounds=rows)
summary['acceptance_pass']=summary['stability_pass_count']==5 and summary['body_lifecycle_pass_count']>=3 and summary['npth_mapping_pass_count']==5 and summary['ule_rounds']==summary['exit1_rounds']==0
(r/'acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print({k:v for k,v in summary.items() if k!='rounds'})
