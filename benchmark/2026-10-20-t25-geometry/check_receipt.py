#!/usr/bin/env python3
"""Validate an actual T25 build receipt and its original files, not declared PASS alone."""
import argparse,hashlib,json
from pathlib import Path
BASELINE='a9abaf09ce020c45dea5a30d1030a8ae7f939a2f4434cd6ff3aec53cfc9726b6'
COMMANDS=['00-frozen','01-exact-player-relocations','02-baseline-link','10-geometry-dependencies','20-compile-geometry','30-candidate-link','40-baseline-elf','41-candidate-elf','42-abi-consumer']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(out):
 r=json.loads((out/'receipt.json').read_text())
 assert r['status']=='OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED' and r['device_calls']==0
 assert [c['name'] for c in r['commands']]==COMMANDS
 for c in r['commands']:
  assert c['rc']==0
  raw=out/'raw';assert (raw/(c['name']+'.rc')).read_text().strip()=='0'
  for ext in ['argv.json','stdout','stderr']:assert (raw/(c['name']+'.'+ext)).is_file()
  argv=json.loads((raw/(c['name']+'.argv.json')).read_text());assert isinstance(argv,list) and argv
 for name,v in r['inputs'].items():
  p=Path(name);assert p.is_file() and sha(p)==v['sha256'] and p.stat().st_size==v['bytes'],name
 for name,v in r['outputs'].items():
  p=out/name;assert p.is_file() and sha(p)==v['sha256'] and p.stat().st_size==v['bytes'],name
 assert set(r['outputs'])=={'baseline.so','geometry.o','candidate.so','abi.json'}
 assert r['outputs']['baseline.so']['sha256']==BASELINE
 assert r['abi']['old_exports']==77 and r['abi']['new_exports']==78
 assert r['abi']['added']==[['FUNC','GLOBAL','DEFAULT','ANativeWindow_setBuffersGeometry@@LIBC']]
 assert r['abi']['needed_unchanged'] and r['abi']['textrel'] is False
 for name in ['geometry.c','geometry.h','build.py']:
  snap=out/'source-snapshot'/name;assert snap.is_file()
  candidates=[v for p,v in r['inputs'].items() if Path(p).name==name]
  assert any(sha(snap)==v['sha256'] for v in candidates)
 return {'status':'VALID_OFFLINE_BUILD','commands':len(COMMANDS),'inputs':len(r['inputs']),'candidate':r['outputs']['candidate.so'],'runtime_geometry':'UNKNOWN','deployment_authorized':False}
def main():
 a=argparse.ArgumentParser();a.add_argument('out',type=Path);x=a.parse_args();print(json.dumps(validate(x.out)))
if __name__=='__main__':main()
