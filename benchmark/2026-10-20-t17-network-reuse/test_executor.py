"""Real host shell CAS checks; SELinux/ownership utilities use explicit host seams."""
import ast, hashlib, json, os, shlex, subprocess, sys, tempfile, unittest
from pathlib import Path
B=Path(__file__).resolve().parent
SOURCE=(B/'executor.py').read_text();TREE=ast.parse(SOURCE)
def helpers(rt):
    env={'q':shlex.quote,'re':__import__('re'),'RT':str(rt),'a':type('A',(),{'boot':'12345678-0000-0000-0000-000000000000','out':rt})(),'sha':lambda b:hashlib.sha256(b).hexdigest()}
    nodes=[n for n in TREE.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ('pathguard','fg','swap','normalize_wid')]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-executor-helpers','exec'),env)
    return env
class ExecutorTests(unittest.TestCase):
    def test_preview_and_recovery_apply_rejected(self):
        for mode in ('preflight','apply','rollback'):
            p=subprocess.run([sys.executable,str(B/'executor.py'),mode],capture_output=True,check=True)
            self.assertEqual(json.loads(p.stdout)['device_calls'],0)
        for mode in ('preflight','apply'):
            p=subprocess.run([sys.executable,str(B/'executor.py'),mode,'--recovery-no-parent'],capture_output=True)
            self.assertNotEqual(p.returncode,0)
        p=subprocess.run([sys.executable,str(B/'executor.py'),'rollback','--recovery-no-parent'],capture_output=True,check=True)
        self.assertEqual(json.loads(p.stdout)['device_calls'],0)
    def test_execute_missing_admission_refused(self):
        p=subprocess.run([sys.executable,str(B/'executor.py'),'apply','--execute'],capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertIn(b'explicit inputs',p.stderr)
    def test_wid_only_byte_equivalence(self):
        e=helpers(Path('/unused'));before=(B/'run5cd.before.reference.sh').read_bytes()
        after=(B/'run5cd.after.wid29.reference.sh').read_bytes()
        for raw in (before,after):
            norm,wid=e['normalize_wid'](raw.replace(b'WL_PARENT_ID=29\n',b'WL_PARENT_ID=41\n'))
            self.assertEqual(norm,raw);self.assertEqual(wid,41)
            foreign=raw.replace(b'ASX_RUNTIME_OWNER_UID=20011300',b'ASX_RUNTIME_OWNER_UID=20011206')
            self.assertNotEqual(e['normalize_wid'](foreign)[0],raw)
        for raw in (before+b'export WL_PARENT_ID=44\n',before.replace(b'WL_PARENT_ID=29\n',b'WL_PARENT_ID=0\n'),before.replace(b'WL_PARENT_ID=29\n',b'WL_PARENT_ID=x\n')):
            with self.assertRaises(AssertionError):e['normalize_wid'](raw)
    def run_swap(self, mode):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();e=helpers(root);target=root/'target';src=root/'source'
            target.write_bytes(b'original');target.chmod(0o644);src.write_bytes(b'candidate')
            meta=f'644:{os.getuid()}:{os.getgid()}';label='u:object_r:appdat:s0'
            if mode=='foreign':target.write_bytes(b'foreign')
            if mode=='symlink':target.unlink();target.symlink_to(src)
            cmd=e['swap']('target',str(src),e['sha'](b'candidate'),meta,label,e['sha'](b'original'))
            # macOS utility adapters only; cp/mv/hash/path tests and actual bytes are real.
            shim='''stat() { /usr/bin/stat -f '%Lp:%u:%g' "$3"; }
ls() { printf 'u:object_r:appdat:s0 %s\\n' "$2"; }
chcon() { return 0; }
chown() { return 0; }
'''
            got=subprocess.run(['sh','-c','set -eu\n'+shim+cmd],capture_output=True)
            if mode=='good':self.assertEqual(got.returncode,0,got.stderr);self.assertEqual(target.read_bytes(),b'candidate')
            else:
                self.assertNotEqual(got.returncode,0)
                if mode=='foreign':self.assertEqual(target.read_bytes(),b'foreign')
                else:self.assertTrue(target.is_symlink())
    def test_real_cas_success(self):self.run_swap('good')
    def test_foreign_cas_refuses(self):self.run_swap('foreign')
    def test_symlink_refuses(self):self.run_swap('symlink')
    def test_actual_strings_environment_and_host_guards(self):
        calls=[n for n in ast.walk(TREE) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='read' and n.args and 'strings /proc/' in ast.unparse(n.args[0])]
        self.assertEqual(len(calls),2)
        env={'a':type('A',(),{'parent':'19163'})()}
        for call in calls:
            cmd=eval(compile(ast.Expression(call.args[0]),'actual-env-command','eval'),env)
            good=subprocess.run(['sh','-c','strings() { printf "WL_PARENT_ID=29\\n"; }; '+cmd],capture_output=True)
            self.assertEqual(good.returncode,0);self.assertEqual(good.stdout.strip(),b'29')
            duplicate=subprocess.run(['sh','-c','strings() { printf "WL_PARENT_ID=29\\nWL_PARENT_ID=29\\n"; }; '+cmd],capture_output=True)
            self.assertNotEqual(duplicate.stdout.strip(),b'29')
            failed=subprocess.run(['sh','-c','strings() { return 127; }; '+cmd],capture_output=True)
            self.assertNotEqual(failed.returncode,0)
        node=next(n for n in TREE.body if isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and n.target.id=='hostguard')
        cmd=eval(compile(ast.Expression(node.value),'actual-host-command','eval'),{'host':{'pid':18952}})
        for text,ok in [('org.westlake.imehost',True),('prefix-org.westlake.imehost',False)]:
            got=subprocess.run(['sh','-c','set -e; strings() { printf "%s\\n" '+shlex.quote(text)+'; }; '+cmd],capture_output=True)
            self.assertEqual(got.returncode==0,ok)
    def test_shell_syntax(self):
        e=helpers(Path('/data/example'))
        p=subprocess.run(['sh','-n'],input=e['swap']('target','/input','a'*64,'644:1:1','u:object_r:appdat:s0','b'*64).encode(),capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()
