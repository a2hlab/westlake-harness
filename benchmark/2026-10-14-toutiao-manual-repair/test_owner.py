#!/usr/bin/env python3
import importlib.util,json,os,pathlib,subprocess,tempfile,unittest,re
P=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('owner',P/'render_owner.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
BOOT='c9436daa-b3ca-44dc-985f-9ee03445567a'
class Tests(unittest.TestCase):
 def test_render_binding(self):
  o=dict(schema='toutiao-owner-observation/v1',status='VERIFIED',boot_id=BOOT,parent_pid=5257,parent_birth=8214,action='preflight',after='66352:154615|0:0|755|u:object_r:appdat:s0')
  d=m.render('apply',BOOT,5257,8214,'hdc',o);self.assertEqual(d['mutation_count'],1)
  for key,val in [('boot_id','bad'),('parent_birth',1),('after','66352:1|12:12|755|u:object_r:appdat:s0')]:
   with self.assertRaises(AssertionError):m.render('apply',BOOT,5257,8214,'hdc',{**o,key:val})
  self.assertEqual(m.render('reconcile',BOOT,5257,8214,'hdc',o)['mutation_count'],0)
 def test_ps_protocol(self):
  text=(P/'owner_remote.sh').read_text();frag=text[text.index(' process_rows=$(ps'):text.index('\n}\nidentity')]
  for rows,rc,ok in [('PID PPID\n1 0\n5257 1',0,True),('PID PPID\n5257 1\n8 5257',0,False),('PID UID\n5257 1',0,False),('PID PPID\n5257 1\nbad',0,False),('PID PPID\n1 0',0,False),('PID PPID\n5257 1',1,False)]:
   code='set -eu\nparent=5257\nfail(){ exit 2; }\nps(){ printf "%s\\n" "$ROWS"; return "$RC"; }\n'+frag
   r=subprocess.run(['sh','-c',code],env={**os.environ,'ROWS':rows,'RC':str(rc)},capture_output=True)
   self.assertEqual(r.returncode==0,ok)
 def test_metadata_actual_fragment(self):
  text=(P/'owner_remote.sh').read_text();frag=text[text.index(" IFS='|' read"):text.index(' if [ "$action" = reconcile')]
  r=subprocess.run(['sh','-c','set -eu\nfail(){ exit 2; }\nexpected="66352:154615|0:0|755|u:object_r:appdat:s0"\n'+frag+'\nprintf "%s" "$inode|20011300:20011300|$original_mode|$original_label"'],capture_output=True,text=True)
  self.assertEqual(r.returncode,0);self.assertEqual(r.stdout,'66352:154615|20011300:20011300|755|u:object_r:appdat:s0')
 def test_actual_cas_and_reconcile_shell(self):
  source=(P/'owner_remote.sh').read_text();body=source[source.index('identity\nbefore='):]
  old='66352:154615|0:0|755|u:object_r:appdat:s0';new=old.replace('|0:0|','|20011300:20011300|')
  cases=[('apply',old,old,0,new,1),('rollback',new,new,0,old,1),('apply',new,old,2,new,0),('reconcile',new,old,0,new,0),('reconcile',old,old,2,old,0)]
  for action,current,expected,rc,after,writes in cases:
   with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td);state=root/'state';state.write_text(current+'\n');calls=root/'calls'
    pre='set -eu\nfail(){ echo "$*" >&2; exit 2; }\nidentity(){ :; }\nmeta(){ cat "$STATE"; }\nchown(){ echo x >> "$CALLS"; printf "%s\\n" "$desired" > "$STATE"; }\n'
    env={**os.environ,'action':action,'expected':expected,'boot':BOOT,'parent':'5257','birth':'8214','T':str(root/'package'),'STATE':str(state),'CALLS':str(calls)}
    r=subprocess.run(['sh','-c',pre+body],env=env,capture_output=True,text=True)
    self.assertEqual(r.returncode,rc,r.stderr);self.assertEqual(state.read_text().strip(),after)
    self.assertEqual(len(calls.read_text().splitlines()) if calls.exists() else 0,writes)
 def jit_fixture(self,kind):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);data=root/'data/data';data.mkdir(parents=True);base=data/'com.ss.android.article.news';code=base/'code_cache';cache=code/'art-volatile'
   meta={str(data):{'uid':20011300,'gid':20011300,'mode':'755'}}
   if kind!='fresh':
    code.mkdir(parents=True)
    for p in [base,code]:meta[str(p)]={'uid':0 if kind!='equal' else 20011300,'gid':0 if kind!='equal' else 20011300,'mode':'755'}
   if kind=='foreign':meta[str(code)]['uid']=123
   if kind=='symlink':code.rmdir();code.symlink_to(data,target_is_directory=True)
   state=root/'state.json';state.write_text(json.dumps(meta));bin=root/'bin';bin.mkdir()
   shim=bin/'tool';shim.write_text('''#!/usr/bin/env python3
import os,sys,json,pathlib
name=pathlib.Path(sys.argv[0]).name;a=sys.argv[1:];state=pathlib.Path(os.environ['STATE']);d=json.loads(state.read_text());p=a[-1];v=d.get(p,{'uid':0,'gid':0,'mode':'755'});label='u:object_r:appdat:s0'
if name=='stat':
 st=os.stat(p);f=a[a.index('-c')+1];out=f.replace('%d',str(st.st_dev)).replace('%i',str(st.st_ino)).replace('%u',str(v['uid'])).replace('%g',str(v['gid'])).replace('%a',v['mode']).replace('%C',label);print(out)
elif name=='chown':
 with open(os.environ['WRITES'],'a') as f:f.write(name+' '+p+'\\n')
 u,g=a[-2].split(':');v.update(uid=int(u),gid=int(g));d[p]=v;state.write_text(json.dumps(d))
elif name=='chmod':v['mode']=a[0].lstrip('0');d[p]=v;state.write_text(json.dumps(d))
elif name=='mkdir':os.mkdir(p);d[p]=v;state.write_text(json.dumps(d))
elif name=='ls':print(p)
''');shim.chmod(0o755)
   for tool in ['stat','chown','chmod','mkdir','ls']:(bin/tool).symlink_to(shim)
   body=re.sub(r'(?<![\w/])/data',lambda _:str(root/'data'),(P/'prepare_jit51-owner-5cd.sh').read_text())
   r=subprocess.run(['sh','-c',body],env={**os.environ,'PATH':str(bin)+':'+os.environ['PATH'],'STATE':str(state),'WRITES':str(root/'writes')},capture_output=True,text=True)
   final=json.loads(state.read_text())
   if kind in ('foreign','symlink'):
    self.assertNotEqual(r.returncode,0);self.assertFalse((root/'writes').exists())
   else:
    self.assertEqual(r.returncode,0,r.stderr)
    for p in [base,code,cache]:self.assertEqual(final[str(p)]['uid'],20011300)
    self.assertEqual(final[str(base)]['mode'],'755');self.assertEqual(final[str(code)]['mode'],'755');self.assertEqual(final[str(cache)]['mode'],'700')
    self.assertFalse((base/'app_webview').exists())
 def test_jit_first_creation(self):self.jit_fixture('fresh')
 def test_jit_existing_root(self):self.jit_fixture('root')
 def test_jit_already_equal(self):self.jit_fixture('equal')
 def test_jit_foreign_zero_write(self):self.jit_fixture('foreign')
 def test_jit_symlink_zero_write(self):self.jit_fixture('symlink')
if __name__=='__main__':unittest.main(verbosity=2)
