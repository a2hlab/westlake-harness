"""VM: summarize raw observation windows without treating a replacement PID as survival."""
from board45 import *

summaries=[]
for name in sys.argv[1:]:
    folder=R/name
    expected=json.loads((folder/'device-report.json').read_text())['child']
    rows=[json.loads(s) for s in (folder/'stability.jsonl').read_text().splitlines()]
    points=[]
    for row in rows:
        lines=row['output'].splitlines()
        stat=next((s for s in lines if s.startswith(str(expected)+' (')),None)
        fields=stat.rsplit(') ',1)[1].split() if stat else []
        maps=re.search(r'^(\d+) /proc/'+str(expected)+r'/maps$',row['output'],re.M)
        rss=re.search(r'^VmRSS:\s+(\d+) kB',row['output'],re.M)
        points.append(dict(elapsed=row['elapsed'],uptime=float(lines[0].split()[0]),
                           current=int(lines[1]),state=fields[0] if fields else None,
                           birth=fields[19] if fields else None,
                           maps=int(maps[1]) if maps else None,rss_kib=int(rss[1]) if rss else None,
                           sequence=lines[-1]))
    valid=all(p['current']==expected and p['state'] not in (None,'Z') for p in points)
    valid=valid and len({p['birth'] for p in points})==1 and len({p['sequence'] for p in points})==1
    text=(folder/'child.stderr').read_text(errors='replace')
    keys=['GLES library translated','GrGLInterface creation failed','InitializeGL failure',
          'getOwnCodecInfo No implementation','UnsatisfiedLinkError','Fatal signal',
          'SQLiteException','SQLiteDatabaseCorruptException']
    summary=dict(name=name,pid=expected,same_live_instance=valid,
                 duration=points[-1]['uptime']-points[0]['uptime'],samples=len(points),
                 markers={k:text.count(k) for k in keys},points=points)
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    summaries.append({k:v for k,v in summary.items() if k!='points'})
print(json.dumps(summaries,indent=2))
