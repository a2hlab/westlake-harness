#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
def check():
 e={x['object']:x for x in json.loads((D/'elf-evidence.json').read_text())}
 assert len(e)==5 and all(x['rc']==0 for x in e.values())
 hits=lambda n:'\n'.join(x['text'] for x in e[n]['hits'])
 assert 'UND __register_atfork@LIBC' in hits('game')
 assert '__register_atfork@@LIBC' in hits('abi') and '__register_atfork@@LIBC' in hits('pthread-system')
 assert 'atfork' not in hits('compat') and 'atfork' not in hits('pthread-route')
 dep=json.loads((D/'deployment-evidence.json').read_text())
 for n in ['abi','pthread-system','pthread-route','compat']:assert e[n]['sha256'] in dep['expected_files'].values()
 assert dep['verification_child']!=31523 and dep['game_identities']==[]
 t=(D/'log-excerpt.txt').read_text()
 for s in ['L3276:', '__register_atfork', 'L3733:', 'exit with code:1']:assert s in t
 r=json.loads((D/'results.json').read_text());assert r['provider_winner']=='UNKNOWN' and not r['runtime_pass'] and r['device_calls']==0
 a=json.loads((D/'apk-binding.json').read_text());assert a['member_sha256']==e['game']['sha256'] and a['local_extracted_match']
 assert len(json.loads((D/'rea-reuse.json').read_text())['existing_methods'])==5
 if (D/'manifest.json').exists():
  for x in json.loads((D/'manifest.json').read_text())['files']:
   p=D/x['path'];assert len(p.read_bytes())==x['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],p
 return {'status':'PASS','ELF_objects':5,'prior_REA_hashes':5,'provider_winner':'UNKNOWN','runtime_acceptance':False}
if __name__=='__main__':print(json.dumps(check()))
