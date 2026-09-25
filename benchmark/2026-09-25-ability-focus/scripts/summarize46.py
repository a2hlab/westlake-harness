"""Derive bounded survival and npth CPU evidence from raw observation files."""
from board34 import *
name=sys.argv[1];r=R/name;result={}
for p in sorted(r.glob('*-input.txt')):
 label=p.name.removesuffix('-input.txt');raw=p.read_text()
 before=float(re.search(r'INPUT_BEFORE\n(\d+\.\d+)',raw)[1])
 actions=[json.loads(x) for x in (r/(label+'-actions.jsonl')).read_text().splitlines()]
 live=[];dead=[]
 for a in actions:
  if '/stat' not in a['command']:continue
  uptime=float(a['output'].split()[0])
  (live if ') ' in a['output'] else dead).append(uptime)
 groups={};taskfile=r/(label+'-task-stats.jsonl')
 if taskfile.exists():
  for line in taskfile.read_text().splitlines():
   rec=json.loads(line)
   for s in rec['tasks'].splitlines():
    m=re.match(r'(\d+) \((.*)\) (.*)',s)
    if not m or 'npth' not in m[2].lower():continue
    v=m[3].split();key=m[1]+':'+v[19]
    groups.setdefault(key,[]).append({'time':rec['epoch'],'comm':m[2],'state':v[0],'ticks':int(v[11])+int(v[12])})
 cpu={k:{'comm':a[0]['comm'],'observations':len(a),'seconds':a[-1]['time']-a[0]['time'],'cpu_ticks_delta':a[-1]['ticks']-a[0]['ticks'],'states':sorted(set(x['state'] for x in a))} for k,a in groups.items()}
 result[label]={'input_before_uptime':before,'last_alive_after_seconds':max(live)-before if live else None,'first_absent_after_seconds':min(dead)-before if dead else None,'npth':cpu}
(r/'observation-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
