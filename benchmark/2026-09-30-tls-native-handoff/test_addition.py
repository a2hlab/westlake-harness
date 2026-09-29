"""Exercise addition rollback using the real deployer against a fake board."""
import copy, importlib.util, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('deploy',R/'scripts/lab/deploy_generation.py')
d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
T='/system/android/lib64/liboh_tls_boundary.so'
S='payload/android/lib64/liboh_tls_boundary.so'
B='payload/android/lib64/liboh_adapter_bridge.so'
H='payload/runtime/appspawn-x'
class Addition(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.old=self.root/'old';self.new=self.root/'new'
  self.om=self.package(self.old,False);self.nm=self.package(self.new,True)
 def package(self,p,add):
  content={B:b'bridge',H:b'host'}
  if add:content[S]=b'TLS'
  for name,data in content.items():
   f=p/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  m={'generation':'a'*64,'runtime_identity':'deployment-only','files':{n:d.sha(p/n) for n in content},'prerequisites':{},'mounts':[{'source':'payload/android','target':'/system/android'},{'source':H,'target':'/system/bin/appspawn-x'}]}
  m['bridge_sha256']=m['files'][B];m['live_hashes']={'/system/android/lib64/liboh_adapter_bridge.so':m['files'][B],'/system/bin/appspawn-x':m['files'][H]}
  if add:m['live_hashes'][T]=m['files'][S]
  d.save(p/'package.json',m);return m
 def test_addition_needs_explicit_mode(self):
  self.assertEqual(d.validate_replacement(self.om,self.nm,T,adding=True),S)
  with self.assertRaisesRegex(ValueError,'requires --add'):d.validate_replacement(self.om,self.nm,T)
 def test_existing_file_and_multi_change_rejected(self):
  with self.assertRaisesRegex(ValueError,'already exists'):d.validate_replacement(self.nm,self.nm,T,adding=True)
  n=copy.deepcopy(self.nm);n['files'][H]='e'*64
  with self.assertRaisesRegex(ValueError,'exactly one'):d.validate_replacement(self.om,n,T,adding=True)
 def test_live_sha_and_mount_change_rejected(self):
  n=copy.deepcopy(self.nm);n['live_hashes'][T]='e'*64
  with self.assertRaisesRegex(ValueError,'SHA/target'):d.validate_replacement(self.om,n,T,adding=True)
  n=copy.deepcopy(self.nm);n['mounts'].append({'source':S,'target':T})
  with self.assertRaisesRegex(ValueError,'mounts'):d.validate_replacement(self.om,n,T,adding=True)
 def transaction(self,fail=False):
  x=d.Deployment.__new__(d.Deployment);x.package=self.new;x.m=self.nm;x.gen='a'*64;x.root=self.root;x.out=self.root/'attempt';x.out.mkdir();x.statepath=self.root/'state.json'
  x.d={'status':'active_verified','package_path':str(self.old),'package_sha256':d.sha(self.old/'package.json'),'remote':'/data/local/tmp/base','boot_id':'boot','mounted':self.om['mounts'],'single_replacements':[]}
  files=dict(self.om['live_hashes']);tops={'/system/android':'/local/tmp/base/payload/android','/system/bin/appspawn-x':'/local/tmp/base/'+H};placeholder={}
  x.board=SimpleNamespace(boot='boot',send=lambda src,dst:files.update({dst:d.sha(src)}));x.hashes=lambda paths:{p:files[p] for p in paths};x.top_mounts=lambda:dict(tops);x.stop=lambda:None;x.start=lambda digest:99
  def shell(cmd,**kw):
   if cmd.startswith('if [ ! -e '):return '' if T in files else 'ABSENT'
   if cmd.startswith('if [ -e '):return 'EXISTS' if T in files else 'ABSENT'
   if cmd.startswith('set -C;'):
    if T in files:raise RuntimeError('noclobber')
    files[T]=placeholder[T]=d.hashlib.sha256(b'').hexdigest()
   if cmd.startswith('mount --bind '):
    _,_,src,dst=cmd.split();files[dst]=files[src];tops[dst]=src[len('/data'):]
   if cmd.startswith('umount '):
    dst=cmd.split()[1];tops.pop(dst,None);files[dst]=placeholder[dst]
   if cmd.startswith('rm '):files.pop(cmd.split()[1])
   return ''
  x.shell=shell
  def verify():
   x.verify_mounts()
   self.assertEqual(x.hashes(list(x.m['live_hashes'])),x.m['live_hashes'])
   if fail and x.m==self.nm:raise RuntimeError('duplicate ART')
   x.d['status']='active_verified';x.record()
  x.verify=verify
  return x,files,tops,placeholder
 def test_success_then_rollback_removes_only_added_file(self):
  x,f,t,p=self.transaction();base=dict(t);x.replace(T,adding=True)
  self.assertEqual(f[T],self.nm['files'][S]);self.assertEqual(x.d['status'],'active_verified')
  x.rollback_single();self.assertNotIn(T,f);self.assertEqual(t,base);self.assertEqual(x.d['package_path'],str(self.old))
 def test_maps_failure_rolls_back_addition(self):
  x,f,t,p=self.transaction(fail=True)
  with self.assertRaisesRegex(RuntimeError,'duplicate ART'):x.replace(T,adding=True)
  self.assertNotIn(T,f);self.assertEqual(x.d['single_replacements'],[]);self.assertEqual(x.d['status'],'active_verified')
 def test_preexisting_target_refused_before_stop(self):
  x,f,t,p=self.transaction();f[T]='e'*64;x.stop=lambda:self.fail('must not stop')
  with self.assertRaisesRegex(RuntimeError,'already exists'):x.replace(T,adding=True)
 def test_changed_underlying_file_never_deleted(self):
  x,f,t,p=self.transaction();x.replace(T,adding=True);p[T]='e'*64
  with self.assertRaisesRegex(RuntimeError,'refuse removal'):x.rollback_single()
  self.assertEqual(f[T],'e'*64);self.assertEqual(len(x.d['single_replacements']),1)
 def test_other_mount_owner_never_removed(self):
  x,f,t,p=self.transaction();x.replace(T,adding=True);t[T]='/somebody/else'
  with self.assertRaisesRegex(RuntimeError,'externally'):x.rollback_single()
  self.assertEqual(t[T],'/somebody/else')
if __name__=='__main__':unittest.main()
