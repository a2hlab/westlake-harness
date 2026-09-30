#!/usr/bin/env python3
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
from deploy_generation import load_package
mode=sys.argv[1]
run=lambda *a:subprocess.run([sys.executable,*map(str,a)],check=True)
if mode=='host':
 run(P/'test_host.py')
 d=json.loads((P/'host-tests.json').read_text());assert len(d['cases'])==12 and all(x['passed'] for x in d['cases'])
 run(P/'audit.py')
elif mode=='package':
 run(P/'audit.py');d=json.loads((P/'package.json').read_text());pkg=Path(d['package'])
 run(R/'scripts/lab/check_frozen.py','--package',pkg,'--source-root',R)
 dry=json.loads((P/'dry-run.json').read_text());assert dry['device_io'] is False and dry['passed']
 assert load_package(pkg)['rollout_ready'] is False
 # Real package validator rejects one changed byte before any board connection.
 with tempfile.TemporaryDirectory(prefix='n3b-negative-') as tmp:
  bad=Path(tmp)/'package';subprocess.run(['/bin/cp','-Rc',str(pkg),str(bad)],check=True)
  f=bad/'payload/android/lib64/liboh_android_runtime.so';f.chmod(f.stat().st_mode|0o200);f.write_bytes(f.read_bytes()+b'negative')
  try:load_package(bad)
  except ValueError as e:assert 'SHA mismatch' in str(e)
  else:raise AssertionError('mutated runtime accepted')
 print('PASS corrupted runtime SHA rejected without device I/O')
elif mode=='handoff':
 d=json.loads((P/'results.json').read_text());assert not d['board_commands'] and d['device_status']=='unverified'
 assert d['java_status']=='handoff_only' and d['provider_payload_status']=='missing_not_fabricated'
 s=(P/'JAVA-HANDOFF.md').read_text()
 for token in ['nativePrime','nativePublishAfterBind','()Z','Application.onCreate','ASX_WEBVIEW_APK','isAvailable','single-process','System.load','sProviderInstance']:assert token in s,token
 for token in ['--rollback','--replace','unknown','HW/ZZ'] :assert token in (P/'README.md').read_text(),token
 for rel,h in json.loads((P/'source-sha256.json').read_text()).items():assert hashlib.sha256((P/rel).read_bytes()).hexdigest()==h,rel
else:raise ValueError(mode)
print('PASS N3b',mode)
