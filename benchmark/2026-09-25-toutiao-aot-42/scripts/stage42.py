from board42 import *
base=R.parent/'touch21/framework-wake/device-report.json'
ref=R.parents[1]/'5ea34a4500000000000000001123012c/ability38/framework-candidate/device-report.json'
b=json.loads(base.read_text());d=json.loads(ref.read_text())
root=R/'framework-baseline';root.mkdir(exist_ok=False)
(root/'reference.json').write_bytes(ref.read_bytes())
(root/'before-processes.txt').write_text(exclusive())
old=b['stage'];stage='/data/local/tmp/a2hlab-framework-aot42-baseline'
assert 'COPIED' in dev(f'if [ -e {stage} ]; then echo EXISTS; else cp -a {old} {stage} && echo COPIED; fi',240)
changes={}
for name,v in d['files'].items():
 if b['files'].get(name,{}).get('sha256')==v['sha256']:continue
 candidates=[A/'out-aot42/inputs'/name]
 if name.startswith('lib'):
  candidates+=list((A/'out-ability38').rglob(pathlib.Path(name).name))+list((A/'out-focus34').rglob(pathlib.Path(name).name))
 p=next((p for p in candidates if p.is_file() and p.stat().st_size==v['bytes'] and sha(p)==v['sha256']),None)
 if p is None:raise RuntimeError('Missing local input '+name)
 send(p,stage+'/'+name);changes[name]=str(p)
expected={stage+'/'+n:v['sha256'] for n,v in d['files'].items()}
assert hashes(sorted(expected))==expected
assert hashes(sorted(d['firmware']))==d['firmware']
exclusive()
cmd=d['device_command'].replace(d['stage'],stage)
log=dev(cmd+' 2>&1; echo PRELOAD_RC=$?',120);(root/'preload.log').write_text(log)
assert 'PRELOAD_RC=0' in log,log[-3000:]
d.update(stage=stage,device_command=cmd,device_log_sha256=hashlib.sha256(log.encode()).hexdigest(),aot42={'reference_sha256':sha(ref),'overlay':changes},passed=True)
(root/'device-report.json').write_text(json.dumps(d,indent=2)+'\n')
print('BASE_STAGE_PASS',len(d['files']),flush=True)
for arm in ['verify','speed']:
 out=R/('framework-'+arm);out.mkdir(exist_ok=False);candidate=json.loads(json.dumps(d));target='/data/local/tmp/a2hlab-framework-aot42-'+arm
 assert 'COPIED' in dev(f'if [ -e {target} ]; then echo EXISTS; else cp -a {stage} {target} && mkdir -p {target}/oat/arm64 && echo COPIED; fi',240)
 for suffix in ['odex','vdex','art']:
  p=A/'out-aot42'/(arm+'-explicit')/('toutiao.'+suffix);name='oat/arm64/'+p.name
  send(p,target+'/'+name);candidate['files'][name]=dict(bytes=p.stat().st_size,sha256=sha(p))
 expected={target+'/'+n:v['sha256'] for n,v in candidate['files'].items()}
 assert hashes(sorted(expected))==expected
 candidate.update(stage=target,device_command=cmd.replace(stage,target))
 candidate['aot42']['app_aot_accepted']=False
 (out/'device-report.json').write_text(json.dumps(candidate,indent=2)+'\n')
 print('ARM_STAGE_HASH_PASS',arm,flush=True)
