from pathlib import Path
import sys,json
name=sys.argv[1];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
j=json.loads((x['r']/'instance.json').read_text());pid=str(j['child']);log=x['rt']+'/private-tmp/adapter_child_'+pid+'.stderr'
s=x["dev"]("cat /proc/uptime; grep -E 'SOURCE-NATIVE-LOAD.*(npth|jato)|WESTLAKE-LOADER|ABILITY38-RESUMED|BEFORE scheduleTransaction|AFTER executeTransaction|UNCAUGHT|CM-EXIT' "+log+" | tail -70",8);(x["r"]/"loader-probe.txt").write_text(s);print(s[-14000:])
