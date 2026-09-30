#!/usr/bin/env python3
"""Device receipts are evidence; screenshot verdict stays human reviewed."""
from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parent
mode=sys.argv[1]
def data(p):return json.loads((R/p).read_text())
if mode=='baseline':
 x=data('before/identity.json');assert x['verified'] and x['actual']==x['expected']
 assert x['runtime_fingerprint']=='0b81cdbe0ed9'
 assert data('jar/original.json')['boot_id']==x['boot_id']
 assert data('jar/original.json')['sha256'].startswith('75c2068c')
 assert data('dry-run.json')['device_io'] is False
 assert '0 violation(s)' in (R/'frozen.txt').read_text()
 assert '现在可以开 N3 短窗' in (R/'authorization.txt').read_text()
elif mode=='evidence':
 d=data('results.json');assert d['device_status'] not in ['unverified','running']
 assert d.get('candidate_deployed') is True, 'N3 never deployed; baseline evidence is not candidate evidence'
 for run in d['runs']:
  p=R/run;assert (p/'facts.txt').is_file() and (p/'runtime-fingerprint.txt').is_file()
  for f in p.glob('*/record.json'):
   row=json.loads(f.read_text())
   for shot in row.get('screenshots',[]):
    if shot.get('captured'):
     image=f.parent/Path(shot['path']).name
     assert image.is_file() and hashlib.sha256(image.read_bytes()).hexdigest()==shot['sha256']
 assert (R/'visual-review.json').is_file()
 assert d['first_fatal_summary'] and d['comparison_reports']
elif mode=='restored':
 before=data('before/identity.json');after=data('final/identity.json');window=data('window.json')
 assert after['verified'] and after['runtime_fingerprint']=='0b81cdbe0ed9'
 assert before['actual']==after['actual'] and before['boot_id']==after['boot_id']
 assert (R/'unlock.txt').read_text().strip()=='holder-gone'
 assert window['finished_epoch']-window['started_epoch']<=2700
else:raise ValueError(mode)
print('PASS N3 device',mode)
