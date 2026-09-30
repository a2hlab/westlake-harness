#!/usr/bin/env python3
"""N2 offline evidence gates; never promote absent device evidence to passed UI."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
from deploy_generation import load_package,validate_upgrade
D=json.loads((P/'results.json').read_text());PKG=Path(D['package'])
def run(*args):subprocess.run([sys.executable,*map(str,args)],check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
mode=sys.argv[1]
if mode=='sources':
 rows=json.loads((P/'dispositions.json').read_text())['clusters'];assert len(rows)==6
 for row in rows:
  assert all(row[k] for k in ['source','first_wall','prediction','limit','implementation'])
  assert (P/row['evidence']).is_file()
 for rel,h in json.loads((P/'source-sha256.json').read_text()).items():assert sha(P/rel)==h,rel
 assert D['skia']['status']=='not_received_not_merged'
 assert len(json.loads((P/'toolchain-identities.json').read_text()))>=3
elif mode=='namespace':
 for name in ['test_namespace.py','test_load_paths.py','test_native_abi.py','audit_abi.py']:run(P/name)
 j=json.loads((P/'jni-signatures.json').read_text());assert len(j['classes'])==2
 for row in j['classes']:
  assert not row['undeclared_entries']
  for f,h in row['jar_sha256'].items():assert sha(Path(f))==h
 for row in json.loads((P/'closure/summary.json').read_text()):assert not row['missing_symbols'] and not row['missing_needed_names']
 assert len(json.loads((P/'closure/summary.json').read_text()))==6
elif mode=='package':
 assert sha(PKG/'package.json')==D['manifest_sha256']
 run(R/'scripts/lab/check_frozen.py','--package',PKG,'--source-root',R)
 before=load_package(Path(D['base_package']));after=load_package(PKG);validate_upgrade(before,after)
 assert sha(Path(D['base_package'])/'package.json')==D['base_sha256']
 changed={f for f,h in after['files'].items() if before['files'].get(f)!=h}
 declared={r['file'] for r in D['changes']};assert changed==declared,(changed,declared)
 for row in D['changes']:assert sha(PKG/row['file'])==row['sha256']
 assert json.loads((P/'dry-run.json').read_text())['passed']
 for row in json.loads((P/'elf-audit.json').read_text()):assert not row['removed_exports']
 with tempfile.TemporaryDirectory() as tmp:
  bad=Path(tmp)/'bad';subprocess.run(['/bin/cp','-Rc',str(PKG),str(bad)],check=True)
  f=bad/'payload/android/lib64/westlake_native/libwestlake_native_abi.so';f.write_bytes(f.read_bytes()+b'negative')
  try:load_package(bad)
  except ValueError as e:assert 'SHA mismatch' in str(e)
  else:raise AssertionError('corrupt package accepted')
 with tempfile.TemporaryDirectory() as tmp:
  rel=Path('benchmark/2026-09-30-asset-fd-runtime/src/android_util_AssetManager_aosp.cpp');f=Path(tmp)/rel;f.parent.mkdir(parents=True);f.write_bytes((R/rel).read_bytes()+b'\n// negative\n')
  x=subprocess.run([sys.executable,str(R/'scripts/lab/check_frozen.py'),'--source-root',tmp],text=True,capture_output=True)
  assert x.returncode and 'FZ-003' in x.stdout+x.stderr
 print('PASS corruption + frozen-source negatives')
elif mode=='handoff':
 assert D['device']['status']=='unverified' and not D['device']['board_writes']
 s=(P/'HANDOFF.md').read_text()
 for token in ['--rollback','--dry-run','45 minute','HW/ZZ','compare_runs.py','unknown']:assert token in s,token
 assert D['docker_byte_comparison'].startswith('unavailable')
else:raise ValueError(mode)
print('PASS N2',mode)
