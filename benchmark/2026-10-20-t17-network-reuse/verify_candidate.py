import hashlib,json
from pathlib import Path
b=Path(__file__).resolve().parent;r=json.loads((b/'results.json').read_text())
a=(b/'run5cd.r8.reference.sh').read_bytes();z=(b/'run5cd.r9.reference.sh').read_bytes()
assert hashlib.sha256(a).hexdigest()==r['r8_5cd_run_sha256'];assert hashlib.sha256(z).hexdigest()==r['r9_5cd_run_wid29_sha256']
changes=[(x,y) for x,y in zip(a.splitlines(),z.splitlines()) if x!=y];assert len(changes)==2 and len(a.splitlines())==len(z.splitlines())
assert changes[0]==(b'export WESTLAKE_ANDROID_NATIVE_NET_TARGETS=libsscronet.so',b'export WESTLAKE_ANDROID_NATIVE_NET_TARGETS=libsscronet.so:libmffmpeg.so')
assert changes[1][1]==changes[1][0]+b':libandroid_native_network_compat.so'
assert b'ASX_RUNTIME_OWNER_UID=20011300\n' in z and b'WL_PARENT_ID=29\n' in z
assert r['builds']==r['device_calls']==r['changed_runtime_binaries_from_r8']==0
for e in json.loads((b/'evidence-index.json').read_text())['excerpts']:
 raw=(b/'evidence'/Path(e['path']).name).read_bytes();assert hashlib.sha256(raw).hexdigest()==e['sha256'] and len(raw)==e['bytes']
print('EXACT_CONFIG_REUSE_OK; device_calls=0; actual5cd_binding=UNKNOWN; playback=NOT_PASSED')
