#!/usr/bin/env python3
"""Evidence gates: absent device evidence fails instead of becoming a skipped pass."""
import hashlib,json,subprocess,sys,tempfile,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent
PKG=R.parent/'westlake-generation-n1-candidate'
sys.path.insert(0,str(R/'scripts/lab'))
from deploy_generation import load_package,validate_upgrade
mode=sys.argv[1]
if mode=='frozen':
 subprocess.run([sys.executable,str(R/'scripts/lab/check_frozen.py'),'--package',str(PKG),'--source-root',str(R)],check=True)
 m=load_package(PKG);validate_upgrade(load_package(R.parent/'westlake-runtime-asset-fd-53f00423'),m)
elif mode=='clusters':
 d=json.loads((P/'dispositions.json').read_text())['clusters'];assert len(d)==11
 assert {x['cluster_id'] for x in d}=={'N0'+str(n) for n in range(1,10)}|{'KEEP01','KEEP02'}
 for row in d:
  assert row['implementation_status'] in ['implemented','partial','not_implemented','java_boundary','preserved']
  assert row['source'] and row['implementation'] and row['pass_checkpoint'] and row['evidence']
elif mode=='host':
 subprocess.run([sys.executable,str(P/'test_namespace.py')],check=True)
 assert json.loads((P/'caller-gate.json').read_text())['passed']
 for row in json.loads((P/'closure/summary.json').read_text()):assert not row['missing_symbols'] and not row['missing_needed_names']
 assert len(json.loads((P/'closure/summary.json').read_text()))==6
 assert '136 checks, 0 failures' in (P/'anl-strict-tests.txt').read_text()
 assert '74 checks, 0 failures' in (P/'native-loader-tests.txt').read_text()
 # Exercise the production package gate, rather than trust a negative label.
 with tempfile.TemporaryDirectory() as tmp:
  dst=Path(tmp)/'bad';subprocess.run(['/bin/cp','-Rc',str(PKG),str(dst)],check=True)
  f=dst/'payload/android/lib64/libwestlake_native_abi.so';f.write_bytes(f.read_bytes()+b'bad')
  try:load_package(dst)
  except ValueError as e:assert 'SHA mismatch' in str(e)
  else:raise AssertionError('corrupt library accepted')
 # A copied frozen source mutation must fail without touching the real source.
 with tempfile.TemporaryDirectory() as tmp:
  rel=Path('benchmark/2026-09-30-asset-fd-runtime/src/android_util_AssetManager_aosp.cpp')
  target=Path(tmp)/rel;target.parent.mkdir(parents=True);target.write_bytes((R/rel).read_bytes()+b'\n// negative-control\n')
  result=subprocess.run([sys.executable,str(R/'scripts/lab/check_frozen.py'),'--source-root',tmp],text=True,capture_output=True)
  assert result.returncode!=0 and 'FZ-003' in result.stdout+result.stderr
  (P/'frozen-negative.txt').write_text(result.stdout+result.stderr)
elif mode=='device':
 d=json.loads((P/'device-verdicts.json').read_text());assert d['controls_reviewed'] and d['frozen_evidence_preserved']
 for f in d['facts_files']:assert 'TOTAL keys=' in (R/f).read_text()
 assert d['compare_runs'] and d['first_fatal_files']
elif mode=='handoff':
 d=json.loads((P/'device-61b/final-identity.json').read_text());assert d['u0_restored'] and d['lock_released']
 assert (P/'HANDOFF.md').is_file()
else:raise ValueError(mode)
print('PASS N1',mode)
