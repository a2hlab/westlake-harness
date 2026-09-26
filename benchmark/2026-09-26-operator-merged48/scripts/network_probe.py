from pathlib import Path
import sys
name=sys.argv[1];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
s=x['dev']('date; cat /proc/uptime; ip route; ping -c 2 -W 2 223.5.5.5; ping -c 2 -W 2 www.toutiao.com',15)
(x['r']/'network-probe.txt').write_text(s);print(s)
