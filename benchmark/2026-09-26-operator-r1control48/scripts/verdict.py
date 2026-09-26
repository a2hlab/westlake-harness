"""Audit observed survival, native identity and fault classes without causal overclaim."""
from pathlib import Path
import json,re
R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/r1control48'
s=json.loads((R/'final-acceptance.json').read_text());assert len(s['rounds'])==3
expected={}
for p in ['patches.json','engines.json']:
 expected.update(json.loads((R/'deployment'/p).read_text())['expected'])
expected['lib/arm64-v8a/libnpth.so']='9966e2966057c4d7d31f81232decf58da046898b9a2be900df675d44d016a107'
expected['lib/arm64-v8a/libmetasec_ml.so']='1021a0582e360ceafb49aa1162ee5d024104a73504ba0801927aaaa8bf2e706f'
sha={Path(n).name:h for n,h in expected.items() if n.startswith('lib/arm64-v8a/')}
rows=[]
for j in s['rounds']:
 d=R/j['round'];hashes=(d/'component-hashes.txt').read_text()
 for n,h in sha.items():assert any(l.startswith(h+'  ') and l.endswith('/'+n) for l in hashes.splitlines()),n
 maps=list(d.glob('maps*.maps'))+list((d/'faults').glob('*.maps'))
 maplines=[l for p in maps for l in p.read_text().splitlines() if any(l.endswith('/'+n) for n in sha)]
 proofs=list(d.glob('maps*-engine-identity.txt'))
 mapped={}
 for n,h in sha.items():
  matches=[l for l in maplines if l.endswith('/'+n)];inodes={l.split()[4] for l in matches};verified=[]
  for p in proofs:
   lines=p.read_text().splitlines()
   assert any(l.startswith(h+'  ') and l.endswith('/'+n) for l in lines),(p,n)
   stats=[l.split() for l in lines if l.endswith('/'+n) and len(l.split())==3]
   if any(a[0] in inodes for a in stats):verified.append(p.name)
  post=(R/'final-check/native-inodes.txt').read_text().splitlines()
  post_inode=any(l.endswith('/'+n) and l.split()[0] in inodes for l in post)
  mapped[n]={'sha256':h,'mapped':bool(matches),'inodes':sorted(inodes),'namespace_hash_and_inode_proofs':verified,'fault_maps_inode_matches_postflight':post_inode}

 (d/'native-mapping-excerpts.txt').write_text('\n'.join(dict.fromkeys(maplines))+'\n')
 events=json.loads((d/'crash-events.json').read_text()) if (d/'crash-events.json').exists() else []
 for e in events:
  e['fault_since_proc_birth_s']=e['monotonic_ns']/1e9-int(j['birth'])/100
  a=e['addresses'].get('pc',{});pc=int(a.get('elf_vaddr',a.get('file_offset','0')),16);lib=a.get('mapping','')
  e['category']=('mallocng' if 'ld-musl' in lib and 0xd5000<=pc<0xd8000 else 'monitorcollector-sigaction-region' if 'ld-musl' in lib and 0x1117d0<=pc<0x111a00 else 'sscronet-null-vtable' if 'libsscronet.so' in lib and pc==0x28a21c else 'other')
 samples=[json.loads(l) for l in (d/'samples.jsonl').read_text().splitlines()];alive=[]
 for q in samples:
  for l in q['output'].splitlines():
   if l.startswith(str(j['child'])+' (') and l.rsplit(') ',1)[1].split()[0]!='Z':alive.append(q['elapsed'])
 rows.append(dict(round=j['round'],child=j['child'],parent=j['parent'],observation_s=j.get('observed_seconds'),last_alive_sample_s=max(alive,default=0),terminal_alive=j.get('terminal_state',{}),stable_360s=j['stability_pass'],guard_count=j['guard_count'],articles=j['articles'],library_identity=mapped,native_sig11=j['native_sig11'],exit1=j['parent_exit1'],ule=j['ule_lines'],fatal_headers=j['fatal_headers'],events=events,main_exceptions=j['main_exceptions'],newdetail_resumed=j['newdetail_resumed'],inflow_resumed=j['inflow_resumed']))
identity=all(all(x['mapped'] and (x['namespace_hash_and_inode_proofs'] or x['fault_maps_inode_matches_postflight']) for x in j['library_identity'].values()) for j in rows)
passed=s['acceptance_pass'] and identity
verdict=dict(rounds=rows,stable_rounds=sum(j['stable_360s'] for j in rows),body_count=s['body_count'],identity_pass=identity,layout79_count=sum(len(j['layout79_lines']) for j in s['rounds']),all_ule_count=sum(len(j['ule_lines']) for j in s['rounds']),scope='Three consecutive warm controls with only sscronet restored to original; survival does not establish article-path functionality.',ack='done' if passed else 'blocked',r2='verified' if passed else 'partially',causal_limit='Observed fault absence applies only to reached paths and this test window; no inference of permanent heap safety or patch causality from survival alone.')
(R/'verdict.json').write_text(json.dumps(verdict,ensure_ascii=False,indent=2))
print(json.dumps([{k:j[k] for k in ('round','observation_s','stable_360s','native_sig11','exit1','newdetail_resumed','inflow_resumed')} for j in rows],indent=2))
