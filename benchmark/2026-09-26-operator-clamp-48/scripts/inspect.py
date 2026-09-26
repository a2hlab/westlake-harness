import sys,json
from pathlib import Path
name,label=sys.argv[1:3]
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
j=json.loads((x['r']/'instance.json').read_text());log=x['rt']+'/private-tmp/adapter_child_'+str(j['child'])+'.stderr'
s=x['dev']("cat /proc/uptime; grep -E '^\\[B47-SLA\\] ENTRY|^\\[ABILITY38-START\\]|^\\[ABILITY38-RESUMED\\]|^\\[UNCAUGHT\\]|^\\[WESTLAKE-LOADER\\] refusing' "+log+' | tail -25',5)
(x['r']/(label+'-log.txt')).write_text(s);print(s[:10000])
