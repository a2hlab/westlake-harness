import ast,contextlib,io,json,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import wrapper as w
class Checks(unittest.TestCase):
    def test_preview_never_opens_device(self):
        with patch.object(sys,'argv',['wrapper']),patch.object(w.subprocess,'Popen',side_effect=AssertionError('device forbidden')),contextlib.redirect_stdout(io.StringIO()) as o:w.main()
        self.assertEqual(json.loads(o.getvalue())['device_calls'],0)
    def test_admission_disabled_before_file_or_device(self):
        for a in ({},{'schema':'t18-outer-v1','execution_enabled':False},{'schema':'t18-outer-v1','execution_enabled':True,'approved_by':'someone'}):
            with self.assertRaisesRegex(ValueError,'outer admission'):w.validate_local(a,Path('/nonexistent'),Path('/nonexistent'))
    def test_exact_port_no_prefix_collision(self):
        self.assertEqual(w.forward_lines('x tcp:50390 tcp:50390\ny tcp:5039 tcp:5039',5039),['y tcp:5039 tcp:5039'])
    def test_guard_shell_syntax_and_stop_gate(self):
        p={'boot':'11111111-2222-3333-4444-555555555555','init_mnt':'mnt:[1]'}
        for n,i in [('parent',20),('child',21),('host',22)]:p[n]={'pid':i,'birth':10,'ppid':1,'uid':0,'mnt':'mnt:[2]','exe_sha256':'a'*64}
        cmd=w.process_guard(p);self.assertIn('test "$1" != T',cmd);self.assertNotIn('test "$1" != T',w.process_guard(p,30));self.assertNotIn('tr ',cmd)
        self.assertEqual(subprocess.run(['sh','-n'],input=('( set -eu; '+cmd+' )').encode()).returncode,0)
    def test_host_cleanup_escalates_bounded(self):
        p=Mock();p.poll.return_value=None;p.wait.side_effect=[subprocess.TimeoutExpired('host',3),0]
        w.stop_host(p);p.terminate.assert_called_once();p.kill.assert_called_once();self.assertEqual([x.kwargs for x in p.wait.call_args_list],[{'timeout':3},{'timeout':3}])
    def test_host_unknown_never_unbounded_wait(self):
        p=Mock();p.poll.return_value=None;p.wait.side_effect=subprocess.TimeoutExpired('host',3)
        with self.assertRaises(subprocess.TimeoutExpired):w.stop_host(p)
        self.assertEqual(p.wait.call_count,2)
    def test_outer_finally_covers_start_and_entry(self):
        tree=ast.parse(Path(w.__file__).read_text());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main');outer=next(x for x in main.body if isinstance(x,ast.Try) and x.finalbody)
        body=ast.unparse(ast.Module(body=outer.body,type_ignores=[]));cleanup=ast.unparse(ast.Module(body=outer.finalbody,type_ignores=[]))
        self.assertIn("result['server_start_attempted'] = True",body);self.assertIn('subprocess.Popen',body);self.assertIn('server_identity()',cleanup);self.assertIn("'fport', 'rm'",cleanup);self.assertIn("result['outer_recovery_required']",cleanup)
if __name__=='__main__':unittest.main()
