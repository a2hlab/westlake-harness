from board34 import *
# Read only faults whose PID and timestamp match an owned run.
paths=dev('find /data/log/faultlog -type f -name "cppcrash-*"',120).splitlines()
for r in R.iterdir():
 if not r.is_dir() or not (r/'device-report.json').exists() or not (r/'actions.jsonl').exists():continue
 d=json.loads((r/'device-report.json').read_text());pid=d.get('child')
 if not pid:continue
 rows=list(map(json.loads,(r/'actions.jsonl').read_text().splitlines()));times=[x['epoch'] for x in rows if 'epoch' in x]
 if not times:continue
 for f in paths:
  m=re.search(r'cppcrash-(\d+)-(\d+)$',f)
  if not m or int(m[1])!=pid or not min(times)-30<=int(m[2])/1000<=max(times)+120:continue
  if not (r/pathlib.Path(f).name).exists():recv(f,r/pathlib.Path(f).name);print('LATE_FAULT',r.name,f)
