"""Offline evidence integrity and A/B identity checks; no device access."""
import hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent
e=r/'evidence';result=json.loads((r/'results.json').read_text())
assert result['serial']=='5ea34a4500000000000000001123012c'
assert len(result['trials'])==2
before=(e/'identity-before.txt').read_text().splitlines()
after=(e/'identity-after.txt').read_text().splitlines()
assert before[:5]==after[:5]
assert before[0]==result['boot_id']
for t in result['trials']:
 assert t['serial']==result['serial'] and t['boot_id']==result['boot_id'] and t['clicked']
 d=e/t['key']
 times=[float(x.split()[1]) for x in (d/'timeline.txt').read_text().splitlines() if x.startswith('T ')]
 assert len(times)==t['samples'] and times[-1]-times[0]>=15
 assert t['new_faults']==[]
 for n in ['bundle.txt','hilog.txt','hilog-clear.txt','faults-before.txt','faults-after.txt','record.json','t1.jpeg','final.jpeg']:
  assert (d/n).is_file(),n
wiki=(e/'wikipedia/hilog.txt').read_text()
assert 'AppSpawnChild id 27' in wiki and 'SetSandboxProperty failed, org.wikipedia' in wiki
assert 'NotifyResToParent:218103816' in wiki and 'pid 26163 exit with code:0' in wiki
for a in json.loads((r/'manifest.json').read_text()):
 p=(r/a['path']).resolve();assert p.is_relative_to(r)
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],str(p)
print('Same 5ea boot/runtime, two >=15s traces, failure evidence and all artifact hashes verified')
