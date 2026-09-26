from pathlib import Path
import sys,json
name=sys.argv[1];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
r=x['r'];j=json.loads((r/'instance.json').read_text());pid=j['child'];rt=x['rt'];dev=x['dev'];st=x['state'](pid)
assert st and st['alive'] and st['birth']==j['birth']
paths=[f'/proc/{pid}/root/data/local/tmp/asx/lib/arm64-v8a/{n}' for n in ['libbytehook.so','libshadowhook.so']]
s=dev('cat /proc/uptime; sha256sum '+' '.join(paths)+'; stat -c "%i %s %n" '+' '.join(paths)+'; grep -E "libbytehook.so|libshadowhook.so" /proc/'+str(pid)+'/maps',10)
(r/'live-engine-identity.txt').write_text(s);print(s)
