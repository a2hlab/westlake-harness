from pathlib import Path
import subprocess,json,shutil
r=Path.cwd();w=r/'bms/src/.work/b6-task58/v1-tests';w.mkdir(parents=True,exist_ok=True)
p=r/'bms/src/.work/b6-real-work/adapter/framework/appspawn-x/security_specialization/stock_child_plugin';o=Path.home()/'orca/.bridge-payload/appspawn-x-src/appspawn-x/security_specialization/stock_child_plugin';t=Path(__file__).resolve().parents[1]
for part in ['src','include']:
 f=w/part
 if not f.exists(): f.symlink_to(p/part,target_is_directory=True)
(w/'tests').mkdir(exist_ok=True)
records=[]
for name,language,flags,sources in [
 ('test_runtime_provider_child_sequence.cpp','c++',['-std=c++20'],[]),
 ('test_sealed_child_provider_loader.c','cc',['-std=c11','-DWLSCPL_TESTING'],[p/'src/sealed_child_provider_loader.c']),
 ('test_child_hook_table_v1.c','cc',['-std=c11'],[p/'src/child_hook_table_v1.c']),
 ('test_westlake_child_hook_table_v1_layout.c','cc',['-std=c11'],[])]:
 f=w/'tests'/name;shutil.copy2(o/'tests'/name,f);binary=w/f.stem
 if name == 'test_sealed_child_provider_loader.c':
  text=f.read_text();extra=(t/'recipes/inherited_loader_tests.c').read_text();text=text.replace('int main(void)',extra+'\nint main(void)').replace('    Run("positive_dependency_order_local_now", Positive);','    Run("r155_inherited_members", InheritedMembers);\n    Run("positive_dependency_order_local_now", Positive);');f.write_text(text)
 cmd=[language,*flags,'-Wall','-Wextra','-Werror','-I'+str(p/'include'),str(f),*map(str,sources),'-o',str(binary)]
 build=subprocess.run(cmd,text=True,capture_output=True);run=subprocess.run([str(binary)],text=True,capture_output=True) if build.returncode==0 else None
 records.append({'test':name,'compile_rc':build.returncode,'run_rc':None if run is None else run.returncode,'stdout':build.stdout+(run.stdout if run else ''),'stderr':build.stderr+(run.stderr if run else '')})
 print(name,records[-1]['compile_rc'],records[-1]['run_rc'],flush=True)
(t/'v1-host-tests.json').write_text(json.dumps({'passed':all(x['compile_rc']==0 and x['run_rc']==0 for x in records),'tests':records},indent=2)+'\n')
