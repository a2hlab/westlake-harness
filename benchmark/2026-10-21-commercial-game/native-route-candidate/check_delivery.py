#!/usr/bin/env python3
"""Verify fixed source/build evidence; optionally execute real local C regression."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(root):
 for r in json.loads((root/'source-pins.json').read_text()):
  assert sha(root/r['path'])==r['sha256'],r['path']
  b=root/r['path'].replace('sources/candidate/','sources/baseline/')
  assert sha(b)==r['baseline_sha256'],str(b)
 for r in json.loads((root/'evidence/owner-source-index.json').read_text()):assert sha(root/r['path'])==r['sha256']
 hb=json.loads((root/'evidence/host-baseline-01.json').read_text());hc=json.loads((root/'evidence/host-candidate-01.json').read_text());a=json.loads((root/'evidence/anl-production-01.json').read_text());f=json.loads((root/'evidence/elf-facts.json').read_text());r=json.loads((root/'results.json').read_text())
 assert hb['status']=='BASELINE_EXACT' and hb['artifact']['sha256']=='2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e'
 assert a['status']=='BASELINE_EXACT_AND_CANDIDATE_BUILT_OFFLINE' and a['builds'][0]['artifact']['sha256']=='eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c'
 assert hc['status']=='CANDIDATE_BUILT_OFFLINE' and r['runtime_binding']=='UNKNOWN' and r['device_calls']==0
 for name in ['host','anl']:
  c=f['comparisons'][name];assert c['dynamic_abi_equal'] and c['needed_order_equal'] and c['dynamic_symbols']>0 and not c['textrel']
 assert len(f['core_libc_matches'])==3
 assert hb['recipe_sha256']==hc['recipe_sha256']==sha(root/'build_host.py')
 assert a['recipe_sha256']==sha(root/'build_anl.py')
 for rec,variant in [(hb,'baseline'),(hc,'candidate')]:
  for name,h in rec['sources'].items():assert sha(root/'sources'/variant/'host'/name)==h
 for rec in a['builds']:
  for name,h in rec['sources'].items():assert sha(root/'sources'/rec['variant']/'anl'/name)==h
 for item in r['executed_commands']:
  assert item['rc']==0
  assert item['stdout_sha256'] and item['stderr_sha256'] and item['argv_sha256']
 assert len(r['executed_commands'])==8
 return {'source_pins':17,'build_commands_rc0':8,'status':'PASS_OFFLINE_ONLY'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--routes',action='store_true');a=p.parse_args();v=check(D)
 if a.routes:
  with tempfile.TemporaryDirectory(prefix='g26-routes-') as t:subprocess.run(['python3',str(D/'check_routes.py'),'--out',str(Path(t)/'run')],check=True)
 print(json.dumps(v))
if __name__=='__main__':main()
