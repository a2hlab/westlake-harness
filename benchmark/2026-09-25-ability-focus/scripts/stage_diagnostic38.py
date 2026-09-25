from board34 import *
import hashlib
base=R/'framework-candidate/device-report.json'
d=json.loads(base.read_text());old=d['stage'];assert old.endswith('ability38-v3')
(base.parent/'v3-report.json').write_bytes(base.read_bytes())
output=R/'framework-candidate';output.mkdir(exist_ok=True)
stage='/data/local/tmp/a2hlab-framework-ability38-v4'
assert old != stage
state=dev(f'if [ -e {stage} ]; then echo EXISTS; else cp -a {old} {stage} && echo COPIED; fi',240)
assert 'COPIED' in state,state
build=pathlib.Path.home()/'a2hlab/ws/out-ability38/inputtrace'
files=[('fw/adapter-runtime-bcp.jar',build/'adapter-runtime-bcp.jar')]+[('boot/'+p.name,p) for p in sorted((build/'boot').glob('boot*')) if p.is_file()]
files += [('liboh_android_runtime.so',pathlib.Path.home()/'a2hlab/ws/out-ability38/native-trace/liboh_android_runtime.so')]
changes={}
for name,p in files:
 subprocess.run([H,'-t',S,'file','send',str(p),stage+'/'+name],check=True,timeout=120,stdout=subprocess.DEVNULL)
 entry={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 assert dev('sha256sum '+stage+'/'+name).split()[0]==entry['sha256']
 changes[name]={'before':d['files'].get(name),'after':entry};d['files'][name]=entry
cmd=d['device_command'].replace(old,stage)
log=dev(cmd+' 2>&1; echo PRELOAD_RC=$?',120);(output/'preload-v4.log').write_text(log)
assert 'PRELOAD_RC=0' in log,log[-4000:]
d.update(stage=stage,device_command=cmd,device_log_sha256=hashlib.sha256(log.encode()).hexdigest(),passed=True)
d['ability38_trace_overlay']={'base_report':str(base),'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'changes':changes}
(output/'device-report.json').write_text(json.dumps(d,indent=2)+'\n');print('STAGED',stage,len(changes),flush=True)
