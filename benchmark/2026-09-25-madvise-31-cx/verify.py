from pathlib import Path
import gzip,json,hashlib,subprocess,sys
from analyze_trace import analyze
root=Path(__file__).resolve().parent
repo=Path(subprocess.check_output(['git','-C',str(root),'rev-parse','--show-toplevel'],text=True).strip())
for item in json.loads((root/'manifest.json').read_text()):
 p=root/item['path'];data=p.read_bytes();assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],p
 if '--git' in sys.argv:assert subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+str(p.relative_to(repo))])==data,p
for row in json.loads((root/'results.json').read_text()):
 p=root/'evidence'/row['run'];raw=gzip.decompress((p/'child.stderr.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==row['stderr_sha256'];lines=raw.decode(errors='replace').splitlines()
 for key in ('fatal','uncaught','ui_failure'):
  for hit in row[key]:assert lines[hit['line']-1]==hit['text']
 for role,old in row['trace'].items():
  with gzip.open(p/'threads.trace.gz','rt') as f:new=analyze(f,old['tid'],old['window_begin'])
  assert new['intervals']==[tuple(x) for x in old['intervals']]
  assert new['D_seconds']==old['D_seconds'] and not new['missing_wakeup_fallbacks']
  if row['measurement_complete']:assert new['trace_time_range'][0]<=old['window_begin'] and new['trace_time_range'][1]>=old['window_end']
  if row['measurement_complete']:assert old['unclosed_D_start'] is None or old['unclosed_D_start']>=old['window_end']
print('PASS evidence hashes, exact stderr lines, D intervals recomputed from scheduler events')

visual=json.loads((root/'visual-review.json').read_text())
for name,screen in json.loads((root/'screen-times.json').read_text()).items():
 events=json.loads((root/'evidence'/name/'events.json').read_text());shots={e['name']:e for e in events if e['kind']=='frame'}
 a=shots[visual[name]['last_host']];b=shots[visual[name]['first_feed']]
 assert screen['last_host_capture']==[a['lower'],a['upper']]
 assert screen['first_feed_capture']==[b['lower'],b['upper']]
 assert screen['appearance_bracket']==[a['lower'],b['upper']]
print('PASS screen timing arithmetic')
