"""Restart a verified deployment with empty or identical snapshotted data."""
from run25 import *
mode,kind,rep=sys.argv[1:4]
origin=R/'offline-fresh-1'
d=json.loads((origin/'device-report.json').read_text())
runtime=d['runtime'];rows=[json.loads(l) for l in (origin/'commands.jsonl').read_text().splitlines()]
r=R/f'{mode}-{kind}-{rep}'
assert not r.exists()
# Require no living child/parent for this deployment before clearing/restoring data.
refs=dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120)
assert not refs.strip(), 'Live deployment namespace remains: '+refs
network(mode=='offline')
try:
 dev(f'cd {runtime} && rm -rf app-data data webview-t-data',120)
 if kind=='fresh':
  dev(f'mkdir -p {runtime}/data/dalvik-cache/arm64 {runtime}/app-data/{PKG}/code_cache/art-volatile {runtime}/app-data/{PKG}/app_webview {runtime}/app-data/org.westlake.imehost {runtime}/webview-t-data && chown -R {UID}:{UID} {runtime}/data {runtime}/app-data {runtime}/webview-t-data && chcon -R u:object_r:data_app_el2_file:s0 {runtime}/app-data/{PKG}')
  provenance={'fresh':True,'cleared':['app-data','data','webview-t-data']}
 else:
  meta=json.loads((R/'reuse-seed.json').read_text());seedpath='/data/local/tmp/pkg28-reuse-seed.tar'
  assert dev('sha256sum '+seedpath).split()[0]==meta['sha256']
  dev(f'cd {runtime} && tar -xf {seedpath} && chcon -R u:object_r:data_app_el2_file:s0 {runtime}/app-data/{PKG}',180)
  provenance=meta
 # Remove the old socket path so readiness implies the new listener.
 dev('rm -f '+d['socket'])
 c=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
 parent=int(dev(c).strip())
 for _ in range(120):
  if 'READY' in dev('if [ -S '+d['socket']+' ]; then echo READY; fi'):break
  time.sleep(.25)
 else:raise RuntimeError('Parent not ready')
 r,d2=launch(r.name,origin);d2['parent']=parent
 (r/'device-report.json').write_text(json.dumps(d2,indent=2));(r/'data-provenance.json').write_text(json.dumps(provenance,indent=2))
 (r/'network-start.txt').write_text(dev('iptables -nvxL OUTPUT; ip6tables -nvxL OUTPUT; ifconfig wlan0'))
 print('LAUNCHED',r.name,d2['child'],flush=True)
 try:
  measure(r,d2,kind=='fresh')
 finally:
  collect(r,d2);stop(d2)
finally:network(False)
