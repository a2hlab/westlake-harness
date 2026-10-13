"""Synthetic protocol/evidence tests only; no HDC or real locks."""
import ast,copy,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import window_hooks as h
import resume_baseline as r
class Tests(unittest.TestCase):
 def test_real_held_format_and_four_rejections(self):
  w=h.Window.__new__(h.Window);w.auth={'holder':'outer(codex)'};w.program=lambda _:Path('/not-executed/board_note.sh')
  good=SimpleNamespace(returncode=0,stdout='outer(codex) 63359 2026-10-13T17:00:00+0800\n',stderr='')
  with patch.object(h.subprocess,'run',return_value=good):self.assertEqual(w.held(),good.stdout.strip())
  for changes in [dict(returncode=1),dict(stderr='warning'),dict(stdout=''),dict(stdout='foreign 63359 time')]:
   bad=copy.copy(good)
   for k,v in changes.items():setattr(bad,k,v)
   with patch.object(h.subprocess,'run',return_value=bad),self.assertRaises(ValueError):w.held()
 def test_inner_auth_full_line_BMS_owner_unchanged(self):
  tree=ast.parse(Path(h.__file__).read_text());auths=[]
  for node in ast.walk(tree):
   if isinstance(node,ast.Dict):
    fields={k.value:v for k,v in zip(node.keys,node.values) if isinstance(k,ast.Constant)}
    if 'action' in fields and isinstance(fields['action'],ast.Constant) and fields['action'].value in ('apply','rollback'):
     auths.append(fields['action'].value);self.assertEqual(ast.unparse(fields['holder']),'self.held()')
  self.assertEqual(sorted(auths),['apply','rollback'])
  text=Path(h.__file__).read_text();self.assertIn("owner=self.auth['holder']",text);self.assertIn("'--lane',self.auth['holder']",text)
 def test_resume_skip_only_after_validation_and_fresh_boot(self):
  w=h.Window.__new__(h.Window);w.plan={'boot_id':'right'};w.boot_id=lambda:'wrong'
  with self.assertRaisesRegex(ValueError,'fresh origin'):w.after_lock()
  text=Path(h.__file__).read_text();self.assertLess(text.index('resume.validate('),text.index('enabled=dict('))
 def fixture(self,base):
  # Deliberately synthetic test documents, never emitted as actual evidence.
  root=base/'prior/run';root.mkdir(parents=True);board=root.parent/'board-run';board.mkdir()
  def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x));return p
  program=put(base/'program.json',{});plan=put(base/'plan.json',{'boot_id':'synthetic-boot'})
  ref=lambda p:dict(path=str(p),sha256=r.sha(p))
  q={'serial':r.SERIAL,'out':str(root),'plan':ref(plan),'activation_binding':ref(program),'popup_keys':['a','b','c','d','e'],'programs':{k:ref(program) for k in ['batch','smoke','installer','r5']}}
  qp=put(root.parent/'request.json',q);bp=put(board/'board-run-result.json',dict(after_lock=2,before_unlock=0,smoke=None,shards=[]))
  put(root/'no-placement.json',dict(no_transaction_or_intent=True,host_foreground_restored=True,original940_passed=True))
  report=dict(status='PASS',passed=True,mode='live-readonly',file_count=940,synthetic=False,serial=r.SERIAL,current_boot='synthetic-boot',boot_before='synthetic-boot',boot_after='synthetic-boot',activation={'binding':q['activation_binding']},checks=[dict(target=str(i),equal=True,expected='x',actual='x') for i in range(940)])
  for tag in ['baseline-r5','no-placement-r5']:put(root/(tag+'.json'),report)
  for key in q['popup_keys']:
   directory=root/'popup-before/batch'/r.SERIAL/key;shots=[]
   for n in [5,10,20]:
    p=put(directory/(str(n)+'.jpeg'),{});shots.append(dict(path=str(p),sha256=r.sha(p),captured=True,scheduled_seconds=n))
   put(directory/'record.json',dict(key=key,serial=r.SERIAL,boot_id='synthetic-boot',status='captured',screenshots=shots))
  put(root/'baseline-hw-zz/smoke-result.json',dict(passed=True,serial=r.SERIAL,checks=[dict(ok=True)]))
  for n,tag in enumerate(['baseline-r5','popup-before','baseline-hw-zz','apply','no-placement-r5']):
   p=put(root/('hook-test/%03d-%s.json'%(n,tag)),dict(argv=['python',str(program)],started=n*2,finished=n*2+1,rc=2 if tag=='apply' else 0));p.with_suffix('.stdout').touch();p.with_suffix('.stderr').touch()
  return q,qp,bp,root
 def test_evidence_closure_and_negative_cases(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);q,qp,bp,root=self.fixture(base)
   with patch.dict(os.environ,WORKSPACES=t):
    r.inspect(qp,bp)
    m=dict(schema='boat-r5-resume-baseline/v1',synthetic=False,serial=r.SERIAL,boot_id='synthetic-boot',prior_request=r.pin(qp),board_run_result=r.pin(bp),files=r.files(root));mp=base/'resume.json';mp.write_text(json.dumps(m));new=dict(q,out=str(base/'new/run'),resume_after_baseline=r.pin(mp))
    self.assertTrue(r.validate(mp,new)['baseline_reused'])
    for key,value in [('serial','wrong'),('popup_keys',['a'])]:
     bad=dict(new);bad[key]=value
     with self.assertRaises(ValueError):r.validate(mp,bad)
    unexpected=root/'unexpected';unexpected.touch()
    with self.assertRaisesRegex(ValueError,'file set'):r.validate(mp,new)
    unexpected.unlink()
    intent=root/'intent-000.json';intent.write_text('{}')
    with self.assertRaisesRegex(ValueError,'intent'):r.inspect(qp,bp)
    intent.unlink()
    p=root/'no-placement-r5.json';data=json.loads(p.read_text());data['current_boot']='other';p.write_text(json.dumps(data))
    with self.assertRaisesRegex(ValueError,'boot'):r.inspect(qp,bp)
 def test_cleanup_pending_cannot_build_resume(self):
  with tempfile.TemporaryDirectory() as t:
   q,qp,bp,root=self.fixture(Path(t));bp.write_text(json.dumps(dict(after_lock=2,before_unlock=2,smoke=None,shards=[])))
   with self.assertRaisesRegex(ValueError,'cleanup'):r.inspect(qp,bp)
if __name__=='__main__':unittest.main(verbosity=2)
