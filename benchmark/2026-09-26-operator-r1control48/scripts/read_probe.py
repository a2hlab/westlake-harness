"""Bounded, read-only board diagnostics; never starts or replaces the test child."""
from pathlib import Path
import sys,json
name,label,cmd=sys.argv[1:4];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
s=x['dev'](cmd,15);(x['r']/(label+'.txt')).write_text(s);print(s)
