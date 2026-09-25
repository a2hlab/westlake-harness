"""VM-only #46 max_map_count experiment, raw 10-second samples and CSV."""
from board34 import *
import csv
cmd,name=sys.argv[1:3];r=R/name
if cmd=='configure':
 r.mkdir(exist_ok=True)
 before=dev('cat /proc/uptime; cat /proc/sys/vm/max_map_count; cat /proc/sys/vm/overcommit_memory; cat /proc/meminfo')
 (r/'sysctl-before.txt').write_text(before)
 (r/'sysctl-change.txt').write_text(dev('echo 1048576 > /proc/sys/vm/max_map_count; cat /proc/sys/vm/max_map_count'))
 assert dev('cat /proc/sys/vm/max_map_count').strip()=='1048576'
elif cmd=='sample':
 d=json.loads((r/'device-report.json').read_text());pid=str(d['child'])
 while not (r/'stop-maps').exists():
  raw=dev('echo UPTIME; cat /proc/uptime; echo MAPS; wc -l /proc/'+pid+'/maps; echo STATUS; cat /proc/'+pid+'/status; echo CGROUP; cat /proc/'+pid+'/cgroup; echo MEMORY; cat /proc/meminfo; echo LIMIT; cat /proc/sys/vm/max_map_count; echo STAT; cat /proc/'+pid+'/stat')
  with (r/'maps-samples.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'raw':raw})+'\n')
  if not re.search(r'^Pid:\s*'+pid+r'$',raw,re.M):break
  time.sleep(10)
 print('SAMPLER_DONE',flush=True)
elif cmd=='report':
 rows=[]
 for line in (r/'maps-samples.jsonl').read_text().splitlines():
  a=json.loads(line);s=a['raw']
  def number(pattern):
   m=re.search(pattern,s,re.M);return int(m[1]) if m else None
  rows.append({'uptime':float(re.search(r'UPTIME\n([\d.]+)',s)[1]),'maps':number(r'MAPS\n(\d+)'),'rss_kib':number(r'^VmRSS:\s*(\d+)'),'swap_kib':number(r'^VmSwap:\s*(\d+)'),'mem_available_kib':number(r'^MemAvailable:\s*(\d+)'),'limit':number(r'LIMIT\n(\d+)')})
 with (r/'maps-curve.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 print(json.dumps({'samples':len(rows),'first':rows[0],'last':rows[-1],'max_maps':max(x['maps'] or 0 for x in rows),'peak_rss_kib':max(x['rss_kib'] or 0 for x in rows)},indent=2))
