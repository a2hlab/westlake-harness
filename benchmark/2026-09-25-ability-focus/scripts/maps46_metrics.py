"""VM: derive resource ranges for each physically recorded observation window."""
from board34 import *
import csv
r=R/sys.argv[1];rows=list(csv.DictReader((r/'maps-curve.csv').open()))
v=[{'uptime':float(a['uptime']),'maps':int(a['maps']),'rss_mib':int(a['rss_kib'])/1024} for a in rows if a['maps'] and a['rss_kib']]
windows={}
for p in sorted(r.glob('*-input.txt')):
 label=p.name.removesuffix('-input.txt');t=float(re.search(r'INPUT_BEFORE\n([\d.]+)',p.read_text())[1])
 actions=[json.loads(a) for a in (r/(label+'-actions.jsonl')).read_text().splitlines()]
 live=[float(a['output'].split()[0]) for a in actions if '/stat' in a['command'] and ') ' in a['output']]
 if not live:continue
 end=max(live);a=[x for x in v if t<=x['uptime']<=end]
 windows[label]={'input_uptime':t,'last_alive_after_s':end-t,'samples':len(a),'first':a[0] if a else None,'last':a[-1] if a else None,'max_maps':max((x['maps'] for x in a),default=None),'peak_rss_mib':max((x['rss_mib'] for x in a),default=None)}
tail=[x for x in v if x['uptime']>=v[-1]['uptime']-120]
dt=tail[-1]['uptime']-tail[0]['uptime']
result={'sample_count':len(v),'first':v[0],'last':v[-1],'span_s':v[-1]['uptime']-v[0]['uptime'],'max_maps':max(x['maps'] for x in v),'exceeded_old_65530':any(x['maps']>65530 for x in v),'peak_rss_mib':max(x['rss_mib'] for x in v),'last_120s_endpoint_rss_mib_per_min':(tail[-1]['rss_mib']-tail[0]['rss_mib'])/dt*60 if dt else None,'windows':windows}
(r/'resource-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
