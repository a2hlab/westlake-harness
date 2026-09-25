"""Verify stored/raw evidence hashes, result counts and optional committed blobs."""
import gzip, hashlib, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
E=ROOT/'evidence'; records=json.loads((E/'files.json').read_text())
repo=pathlib.Path(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--show-toplevel'],text=True).strip())
for row in records:
 p=E/row['file']; stored=p.read_bytes()
 assert hashlib.sha256(stored).hexdigest()==row['stored_sha256'],p
 raw=gzip.decompress(stored) if row['gzip'] else stored
 assert len(raw)==row['raw_bytes'] and hashlib.sha256(raw).hexdigest()==row['raw_sha256'],p
 if '--git' in sys.argv:
  blob=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+str(p.relative_to(repo))])
  assert blob==stored,p
before=(ROOT/'results.json').read_bytes()
subprocess.run([sys.executable,str(ROOT/'scripts/analyze30.py')],check=True)
assert (ROOT/'results.json').read_bytes()==before,'results.json differs from recomputation'
for row in json.loads((ROOT/'visual-review.json').read_text()):
 assert hashlib.sha256((E/row['file']).read_bytes()).hexdigest()==row['sha256'],row
p=json.loads((E/'runtime-provenance.json').read_text())
assert all(x['source_file_count']==306 and x['all_static_files_identical'] for x in p['runs'])
f=json.loads((E/'final-runtime-verification.json').read_text())
assert f['count']==306 and f['all_match']
assert all(not v.strip() for v in json.loads((E/'final-runtime-references.json').read_text()).values())
result=json.loads((ROOT/'results.json').read_text())
assert len(result['controls'])==2 and all(x['pass'] for x in result['controls'])
profile=json.loads((ROOT/'targets.json').read_text())
expected=sorted(set(profile['baseline_targets']+profile['additional_targets']))
assert len(expected)==19
for row in result['runs']:
 if row['run'].startswith('full-'):
  assert row['native_targets']==expected and row['ndk1_symbol_not_found']==0
assert next(x for x in result['runs'] if x['run']=='baseline-2')['ndk1_symbol_not_found']==1486
assert all(x['pc_mapping']['file_offset']=='0x1e006f0' for x in result['native_faults'] if x['run'] in ['baseline-3','full-3'])
print('PASS',len(records),'evidence files; hashes, gzip, counts, visual hashes, runtime and controls', 'including git blobs' if '--git' in sys.argv else '')
