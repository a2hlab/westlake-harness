#!/usr/bin/env python3
"""Offline source/recipe/raw-receipt audit; historical output mismatch must stay failure."""
import argparse,copy,hashlib,importlib.util,json,tempfile,unittest,shutil
from unittest.mock import patch
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SOURCE=REPO/'sources/api-implementations/jar-production-closeout'
HISTORICAL={'j1':'faf0782bb3a6dbf67a59022c35f95a1e3d33f35401f36d3a4ddbef309888180e','j7b':'381110a675fb543b6ad4102c8fc721fcb5673bc0da8644ececd1bab1ca60bec8'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def input_check(inputs,lock):
 assert {p.name for p in inputs.glob('*.jar')}==set(lock['dependency_inputs']),'unexpected/missing dependency'
 for name,h in lock['dependency_inputs'].items():assert sha(inputs/name)==h,'dependency drift: '+name
def claims(result):
 assert result['signature']=='SOURCE-CLOSEOUT' and result['device_calls']==0
 assert result['historical_exact_reproduction_proven'] is False,'false historical exact claim'
 assert result['historical_original_production_logs_recovered'] is False,'original logs not recovered'
 assert result['source_scope']=='overlay producer with pinned inherited baseline','baseline must remain explicit'
 assert result['human_review']=='pending_review','not independently accepted yet'
 for n in HISTORICAL:
  row=result['builds'][n]
  assert row['producer_rc']==0 and row['strict_wrapper_rc']==2
  assert row['historical_output_sha256']==HISTORICAL[n]
  assert row['output_sha256']!=HISTORICAL[n] and row['output_matches_historical'] is False
 return True
def verify(result=None):
 result=result or load(HERE/'results.json');claims(result)
 run=load(HERE/'evidence/run.json');assert len(run['executions'])==2
 for name,count in [('j1',39),('j7b',51)]:
  src=SOURCE/name;lock=load(src/'sources.lock.json');assert lock['historical_output_sha256']==HISTORICAL[name]
  assert len(lock['sources'])==count and len({r['path'] for r in lock['sources']})==count
  for r in lock['sources']:assert sha(src/r['path'])==r['sha256'],r['path']
  assert len(lock['dependency_inputs'])==14
  assert sha(src/'producer.py')==lock['producer_sha256']
  assert sha(src/'producer.original.py')==lock['original_producer_sha256']
  old=(src/'producer.original.py').read_text();new=(src/'producer.py').read_text()
  assert old.count("'assemble', smali, '-o'")==1
  assert old.replace("'assemble', smali, '-o'","'assemble', '--jobs', '1', smali, '-o'")==new,'recipe change beyond serial assembly'
  # Original strict gate is byte for byte unchanged.
  assert "q.returncode or (0 if result.get('output_matches_historical') else 2)" in (src/'build.py').read_text()
  ev=HERE/'evidence'/name;execution=load(ev/'execution.json');row=next(r for r in run['executions'] if r['label']==name)
  assert execution['producer_sha256']==lock['producer_sha256'] and execution['producer_rc']==0
  assert execution['historical_output_sha256']==HISTORICAL[name] and execution['historical_logs_recovered'] is False
  assert row['strict_wrapper_rc']==2
  assert sha(ev/'wrapper.stdout.txt')==row['stdout_sha256'] and sha(ev/'wrapper.stderr.txt')==row['stderr_sha256']
  assert (ev/'producer.stdout.txt').is_file() and (ev/'producer.stderr.txt').is_file()
  for phase in ('static','fresh'):
   comp=load(ev/phase/'comparison.json');classes=load(ev/phase/'classes.json')
   assert comp['historical']['artifact_sha256']==HISTORICAL[name]
   assert comp['historical_exact_match'] is False and comp['semantic_identity_is_not_historical_sha_acceptance'] is True
   assert comp['class_counts']==([129,129] if name=='j1' else [161,161])
   assert comp['full_disassembly_equal'] and classes['historical']==classes['rebuilt']
   assert not comp['class_added'] and not comp['class_removed'] and not comp['class_changed']
   for kind in ('0x2001','0x2003','0x2000'):
    section=next(s for s in comp['sections'] if s['map_type']==kind)
    assert section['equal'] and section['historical_sha256']==section['rebuilt_sha256'],'code/debug/class_data drift'
   for e in comp['executions']:
    assert e['rc']==0 and sha(ev/phase/e['stdout'])==e['stdout_sha256'] and sha(ev/phase/e['stderr'])==e['stderr_sha256']
   if phase=='fresh':assert comp['rebuilt']['artifact_sha256']==execution['output_sha256']==result['builds'][name]['output_sha256']
  order=load(HERE/'evidence'/(name+'-type-list-order.json'));assert len(order['inversions'])==(5 if name=='j1' else 6)
  assert all(r['same_content_hash_bucket512'] for r in order['inversions'])
 # Inspect production evidence only: a running Cargo log contains host paths and must
 # not become a recursive input to the very check currently producing that log.
 for name in HISTORICAL:
  for p in (HERE/'evidence'/name).rglob('*'):
   if p.is_file():assert b'/Users/' not in p.read_bytes() and b'/home/zhaoyue' not in p.read_bytes(),str(p)
 return {'status':'PASS','source_counts':[39,51],'dependencies':14,'classes':[129,161],'historical_binary_gate':'REJECTED_RC2','human_review':'pending_review','device_calls':0}
class Checks(unittest.TestCase):
 def test_actual_sources_receipts_and_unchanged_guards(self):self.assertEqual(verify()['historical_binary_gate'],'REJECTED_RC2')
 def test_cannot_upgrade_semantic_identity_to_binary_match(self):
  r=load(HERE/'results.json');r['historical_exact_reproduction_proven']=True
  with self.assertRaises(AssertionError):claims(r)
 def test_cannot_invent_original_logs(self):
  r=load(HERE/'results.json');r['historical_original_production_logs_recovered']=True
  with self.assertRaises(AssertionError):claims(r)
 def test_cannot_hide_wrapper_rc2(self):
  r=load(HERE/'results.json');r['builds']['j1']['strict_wrapper_rc']=0
  with self.assertRaises(AssertionError):claims(r)
 def test_missing_dependency_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(AssertionError,'missing dependency'):input_check(Path(d),load(SOURCE/'j1/sources.lock.json'))
 def test_changed_dependency_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'only.jar').write_bytes(b'wrong');lock={'dependency_inputs':{'only.jar':'0'*64}}
   with self.assertRaisesRegex(AssertionError,'dependency drift'):input_check(p,lock)
 def test_absent_raw_log_not_accepted(self):
  with tempfile.TemporaryDirectory() as d:
   temp=Path(d);shutil.copytree(HERE/'evidence',temp/'evidence');shutil.copyfile(HERE/'results.json',temp/'results.json')
   (temp/'evidence/j1/producer.stdout.txt').unlink()
   with patch.dict(globals(),{'HERE':temp}):
    with self.assertRaises(AssertionError):verify()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');a=ap.parse_args()
 print(json.dumps(verify(),indent=2))
 if not a.check:
  suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks);r=unittest.TextTestRunner(verbosity=2).run(suite)
  if not r.wasSuccessful():raise SystemExit(1)
if __name__=='__main__':main()
