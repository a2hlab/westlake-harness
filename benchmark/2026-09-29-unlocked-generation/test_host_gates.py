import copy,importlib.util,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('deploy',R/'scripts/lab/deploy_generation.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
T='/system/android/lib64/liboh_adapter_bridge.so';SRC='payload/android/lib64/liboh_adapter_bridge.so'
class Gates(unittest.TestCase):
 def manifest(self):return {'runtime_identity':'deployment-only','generation':'a'*64,'mounts':[{'target':'/system/android','source':'payload/android'}],'prerequisites':{},'files':{SRC:'b'*64,'payload/other':'e'*64},'live_hashes':{T:'b'*64}}
 def test_single_file_only(self):
  old=self.manifest();new=copy.deepcopy(old);new['files'][SRC]='c'*64;new['live_hashes'][T]='c'*64
  self.assertEqual(d.validate_replacement(old,new,T),SRC)
  new['files']['payload/other']='d'*64
  with self.assertRaisesRegex(ValueError,'exactly one'):d.validate_replacement(old,new,T)
 def test_live_sha_mismatch(self):
  old=self.manifest();new=copy.deepcopy(old);new['files'][SRC]='c'*64
  with self.assertRaisesRegex(ValueError,'SHA/target'):d.validate_replacement(old,new,T)
 def test_locked_generation_not_eligible(self):
  old=self.manifest();old.pop('runtime_identity')
  with self.assertRaisesRegex(ValueError,'unlocked'):d.validate_replacement(old,copy.deepcopy(old),T)
 def test_double_art_gate(self):
  g='a'*64;route='/system/lib64/westlake/route-a/'+g+'/'
  text='\n'.join('100-200 r-xp 00000000 0:0 1 '+p for p in [route+'libart.so',route+'libopenjdkjvm.so','/system/android/lib64/liboh_adapter_bridge.so'])
  self.assertTrue(d.check_maps(text,g)['passed'])
  self.assertFalse(d.check_maps(text+'\n300-400 r-xp 00000000 0:0 2 /system/android/lib64/libart.so',g)['passed'])
 def test_required_sources_and_zip(self):
  helper=R/'bms/src/adapter/build/inner/bridge_manifest_inputs.sh'
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);jni=root/'framework/package-manager/jni';jni.mkdir(parents=True);z=root/'zip';z.mkdir()
   files=[jni/n for n in ['apk_manifest_jni.cpp','apk_manifest_parser.cpp','axml_parser.cpp','arsc_resolver.cpp']]+[z/n for n in ['unzip.o','ioapi.o','libz.a']]
   for f in files:f.touch()
   env=dict(os.environ,ADAPTER_ROOT=str(root),OH=str(root),BRIDGE_MINIZIP_DIR=str(z),BRIDGE_LIBZ_A=str(z/'libz.a'))
   h=root/'build/inner/bridge_manifest_inputs.sh';h.parent.mkdir(parents=True);shutil.copyfile(helper,h)
   env['BUILD_INNER_INVOKED']='1'
   def run(full=False):return subprocess.run(['bash',str(R/'bms/src/adapter/build/inner/compile_oh_adapter_bridge.sh' if full else helper)],env=env,capture_output=True,text=True)
   self.assertEqual(run().returncode,0)
   for f in [files[0],files[4]]:
    f.unlink();r=run(full=True);self.assertNotEqual(r.returncode,0);self.assertIn(str(f),r.stderr);f.touch()

# Transaction test: an observed child maps failure after a real bind intent must
# restore only that file, restart the previous parent and keep the base mounts.
class TransactionRollback(unittest.TestCase):
 def test_post_swap_maps_failure_restores_previous_file(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);old=root/'old';new=root/'new';old.mkdir();new.mkdir()
   def package(p,content):
    f=p/SRC;f.parent.mkdir(parents=True);f.write_bytes(content)
    h=p/'payload/runtime/appspawn-x';h.parent.mkdir();h.write_bytes(b'host')
    digest=d.sha(f);m={'generation':'a'*64,'runtime_identity':'deployment-only','bridge_sha256':digest,'files':{SRC:digest,'payload/runtime/appspawn-x':d.sha(h)},'live_hashes':{T:digest,'/system/bin/appspawn-x':d.sha(h)},'prerequisites':{},'mounts':[{'source':'payload/android','target':'/system/android'},{'source':'payload/runtime/appspawn-x','target':'/system/bin/appspawn-x'}]};d.save(p/'package.json',m);return m
   om=package(old,b'bridge-before');nm=package(new,b'bridge-after')
   x=d.Deployment.__new__(d.Deployment);x.package=new;x.m=nm;x.gen='a'*64;x.root=root;x.out=root/'attempt';x.out.mkdir();x.statepath=root/'state.json'
   x.d={'status':'active_verified','package_path':str(old),'package_sha256':d.sha(old/'package.json'),'remote':'/data/local/tmp/base','boot_id':'boot','mounted':om['mounts'],'single_replacements':[]}
   files=dict(om['live_hashes']);tops={'/system/android':'/local/tmp/base/payload/android','/system/bin/appspawn-x':'/local/tmp/base/payload/runtime/appspawn-x'}
   x.board=SimpleNamespace(boot='boot',send=lambda src,dst:files.update({dst:d.sha(src)}))
   x.hashes=lambda paths:{p:files[p] for p in paths};x.top_mounts=lambda:dict(tops)
   x.stop=lambda:None;x.start=lambda digest:99
   def shell(cmd,**kw):
    if cmd.startswith('mount --bind '):
     _,_,src,dst=cmd.split();files[dst]=files[src];tops[dst]=src[len('/data'):]
    if cmd.startswith('umount '):
     dst=cmd.split()[1];tops.pop(dst,None);files[dst]=om['live_hashes'][dst]
    return ''
   x.shell=shell
   calls=[]
   def verify():
    x.verify_mounts();calls.append(x.m['bridge_sha256'])
    if x.m==nm:raise RuntimeError('child maps/SHA gate failed: duplicate libart')
    self.assertEqual(files[T],om['live_hashes'][T]);x.d['status']='active_verified';x.record()
   x.verify=verify
   with self.assertRaisesRegex(RuntimeError,'duplicate libart'):x.replace(T)
   self.assertEqual(files[T],om['live_hashes'][T]);self.assertEqual(files['/system/bin/appspawn-x'],om['live_hashes']['/system/bin/appspawn-x'])
   self.assertEqual(x.d['single_replacements'],[]);self.assertEqual(x.d['package_path'],str(old));self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
