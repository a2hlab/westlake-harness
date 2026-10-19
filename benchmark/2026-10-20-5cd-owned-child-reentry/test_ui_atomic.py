"""One actual UI-class regression through original Board.shell/raw_shell marker.
Only ready and transport are fixtures; all shell execution stays in a tempdir.
"""
import argparse,ast,copy,json,re,shlex,subprocess,tempfile,time,types,unittest,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=HERE.parents[1]);args,rest=ap.parse_known_args()
class AtomicInput(unittest.TestCase):
 def test_guard_and_exact_click_share_remote_shell(self):
  ui=next(n for n in ast.parse((HERE/'ui.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='UI')
  basepath=args.source_root/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
  original=next(n for n in ast.parse(basepath.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Board')
  methods=[n for n in original.body if isinstance(n,ast.FunctionDef) and n.name in ('shell','raw_shell')]
  base=ast.ClassDef(name='Base',bases=[],keywords=[],body=methods,decorator_list=[])
  rows=[]
  for case in ('success','guard_refuses','stop_at_click_dispatch','lost_reply','awake_failure'):
   with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
    root=Path(d);calls=[];saved=[];record={'selected_icon':{'center':[736,507]}}
    (root/'config-common.sh').write_text('uitest(){ printf "%s\\n" "$*" >> "$HERE/clicks"; }\n')
    (root/'launch-common.sh').write_text(':\n')
    (root/'adoption-guard.sh').write_text('t13_adoption_guard(){ [ ! -e "$HERE/stop" ]; }\n')
    (root/'state').write_text('AWAITING_REENTRY\n');(root/'icon.intent').write_text('fixture\n')
    if case=='guard_refuses':(root/'stop').touch()
    env={'re':re,'uuid':uuid,'time':time,'BatchStop':RuntimeError,'AppFailure':RuntimeError}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[base],type_ignores=[])),'<original-Board-methods>','exec'),env)
    b=types.SimpleNamespace(Board=env['Base'],save=lambda p,r:saved.append(copy.deepcopy(r)),BatchStop=RuntimeError)
    env.update(b=b,a=types.SimpleNamespace(action='launch'),authority={'root':str(root)},record=record,out=root,shlex=shlex)
    exec(compile(ast.Module(body=[ui],type_ignores=[]),'<actual-UI-class>','exec'),env)
    def transport(self,argv,timeout=60):
     wrapped=argv[-1];calls.append(wrapped)
     self.assert_marker(wrapped)
     click='uitest uiInput click 736 507' in wrapped
     if click and case=='stop_at_click_dispatch':(root/'stop').touch()
     if wrapped.startswith('power-shell'):
      if case=='awake_failure':raise RuntimeError('awake failure')
      marker=re.search(r'__BMS_REMOTE_RC_[0-9a-f]+__',wrapped).group()
      return 0,('OverrideTimeout=86400000ms\n' if wrapped.startswith('power-shell dump') else '')+marker+'0\n'
     result=subprocess.run(['sh','-c',wrapped],capture_output=True,text=True,timeout=5)
     if click and case=='lost_reply':return 0,'lost marker'
     return result.returncode,result.stdout+result.stderr
    klass=type('FixtureUI',(env['UI'],),{'ready':lambda self:None,'command':transport,'assert_marker':lambda self,s: self_test.assertIn('__BMS_REMOTE_RC_',s)})
    self_test=self;obj=klass();obj.hdc=['mock'];obj.serial='fixture';obj.out=root;obj.index=0
    error=None
    try:obj.shell('uitest uiInput click 736 507')
    except RuntimeError as ex:error=str(ex)
    target_calls=[x for x in calls if 'uitest uiInput click 736 507' in x]
    self.assertEqual(len(target_calls),1)
    self.assertIn('t13_adoption_guard;',target_calls[0]);self.assertIn('set -eu;',target_calls[0])
    self.assertEqual(len([x for x in calls if 't13_adoption_guard;' in x]),1)
    self.assertEqual(record['ui_calls'][0]['command'],'uitest uiInput click 736 507')
    clicks=(root/'clicks').read_text().splitlines() if (root/'clicks').exists() else []
    if case in ('guard_refuses','stop_at_click_dispatch'):
     self.assertEqual(clicks,[]);self.assertFalse(record.get('clicked'));self.assertIsNotNone(error)
    else:self.assertEqual(clicks,['uiInput click 736 507'])
    if case=='lost_reply':
     self.assertEqual(record['ui_calls'][0]['result'],'unknown');self.assertFalse(record.get('clicked'));self.assertIn('lost remote status marker',error)
    if case in ('success','awake_failure'):
     self.assertTrue(record['clicked']);self.assertEqual(record['ui_calls'][0]['remote_rc'],0)
    if case=='success':self.assertIsNone(error)
    rows.append({'case':case,'target_remote_dispatches':len(target_calls),'actual_fixture_clicks':len(clicks),'record':record,'error':error})
  print(json.dumps({'cases':rows,'device_calls':0,'scope':'actual UI and original Board shell/raw_shell; local fixture transport'},indent=2))
if __name__=='__main__':unittest.main(argv=['test_ui_atomic.py']+rest)
