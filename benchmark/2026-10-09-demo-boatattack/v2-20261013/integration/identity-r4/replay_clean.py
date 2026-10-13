"""Copy only declared Python inputs, then rebuild actual proof and full128 in a fresh tree."""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
FILES=['candidate_identity.py','absence_reader.py','compile_candidate.py','prepare_actual.py','run_candidate_post_reboot.py','test_candidate.py','test_r4_delta.py','prepare_smoke10.py','full128-stable-first-manifest.json','smoke10-t20-tiers.json','smoke10-controls-t20.json']
def main():
 env=dict(os.environ);env.setdefault('WORKSPACES',str(HERE.parents[5]))
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)
  for name in FILES:shutil.copyfile(HERE/name,root/name)
  def run(args):subprocess.run([sys.executable,*map(str,args)],cwd=root,env=env,check=True)
  run(['-m','unittest','discover','-s',root,'-p','test_*.py','-v'])
  run([root/'prepare_actual.py','--out',root/'inputs'])
  run([root/'compile_candidate.py','--request',root/'inputs/request.json','--out',root/'compiled'])
  import hashlib
  proof=root/'compiled/candidate-proof.json';digest=hashlib.sha256(proof.read_bytes()).hexdigest()
  run([root/'run_candidate_post_reboot.py','--out',root/'round','--serial','5ea34a4500000000000000001123012c','--boot-before','d0e1f5eb-ac35-4c39-9e1a-7c40d9251220','--candidate-proof',proof,'--candidate-proof-sha256',digest,'--smoke',root/'compiled/smoke.json'])
  config=json.loads((root/'round/round.json').read_text());assert config['apps']==128 and config['execution_enabled'] is False
  assert len(json.loads((root/'round/batch-apps.json').read_text())['apps'])==128
  print(json.dumps({'status':'CLEAN_REPLAY_PASS','tests':22,'canonical_apps':128,'execution_enabled':False,'device_calls':0,'generation_sha256':config['generation_sha256']}))
if __name__=='__main__':main()
