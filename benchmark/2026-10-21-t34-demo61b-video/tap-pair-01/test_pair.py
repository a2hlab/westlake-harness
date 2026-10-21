import ast,json,os,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ui
ROOT=Path(os.environ.get('T34_MAIN',Path(__file__).resolve().parents[3]))

class Tests(unittest.TestCase):
 def test_guard_functions_unchanged(self):
  def blocks(path):
   s=path.read_text();return {n.name:ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name!='main'}
  self.assertEqual(blocks(ROOT/'benchmark/2026-10-21-t34-demo61b-video/ui-01/ui.py'),blocks(Path(ui.__file__)))
 def exercise(self,fail):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t);start=int(time.time());session=dict(serial=ui.SERIAL,boot='dc603250-21c6-4aaf-ab84-d28cfe096ee5',holder='inner(cc-video) 123 '+ui.datetime.fromtimestamp(start).astimezone().isoformat(),start=start)
   (out/'session.json').write_text(json.dumps(session));calls=[]
   class OfflineBoard:
    def __init__(self,*args):self.record=None
    def ready(self):pass
    def shell(self,command,*args,**kwargs):
     calls.append(command)
     if fail and command=='uitest uiInput click 600 960':raise RuntimeError('first actual shell failure seam')
   fake=SimpleNamespace(save=ui.save);spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m:None))
   with patch.object(ui.importlib.util,'spec_from_file_location',return_value=spec),patch.object(ui.importlib.util,'module_from_spec',return_value=fake),patch.object(ui,'board_class',return_value=OfflineBoard),patch.object(ui,'observe') as observe,patch('subprocess.run') as run:
    args=['--repo',str(ROOT),'--window',str(out),'--session',str(out/'session.json'),'--tag','pair','--observe-seconds','0','tap-pair']
    if fail:
     with self.assertRaises(RuntimeError):ui.main(args)
     observe.assert_not_called()
    else:ui.main(args);observe.assert_called_once()
    run.assert_not_called()
   self.assertEqual([c for c in calls if c.startswith('uitest ')],['uitest uiInput click 600 960']+([] if fail else ['uitest uiInput click 1120 1862']))
   record=json.loads((out/'ui-pair/record.json').read_text())
   self.assertEqual(record['status'],'FAILED_OR_UNKNOWN_NO_AUTOMATIC_RETRY' if fail else 'completed')
 def test_exact_two_calls_then_one_observe(self):self.exercise(False)
 def test_first_failure_stops_second_and_observe(self):self.exercise(True)
if __name__=='__main__':unittest.main(verbosity=2)
