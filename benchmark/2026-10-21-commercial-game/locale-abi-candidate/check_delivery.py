#!/usr/bin/env python3
"""Portable public packet validation plus actual host TU regressions; never builds OH."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
from check_elf import dynsyms,validate_abi
D=Path(__file__).resolve().parent;R=D.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--host',action='store_true');a=p.parse_args()
 manifest=json.loads((D/'final/manifest.json').read_text())
 for e in manifest['files']:
  f=R/e['path'];assert f.is_file() and sha(f)==e['sha256'] and f.stat().st_size==e['bytes'],e['path']
 result=json.loads((D/'final/results.json').read_text());b=json.loads((D/'final/baseline-receipt.json').read_text());c=json.loads((D/'final/candidate02-receipt.json').read_text());book=json.loads((D/'final/candidate02-bookends.json').read_text())
 assert b['status']=='BASELINE_EXACT' and b['artifact']['sha256']==result['baseline_sha256']=='d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'
 assert c['outputs']['libwestlake_native_abi.so']['sha256']==result['candidate_sha256']==book['artifact_sha256']=='4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b'
 assert c['recipe_sha256']==sha(D/'build_candidate.py');assert b['recipe_sha256']==sha(D/'build_baseline.py')
 assert all(x['rc']==0 for x in b['commands']+c['commands']);assert len(c['inputs'])==55==book['input_count'];assert book['rc']==0
 for n,h in json.loads((D/'candidate-source-pins.json').read_text()).items():assert sha(D/'sources/candidate'/n)==h
 assert len(json.loads((D/'final/input-closure.json').read_text())['files'])==55
 for n in ['native_abi.c','bionic_stdio_compat.c']:assert (D/'sources/baseline'/n).read_bytes()==(D/'sources/candidate'/n).read_bytes()
 validate_abi(dynsyms((D/'evidence/baseline-symbols.txt').read_text()),dynsyms((D/'evidence/candidate-symbols.txt').read_text()))
 assert result['status']=='OFFLINE_CANDIDATE_VERIFIED_NOT_DEPLOYED' and '__assert2 excluded' in result['limits']
 if a.host:
  out=Path(os.environ.get('G30_HOST_OUT',str(D/'.private/replays'/str(time.time_ns()))));out.mkdir(parents=True,exist_ok=False)
  steps=[['python3',str(D/'run_host.py'),'--out',str(out/'locale')],['python3',str(D/'run_preservation.py'),'--out',str(out/'preservation')],['python3',str(D/'check_negative.py')]]
  for i,argv in enumerate(steps):
   (out/(str(i)+'.argv.json')).write_text(json.dumps(argv))
   with (out/(str(i)+'.stdout')).open('wb') as so,(out/(str(i)+'.stderr')).open('wb') as se:r=subprocess.run(argv,stdout=so,stderr=se)
   (out/(str(i)+'.rc')).write_text(str(r.returncode));assert r.returncode==0,(i,str(out))
 print('PASS public manifest/source/build/ABI; OH runtime remains unknown; host='+str(a.host))
if __name__=='__main__':main()
