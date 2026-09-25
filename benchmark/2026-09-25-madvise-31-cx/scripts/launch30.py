from common30 import *
BASE=['libvision_core.so','libc++_shared.so','libsscronet.so']
IMAGE=['libbdheif.so','libttheif_dec.so','libgifimage.so']
def launch(name,variant,app='toutiao'):
 r=R/name
 assert not r.exists(),r
 targets=BASE.copy() if app=='toutiao' else []
 if variant=='images':targets+=IMAGE
 elif variant=='full':targets+=json.loads((pathlib.Path(__file__).parents[1]/'targets.json').read_text())['additional_targets']
 elif variant not in ('baseline','candidate'):raise ValueError(variant)
 cmd=['python3',str(A/'out-madvise31-cx/probe-local/tools/probe_source_app.py'),'--workspace',str(A),'--westlake-source',str(A/'westlake-touch21'),'--framework-report',str(R/'framework/device-report.json') if variant=='candidate' else str(R.parent/'integrate-14/framework/device-report.json'),'--app-input',str(pathlib.Path.home()/'a2hlab/app-inputs'/app),'--app',app,'--hdc',H,'--serial',S,'--out',str(r),'--host-build',str(A/'out/signed-host'),'--webview-input',str(A/'out/webview-input-source'),'--source-webview-build',str(A/'out-sp20/webview-candidate'),'--runtime-env','WL_TOUCH_TRACE=1']
 for t in sorted(set(targets)):cmd+=['--android-native-target',t]
 if app=='toutiao':cmd+=['--android-native-net-target','libsscronet.so']
 with (R/(name+'.driver.log')).open('w') as f:subprocess.run(cmd,cwd=pathlib.Path.home()/'a2hlab/manifest',stdout=f,stderr=subprocess.STDOUT,check=True)
 d=json.loads((r/'device-report.json').read_text())
 (r/'launch-config.json').write_text(json.dumps({'variant':variant,'argv':cmd,'native_targets':sorted(set(targets)),'net_targets':['libsscronet.so'] if app=='toutiao' else []},indent=2))
 return r,d
def restart(name,origin):
 r=R/name;old=R/origin;assert not r.exists();r.mkdir()
 d=json.loads((old/'device-report.json').read_text());runtime=d['runtime']
 assert not dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120).strip()
 dev(f'cd {runtime} && rm -rf app-data data webview-t-data',120)
 dev(f'mkdir -p {runtime}/data/dalvik-cache/arm64 {runtime}/app-data/{PKG}/code_cache/art-volatile {runtime}/app-data/{PKG}/app_webview {runtime}/app-data/org.westlake.imehost {runtime}/webview-t-data && chown -R {UID}:{UID} {runtime}/data {runtime}/app-data {runtime}/webview-t-data && chcon -R u:object_r:data_app_el2_file:s0 {runtime}/app-data/{PKG}')
 rows=[json.loads(s) for s in (old/'commands.jsonl').read_text().splitlines()]
 dev('rm -f '+d['socket'])
 c=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
 d['parent']=int(dev(c).strip())
 for _ in range(120):
  if 'READY' in dev('if [ -S '+d['socket']+' ]; then echo READY; fi'):break
  time.sleep(.25)
 else:raise RuntimeError('Parent not ready')
 c=next(x['command'] for x in rows if '/host_spawn /dev/unix' in x['command'])
 d['child']=int(re.search(r'result=0 pid=(\d+)',dev(c))[1])
 box=f'/proc/{d["child"]}/root/data/local/tmp/noice_tap.{d["child"]}'
 dev(f': > {box}; chown {UID}:{UID} {box}; chmod 666 {box}; ln -sf {box} /data/local/tmp/noice_tap')
 (r/'device-report.json').write_text(json.dumps(d,indent=2));(r/'commands.jsonl').write_bytes((old/'commands.jsonl').read_bytes());(r/'launch-config.json').write_bytes((old/'launch-config.json').read_bytes())
 (r/'data-provenance.json').write_text(json.dumps({'fresh':True,'origin':origin,'cleared':['app-data','data','webview-t-data']},indent=2))
 return r,d
