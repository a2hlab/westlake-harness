"""Actual main() argument wiring with offline seams; original guard suite is separate."""
import ast, contextlib, io, json, os, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ui

ROOT=Path(os.environ.get('T34_MAIN',Path(__file__).resolve().parents[3]))
OLD=ROOT/'benchmark/2026-10-21-t34-demo61b-video/ui-01/ui.py'

class Tests(unittest.TestCase):
    def test_exact_guard_budget_power_observation_bytes_unchanged(self):
        def blocks(path):
            s=path.read_text();tree=ast.parse(s)
            return {n.name:ast.get_source_segment(s,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        before=blocks(OLD);after=blocks(Path(ui.__file__))
        for key in before:
            if key!='main':self.assertEqual(before[key],after[key],key)

    def test_actual_main_routes_both_exact_selectors_to_desktop_launch(self):
        expected={'boatattack':{'package':'com.Unity3d.BoatAttackDay','launch_activity':'com.unity3d.player.UnityPlayerActivity'},'libresudoku':{'package':'com.kaajjo.libresudoku','launch_activity':'com.kaajjo.libresudoku.MainActivity'}}
        for app,want in expected.items():
            with self.subTest(app=app),tempfile.TemporaryDirectory() as t:
                root=Path(t);start=int(time.time())
                holder='inner(cc-video) 123 '+ui.datetime.fromtimestamp(start).astimezone().isoformat()
                session={'serial':ui.SERIAL,'boot':'dc603250-21c6-4aaf-ab84-d28cfe096ee5','holder':holder,'start':start}
                (root/'session.json').write_text(json.dumps(session));events=[]
                class OfflineBoard:
                    def __init__(self,s,budget,repo,hdc,out):
                        self.budget=budget;events.append(('construct',s));self.record=None
                    def ready(self):events.append(('ready',))
                    def shell(self,*args,**kwargs):events.append(('shell',args));return 0,''
                fake=SimpleNamespace(desktop_launch=lambda board,selected,remote,out,record:events.append(('launch',selected)),save=ui.save)
                spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m:None))
                # No transport. Actual parser/budget/pin checks, branch and final receipt execute.
                with patch.object(ui.importlib.util,'spec_from_file_location',return_value=spec),patch.object(ui.importlib.util,'module_from_spec',return_value=fake),patch.object(ui,'board_class',return_value=OfflineBoard) as factory,patch.object(ui,'observe') as observe,patch('subprocess.run') as run:
                    ui.main(['--app',app,'--repo',str(ROOT),'--window',str(root),'--session',str(root/'session.json'),'--tag',app,'--observe-seconds','10','launch'])
                    factory.assert_called_once_with(fake);observe.assert_called_once();run.assert_not_called()
                self.assertEqual([x[1] for x in events if x[0]=='launch'],[want])
                self.assertLess(next(i for i,x in enumerate(events) if x[0]=='ready'),next(i for i,x in enumerate(events) if x[0]=='launch'))
                self.assertEqual(json.loads((root/('ui-'+app)/'record.json').read_text())['status'],'completed')

    def test_invalid_or_missing_app_fails_before_session_or_device(self):
        base=['--repo','.','--window','.','--session','absent','--tag','x','launch']
        for addition in [[],['--app','imehost'],['--app','com.Unity3d.BoatAttackDay'],['--app','../boatattack']]:
            with self.subTest(addition=addition),patch('subprocess.run') as run,patch.object(ui,'board_class') as factory,contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:ui.main(addition+base)
                self.assertEqual(error.exception.code,2);factory.assert_not_called();run.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
