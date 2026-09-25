"""Offline evidence verification, including the explicit failed performance gate."""
import pathlib,json,gzip,hashlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];e=root/'evidence'
records=json.loads((e/'files.json').read_text())
for r in records:
 b=(e/r['file']).read_bytes();assert hashlib.sha256(b).hexdigest()==r['stored_sha256'],r['file']
 raw=gzip.decompress(b) if r['gzip'] else b
 assert len(raw)==r['raw_bytes'] and hashlib.sha256(raw).hexdigest()==r['raw_sha256'],r['file']
 if '--git' in sys.argv:
  repo=root.parents[1];rel=(e/r['file']).relative_to(repo)
  blob=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+str(rel)])
  assert blob==b,str(rel)
d=json.loads((root/'results.json').read_text())
assert d['board']=='5ea34a4500000000000000001123012c'
assert len(d['trials'])==4 and len(d['diagnostics'])==2 and len(d['controls'])==2
for r in d['trials']+d['diagnostics']:
 assert r['certificate_starts']==r['certificate_passes']==1 and r['certificate_failures']==0,r['run']
 assert not r['registry_ui_samples'] and not r['fatal_signals'] and not r['ui_exit_lines'],r['run']
 assert any('skipVerify=false' in x['text'] for x in r['certificates'])
 assert any('scheme=3 signers=1' in x['text'] for x in r['certificates'])
for r in d['trials']:
 assert len(r['touches'])==2 and not r['unconsumed_posts']
 assert min(s['line'] for s in r['ui_stacks'])>max(t['run_line'] for t in r['touches'])
for r in d['controls']:assert r['observation']['pass'] and r['observation']['observation_seconds']>=65
assert d['status']=='blocked' and not any(x['under_2s'] for x in d['comparisons'])
p=json.loads((e/'build-provenance.json').read_text())
assert p['all_source_hashes_match_build'] and p['contains_2478a7f'] and p['source_inputs']==73
assert len(p['runtime_changes'])==9 and all(x['file'].startswith('boot/') or x['file']=='fw/adapter-runtime-bcp.jar' for x in p['runtime_changes'])
f=json.loads((e/'final-runtime-verification.json').read_text());assert f['all_match'] and f['count']==306
assert not any(json.loads((e/'final-runtime-references.json').read_text()).values())
print('PASS',len(records),'evidence hashes; 4 measurements + 2 diagnostics; genuine verification logs; 2 smoke controls; <2s gate truthfully FAILED')
