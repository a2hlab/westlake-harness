"""Offline evidence/parameter verification only; never a deployment admission."""
import hashlib,json
from pathlib import Path
b=Path(__file__).resolve().parent
h=lambda x:hashlib.sha256(x).hexdigest()
p=json.loads((b/'parameters.json').read_text());e=json.loads((b/'evidence-index.json').read_text())
assert p['status']=='DISABLED_STATIC_PLAN_NOT_ADMISSION' and p['approved_by'] is None
assert p['serial']=='5cd1e3dd00000000000000000923012c' and p['uid']==20011300
assert p['cfg_sha256']=='19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152'
assert len(p['artifacts'])==4 and p['device_calls']==p['builds']==p['runtime_writes']==0
assert h((b/'run5cd.before.reference.sh').read_bytes())==p['run_derivation']['before_sha256']=='5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79'
assert h((b/'run5cd.after.wid29.reference.sh').read_bytes())==p['run_derivation']['after_wid29_reference_sha256']
assert p['run_derivation']['wid29_is_current_admission'] is False
for name in ['run5cd.before.reference.sh','run5cd.after.wid29.reference.sh']:
 data=(b/name).read_bytes();assert data.count(b'ASX_RUNTIME_OWNER_UID=20011300\n')==1
 assert b'20011206' not in data and data.count(b'WL_PARENT_ID=29\n')==1
assert len(e['excerpts'])==5
for row in e['excerpts']:
 raw=(b/'evidence'/Path(row['path']).name).read_bytes()
 assert h(raw)==row['sha256'] and len(raw)==row['length']
 assert row['source_byte_offset']==row['selected_byte_offset']+26377929
 assert len(raw)<1000 and b'http' not in raw.lower() and b'{' not in raw
assert b'SL_IID_ANDROIDSIMPLEBUFFERQUEUE: symbol not found' in (b/'evidence/01-player-iid.txt').read_bytes()
print('OFFLINE_EVIDENCE_PARAMETERS_OK; device_calls=0; execution/human acceptance=pending_review')
