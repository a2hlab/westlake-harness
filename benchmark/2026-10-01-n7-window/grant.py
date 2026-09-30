"""Materialize outer ACK(90) 04:15:59 for this one locked window."""
import datetime,json
from pathlib import Path
H=Path(__file__).resolve().parent
proposal=json.loads((H.parent/'2026-10-01-n7-native/exception-proposal.json').read_text())
now=datetime.datetime.now().astimezone();rows=[]
for entry in proposal['entries']:
 rows.append({**{k:entry[k] for k in ['gate','issue_id','package_manifest_sha256','inputs_sha256','reason','evidence','removal_condition']},'approved_by':'outer(claude)','approved_at':'2026-10-01T04:15:59+08:00'})
assert len(rows)==185
out=dict(schema_version=1,serial='61b0657200000000000000000324012c',package_manifest_sha256='a77c7c6cfdc1c0f78a9f32dad2c184dabe049afedc9674774bd578fab1ab67ff',issued_at=now.isoformat(),expires_at=(now+datetime.timedelta(minutes=29,seconds=30)).isoformat(),status='active',exceptions=rows)
assert not (H/'window.json').exists(),'one use only'
(H/'window.json').write_text(json.dumps(out,indent=2)+'\n');print(out['expires_at'])
