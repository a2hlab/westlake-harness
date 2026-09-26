from pathlib import Path
import sys,json
name,label=sys.argv[1:3];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
j=json.loads((x['r']/'instance.json').read_text());pid=j['child'];log=x['rt']+'/private-tmp/adapter_child_'+str(pid)+'.stderr'
cmd="cat /proc/uptime; grep -E '^\\[B47-SLA\\] ENTRY|^\\[ABILITY38-RESUMED\\]|DEGENERATE|Layout: -79|J_invokeStaticMain_main_threw|^Fatal signal|^\\[CM-EXIT\\]' "+log+" | tail -35"
s=x['dev'](cmd,8);(x['r']/(label+'-clamp.txt')).write_text(s);print(s)
