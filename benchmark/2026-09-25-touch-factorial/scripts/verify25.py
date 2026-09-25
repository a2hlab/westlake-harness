"""Read-only evidence verification; no board access."""
import pathlib,json,gzip,hashlib,re
E=pathlib.Path(__file__).resolve().parents[1]/'evidence'
manifest=json.loads((E/'files.json').read_text())
for item in manifest:
 b=(E/item['file']).read_bytes();assert hashlib.sha256(b).hexdigest()==item['stored_sha256'],item['file']
 raw=gzip.decompress(b) if item['gzip'] else b
 assert len(raw)==item['raw_bytes'] and hashlib.sha256(raw).hexdigest()==item['raw_sha256'],item['file']
rows={r['run']:r for r in json.loads((E/'summary.json').read_text())}
names=['offline-fresh-3','offline-fresh-4','online-fresh-1','online-fresh-2','offline-seeded-1','offline-seeded-2','online-seeded-1','online-seeded-2']
seed=json.loads((E/'reuse-seed.json').read_text())
base=None
for name in names:
 r=rows[name];assert [t['action'] for t in r['touches']]==[0,1],name
 assert not r['unconsumed_posts'],name
 report=json.loads((E/name/'device-report.json').read_text())
 assert report['uid']==20010053 and report['runtime_env']==['WL_TOUCH_TRACE=1'],name
 if base is None:base=report['source_files']
 assert report['source_files']==base,name
 assert r['ui_stacks'],name
 source=gzip.open(E/name/'child.stderr.gz','rt',errors='replace').read().splitlines()
 dump_start=next(i for i,l in enumerate(source,1) if l.startswith('----- pid '))
 assert max(t['run_line'] for t in r['touches'])<dump_start,name+' SIGQUIT overlaps measurement'
 for t in r['touches']:
  assert t['latency_ms']==t['run_ms']-t['post_ms'] and t['latency_ms']>=0
  assert '[TOUCH21] post action=' in source[t['post_line']-1]
  assert '[TOUCH21] run action=' in source[t['run_line']-1]
 if 'seeded' in name:
  provenance=json.loads((E/name/'data-provenance.json').read_text())
  assert provenance['sha256']==seed['sha256'] and provenance['regular_files_verified']==236,name
 net=(E/name/'network-start.txt').read_text()
 assert (net.count('owner UID match 20010053 /* touch25 */')==2)==name.startswith('offline'),name
 assert 'inet addr:192.168.0.109' in net,name
print(f'PASS: {len(manifest)} artifact hashes/gzip round trips; 8 trials, 16 trace pairs, same runtime/seed, UID rules; all baseline dumps follow touch consumption')
