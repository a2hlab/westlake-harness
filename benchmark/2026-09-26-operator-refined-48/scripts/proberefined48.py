"""Read-only stage probe bound to the original child; optional screenshot."""
from boardrefined48 import *
name,label=sys.argv[1:3];assert re.fullmatch(r'[a-z0-9-]+',name+label)
r=R/name;d=json.loads((r/'device-report.json').read_text());pid=d['child']
recv(d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr',r/(label+'.stderr'))
s=(r/(label+'.stderr')).read_text(errors='replace')
state=dev(f'cat /proc/uptime; cat /proc/{pid}/stat; grep libmetasec /proc/{pid}/maps; sha256sum {d["runtime"]}/app-data/{PKG}/app_lib/libmetasec_ml.so')
(r/(label+'-state.txt')).write_text(state)
print('ORIGINAL_ALIVE',live(pid,d['birth']));print(state[:1800]);print('\n'.join(l for l in s.splitlines() if any(x in l for x in ('[UNCAUGHT]','Fatal signal','symbol not found','[B47-SLA] ENTRY','[ABILITY38-RESUMED]')))[-4000:])
shot(r,label)
