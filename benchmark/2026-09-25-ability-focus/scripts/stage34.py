from board34 import *
import hashlib
base=R.parent/'touch25/framework-wake/device-report.json'
d=json.loads(base.read_text());old=d['stage']
out=R/'framework-candidate';out.mkdir(exist_ok=True)
stage='/data/local/tmp/a2hlab-framework-focus34-v6'
assert old != stage
print(dev(f'if [ -e {stage} ]; then echo EXISTS; else cp -a {old} {stage} && echo COPIED; fi',240))
changes={}
for name in ['libwestlake_input_transport.so','liboh_adapter_bridge.so','liboh_android_runtime.so']:
 p=pathlib.Path.home()/'a2hlab/ws/out-focus34/incremental'/name
 subprocess.run([H,'-t',S,'file','send',str(p),stage+'/'+name],check=True,timeout=120)
 entry={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 actual=dev('sha256sum '+stage+'/'+name).split()[0];assert actual==entry['sha256']
 changes[name]={'before':d['files'].get(name),'after':entry};d['files'][name]=entry
cmd=d['device_command'].replace(old,stage)
log=dev(cmd+' 2>&1; echo PRELOAD_RC=$?',120);(out/'preload.log').write_text(log)
assert 'PRELOAD_RC=0' in log,log[-4000:]
d.update(stage=stage,device_command=cmd,device_log_sha256=hashlib.sha256(log.encode()).hexdigest(),passed=True)
d['focus34_overlay']={'base_report':str(base),'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'changes':changes}
(out/'device-report.json').write_text(json.dumps(d,indent=2)+'\n')
print('STAGED',stage,changes)
