from common34 import *
import hashlib
old=R/'cold-a1';new=R/'mainstack-v7-base';new.mkdir()
d=json.loads((old/'device-report.json').read_text());runtime=d['runtime']
assert not dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120).strip()
p=pathlib.Path.home()/'a2hlab/ws/out-ability38/native-stack/liboh_adapter_bridge.so'
sha=hashlib.sha256(p.read_bytes()).hexdigest();before=dev('sha256sum '+runtime+'/'+p.name).split()[0]
subprocess.run([H,'-t',S,'file','send',str(p),runtime+'/'+p.name],check=True)
assert dev('sha256sum '+runtime+'/'+p.name).split()[0]==sha
f=R/'framework-candidate/device-report.json';fw=json.loads(f.read_text());assert fw['stage'].endswith('ability38-v7')
assert fw['files'][p.name]['sha256']==sha
for key in d['source_files']:
 if key==p.name:d['source_files'][key]={'bytes':p.stat().st_size,'sha256':sha}
d['framework_report_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
d['ability38_runtime_overlay']={'source':str(p),'before_sha256':before,'after_sha256':sha,'no_process_namespace_live':True,'framework_stage':fw['stage']}
(new/'device-report.json').write_text(json.dumps(d,indent=2))
for name in ('commands.jsonl','launch-config.json','run.sh'):(new/name).write_bytes((old/name).read_bytes())
print('UPGRADED_SINGLE_DSO',runtime,sha)
