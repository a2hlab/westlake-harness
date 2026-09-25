"""Offline hash and measurement recomputation; does not connect to any board."""
import collections,gzip,hashlib,json,re,tempfile
from pathlib import Path
from analyze_device import analyze
root=Path(__file__).resolve().parent
manifest=json.loads((root/'device-evidence-manifest.json').read_text())
results=json.loads((root/'device-results.json').read_text())
assert len(results['formal_order'])==9 and len(set(results['formal_order']))==9
with tempfile.TemporaryDirectory(prefix='aot42-verify-') as tmp:
 tmp=Path(tmp)
 for item in manifest:
  raw=(root/'device-evidence'/item['path']).read_bytes()
  assert hashlib.sha256(raw).hexdigest()==item['stored_sha256'],item['path']
  data=gzip.decompress(raw) if item['gzip'] else raw
  assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],item['path']
  target=tmp/item['original'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 for row in results['rows']:
  actual=analyze(tmp/row['name'])
  for key,value in actual.items():assert row[key]==value,(row['name'],key)
  if row['formal_included']:
   assert row['name'] in results['formal_order']
   assert any('killed by signal 11' in x for x in row['parent_reap'])
   if row['touch_uptime']:
    assert 60<=row['last_consent_to_touch_s']<61
    assert len([x for x in row['article_events'] if x['action']=='DOWN'])==1
    assert len(row['detail_lifecycle'])==1
    t=row['touch_uptime'][0]
    bounds=[round(float(row['detail_observations'][0][k].split()[0])-t,3) for k in ['previous_poll','observed']]
    assert bounds==row['entry_poll_bounds_s']
    resumed=[round(int(re.search(r'uptime=(\d+)',x['text'])[1])/1000-t,3) for x in row['activity_times'] if 'RESUMED' in x['text'] and int(re.search(r'uptime=(\d+)',x['text'])[1])>t*1000]
    assert resumed==row['post_click_resumed_s']
   # Every downloaded stderr was re-read after the child ended and compared to device SHA.
   assert (tmp/row['name']/'stderr-sha256.txt').read_text().strip()==hashlib.sha256((tmp/row['name']/'child.stderr').read_bytes()).hexdigest()
 formal=[x for x in results['rows'] if x['formal_included']]
 assert collections.Counter(x['arm'] for x in formal)=={'baseline':3,'verify':3,'speed':3}
 assert collections.Counter(x['arm'] for x in formal if x['touch_uptime'])=={'baseline':3,'speed':2}
 assert all(not x['faults'] for x in formal),'Update crash classification if late reports appear'
 for arm in ('verify','speed'):
  samples=[x for x in formal if x['arm']==arm]
  assert all(x['app_image_loads'] and x['oat_maps'] for x in samples)
  assert all(any(' r-xp ' in m for m in x['oat_maps'])==(arm=='speed') for x in samples)
 print(f"PASS: {len(manifest)} evidence hashes; {len(results['rows'])} trials recomputed; formal 3/3/3 attempts, 3/0/2 clicks; 9 SIGSEGV exits")
