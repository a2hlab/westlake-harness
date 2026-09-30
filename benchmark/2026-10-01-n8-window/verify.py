"""Evidence integrity only; human screenshots decide rendering."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
r=json.loads((H/'results.json').read_text());s=json.loads((H/'supervisor-result.json').read_text());f=json.loads((H/'final-receipt.json').read_text())
assert s['u5_restored'] and s['unlocked'] and s['overrun_seconds']==0
assert f['fingerprint']=='73ecf422dba2' and f['boot_image_fingerprint']=='0876029078e2'
assert f['live_sha256'].startswith('2488052f')
assert json.loads((H/'window.json').read_text())['status']=='revoked'
assert r['r2']=='partially_verified' and r['unknown']
for row in json.loads((H/'visual-reviews.json').read_text()):
 p=H/'evidence'/row['run']/row['key'];record=json.loads((p/'record.json').read_text())
 assert (p/'t20.jpeg').exists()
 assert any(s.get('captured') and s.get('scheduled_seconds')==20 for s in record['screenshots'])
assert 'batch_interrupted' in (H/'facts-all.txt').read_text()
print('evidence integrity PASS; visual verdict pending outer review')
