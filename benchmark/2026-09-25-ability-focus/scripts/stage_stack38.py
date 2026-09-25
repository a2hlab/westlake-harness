from board34 import *
import hashlib
out=R/'framework-candidate';d=json.loads((out/'device-report.json').read_text());old=d['stage'];assert old.endswith('ability38-v5')
(out/'v5-report.json').write_text(json.dumps(d,indent=2))
stage='/data/local/tmp/a2hlab-framework-ability38-v6';assert 'COPIED' in dev(f'if [ -e {stage} ]; then echo EXISTS; else cp -a {old} {stage} && echo COPIED; fi',120)
p=pathlib.Path.home()/'a2hlab/ws/out-ability38/native-stack/liboh_adapter_bridge.so';subprocess.run([H,'-t',S,'file','send',str(p),stage+'/'+p.name],check=True)
sha=hashlib.sha256(p.read_bytes()).hexdigest();assert dev('sha256sum '+stage+'/'+p.name).split()[0]==sha
d['files'][p.name]={'sha256':sha,'bytes':p.stat().st_size};cmd=d['device_command'].replace(old,stage);log=dev(cmd+' 2>&1; echo PRELOAD_RC=$?',120)
(out/'preload-v6.log').write_text(log);assert 'PRELOAD_RC=0' in log,log[-4000:]
d.update(stage=stage,device_command=cmd,device_log_sha256=hashlib.sha256(log.encode()).hexdigest());d['ability38_policy']={'base':old,'sha256':sha}
(out/'device-report.json').write_text(json.dumps(d,indent=2)+'\n');print('STAGED',stage,sha)
