"""Evidence audit, with no upgrade from a short clean window to causal closure."""
from pathlib import Path
import json,re
R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/enginecheck48'
s=json.loads((R/'final-acceptance.json').read_text());assert len(s['rounds'])==5
sha={'libbytehook.so':'fbb761a0f0d16342f9c63ff94af52b7d6377fda2def7c3f14950139907ea1baa','libshadowhook.so':'34378f5c2e2f7f4b418a332018916d488fcbabdf68109836bc83b74bc6f53e3c'}
rows=[]
for j in s['rounds']:
 d=R/j['round'];hashes=(d/'component-hashes.txt').read_text()
 for n,h in sha.items():assert h+'  ' in hashes and '/'+n in hashes
 maps=list(d.glob('maps*.maps'))+list((d/'faults').glob('*.maps'))
 maplines=[l for p in maps for l in p.read_text().splitlines() if any('/'+n in l for n in sha)]
 for n,i in [('libbytehook.so','137370'),('libshadowhook.so','137195')]:assert any(l.split()[4]==i and l.endswith('/'+n) for l in maplines),n
 (d/'engine-mapping-excerpts.txt').write_text('\n'.join(dict.fromkeys(maplines))+'\n')
 proofs=list(d.glob('maps*-engine-identity.txt'))+list(d.glob('live-engine-identity.txt'))
 for p in proofs:
  for n,h in sha.items():assert h+'  ' in p.read_text() and '/'+n in p.read_text()
 events=json.loads((d/'crash-events.json').read_text()) if (d/'crash-events.json').exists() else []
 for e in events:e['fault_since_proc_birth_s']=e['monotonic_ns']/1e9-int(j['birth'])/100;e['fault_address_hex']=hex(e['si_addr_or_union'])
 samples=[json.loads(l) for l in (d/'samples.jsonl').read_text().splitlines()];alive=[]
 for q in samples:
  for l in q['output'].splitlines():
   if l.startswith(str(j['child'])+' (') and l.rsplit(') ',1)[1].split()[0]!='Z':alive.append(q['elapsed'])
 rows.append(dict(round=j['round'],child=j['child'],parent=j['parent'],observation_s=j['observed_seconds'],last_alive_sample_s=max(alive),pass_180s=j['stability_pass'],guard_count=j['guard_count'],articles=j['articles'],library_mapping=j['library_mapping'],mapped_engine_identity='preflight+fault-maps inode+postflight' if not proofs else 'live /proc/pid/root SHA + matching maps inode',live_identity_files=[p.name for p in proofs],native_sig11=j['native_sig11'],exit1=j['parent_exit1'],ule=j['ule_lines'],fatal_headers=j['fatal_headers'],events=events))
verdict=dict(rounds=rows,stable_rounds=sum(j['pass_180s'] for j in rows),layout79_count=sum(len(j['layout79_lines']) for j in s['rounds']),all_ule_count=sum(len(j['ule_lines']) for j in s['rounds']),scope='five warm attempts, no replacements, nominal 360s navigation window; actual sampled survival listed separately',ack='blocked',r2='partially',causal_limit='No observed mallocng crash in this sample; sscronet null-vtable and sigaction write-out SIG11 remain. No claim all heap corruption is fixed or a NET/GFX hook is proven load-bearing.')
(R/'verdict.json').write_text(json.dumps(verdict,ensure_ascii=False,indent=2))
print(json.dumps([{k:j[k] for k in ('round','observation_s','last_alive_sample_s','pass_180s','native_sig11','exit1')} for j in rows],indent=2))
