"""Exercise the real upgrade/rollback command flow over a modeled mount stack."""
import copy,hashlib,importlib.util,json,shlex,tarfile,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('deployment',ROOT/'scripts/lab/deploy_generation.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
GEN='a'*64;ROUTE='/system/lib64/westlake/route-a/'+GEN
BR='/system/android/lib64/liboh_adapter_bridge.so';HOST='/system/bin/appspawn-x';NEW='/system/android/lib64/libnew.so';ALIAS='/system/android/lib64/libprovider.so'
def digest(b):return hashlib.sha256(b).hexdigest()
class MountBoard:
 def __init__(self,old,new):
  self.boot='boot';self.files={};self.mounts=[];self.events=[];self.fail_mount=0;self.mount_count=0;self.fail_send=False
  self.install('/data/local/tmp/resident',old)
  for row in old['mounts']:self.mounts.append(('/data/local/tmp/resident/'+row['source'],row['target']))
  self.files['/system/lib64/libapk_installer.so']='c'*64;self.files['/system/lib64/platformsdk/libapk_installer.so']='c'*64
 def install(self,remote,m):
  for n,h in m['files'].items():self.files[remote+'/'+n]=h
 def resolve(self,p):
  # A later directory bind hides earlier child mounts until it is unmounted.
  for src,dst in reversed(self.mounts):
   if p==dst or p.startswith(dst+'/'):return self.files.get(src+p[len(dst):])
  return self.files.get(p)
 def tops(self):return {dst:src[len('/data'):] for src,dst in self.mounts}
 def send(self,src,dst):
  self.events.append('send')
  if self.fail_send:raise RuntimeError('injected transfer failure')
  with tarfile.open(src) as t:
   for f in t.getmembers():
    if f.isfile():self.files[str(Path(dst).parent/f.name)]=digest(t.extractfile(f).read())
 def shell(self,cmd,**kw):
  if cmd.startswith('for p in '):
   paths=shlex.split(cmd[len('for p in '):cmd.index('; do')]);return '\n'.join((self.resolve(p) or 'ABSENT')+' '+p for p in paths)
  if cmd.startswith('test -e '):
   p=shlex.split(cmd)[-1];assert self.resolve(p) or any(x.startswith(p+'/') for x in [dst for _,dst in self.mounts]+list(self.files));return ''
  if cmd=='cat /proc/mounts':return '/dev/root / ext4 ro 0 0'
  if cmd.startswith('mount --bind '):
   _,_,src,dst=shlex.split(cmd);self.mounts.append((src,dst));self.events.append('mount:'+dst);self.mount_count+=1
   if self.mount_count==self.fail_mount:raise RuntimeError('injected bind completion before marker')
  if cmd.startswith('umount '):
   dst=shlex.split(cmd)[1];i=max(i for i,(_,t) in enumerate(self.mounts) if t==dst);self.mounts.pop(i);self.events.append('unmount:'+dst)
  return ''
class UpgradeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.old,self.om=self.package('old',False);self.new,self.nm=self.package('new',True)
  self.board=MountBoard(self.om,self.nm);x=d.Deployment.__new__(d.Deployment);self.x=x
  x.package=self.new;x.m=self.nm;x.gen=GEN;x.a=SimpleNamespace(serial='5cd');x.root=self.root;x.out=self.root/'attempt';x.out.mkdir();x.statepath=self.root/'state.json';x.board=self.board
  x.d={'status':'active_verified','package_path':str(self.old),'package_sha256':d.sha(self.old/'package.json'),'remote':'/data/local/tmp/resident','boot_id':'boot','mounted':copy.deepcopy(self.om['mounts']),'before':{HOST:'1'*64},'installer_before':{}}
  self.original=copy.deepcopy(x.d);x.b=SimpleNamespace(parse_bundle=lambda *a:{})
  x.shell=self.board.shell;x.top_mounts=self.board.tops
  def hashes(paths):
   result={p:self.board.resolve(p) for p in paths}
   if any(v is None for v in result.values()):raise RuntimeError('incomplete SHA readback')
   return result
  x.hashes=hashes;x.stop=lambda:self.board.events.append('stop')
  def start(h):self.assertEqual(self.board.resolve(HOST),h);self.board.events.append('start');return 42
  x.start=start;self.reject_new=False
  def verify():
   x.verify_mounts();self.assertEqual(hashes(x.m['live_hashes']),x.m['live_hashes'])
   if self.reject_new and x.package==self.new:raise RuntimeError('injected child maps failure')
   x.d['status']='active_verified';x.record()
  x.verify=verify
 def tearDown(self):self.tmp.cleanup()
 def package(self,name,new):
  root=self.root/name;root.mkdir()
  blobs={'payload/android/lib64/liboh_adapter_bridge.so':b'bridge','payload/android/lib64/libprovider.so':b'new-provider' if new else b'old-provider','payload/route/libprovider.so':b'new-provider' if new else b'old-provider','payload/runtime/appspawn-x':b'new-host' if new else b'old-host'}
  if new:blobs['payload/android/lib64/libnew.so']=b'new-library'
  for n,b in blobs.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  mounts=[{'source':'payload/android','target':'/system/android'},{'source':'payload/route','target':ROUTE},{'source':'payload/route/libprovider.so','target':ALIAS},{'source':'payload/runtime/appspawn-x','target':HOST}]
  files={n:digest(b) for n,b in blobs.items()};live={BR:files['payload/android/lib64/liboh_adapter_bridge.so'],ALIAS:files['payload/route/libprovider.so'],ROUTE+'/libprovider.so':files['payload/route/libprovider.so'],HOST:files['payload/runtime/appspawn-x']}
  if new:live[NEW]=files['payload/android/lib64/libnew.so']
  m={'generation':GEN,'runtime_identity':'deployment-only','bridge_sha256':live[BR],'mounts':mounts,'files':files,'live_hashes':live,'prerequisites':{}}
  d.save(root/'package.json',m);return root,m
 def assert_restored(self):
  self.assertEqual(self.x.d['package_path'],str(self.old));self.assertEqual(self.x.d['status'],'active_verified')
  self.assertEqual(self.x.hashes(self.om['live_hashes']),self.om['live_hashes']);self.assertIsNone(self.board.resolve(NEW));self.assertEqual(len(self.board.mounts),len(self.om['mounts']))
 def test_upgrade_aliases_then_exact_rollback_and_absence(self):
  self.x.deploy(upgrade=True)
  self.assertEqual(self.x.d['before_absent'],[NEW]);self.assertEqual(self.x.hashes(self.nm['live_hashes']),self.nm['live_hashes'])
  first_start=self.board.events.index('start');self.assertEqual(sum(e.startswith('mount:') for e in self.board.events[:first_start]),len(self.nm['mounts']))
  mounts=list(self.board.mounts);self.x.deploy(upgrade=True);self.assertEqual(mounts,self.board.mounts)
  self.x.rollback();self.assert_restored()
 def test_completed_alias_mount_before_marker_restores_resident(self):
  self.board.fail_mount=3
  with self.assertRaisesRegex(RuntimeError,'bind completion'):self.x.deploy(upgrade=True)
  self.assert_restored()
 def test_child_gate_failure_restores_resident(self):
  self.reject_new=True
  with self.assertRaisesRegex(RuntimeError,'child maps'):self.x.deploy(upgrade=True)
  self.assert_restored()
 def test_transfer_failure_preserves_resident(self):
  self.board.fail_send=True
  with self.assertRaisesRegex(RuntimeError,'transfer failure'):self.x.deploy(upgrade=True)
  self.assert_restored()
 def test_bad_alias_manifest_rejected_before_writes(self):
  self.nm['live_hashes'][ALIAS]='f'*64
  with self.assertRaisesRegex(ValueError,'alias/source'):self.x.deploy(upgrade=True)
  self.assertEqual(self.board.events,[])
 def test_foreign_mount_rejected_before_writes(self):
  self.board.mounts.append(('/data/foreign',ALIAS))
  with self.assertRaisesRegex(ValueError,'mount changed'):self.x.deploy(upgrade=True)
  self.assertEqual(self.board.events,[])
 def test_changed_underlying_addition_is_not_deleted_on_rollback(self):
  self.x.deploy(upgrade=True)
  self.board.files['/data/local/tmp/resident/payload/android/lib64/libnew.so']='f'*64
  with self.assertRaisesRegex(RuntimeError,'SHA/absence mismatch'):self.x.rollback()
  self.assertEqual(self.board.resolve(NEW),'f'*64)
 def test_existing_library_under_directory_is_restored_not_removed(self):
  path='/data/local/tmp/resident/payload/android/lib64/libnew.so';self.board.files[path]='e'*64
  self.x.deploy(upgrade=True);self.assertEqual(self.x.d['before_absent'],[])
  self.x.rollback();self.assertEqual(self.board.resolve(NEW),'e'*64)
  self.assertEqual(self.x.d['package_path'],str(self.old))
 def test_previous_single_overlay_is_preserved_on_upgrade_rollback(self):
  target=ROUTE+'/libprovider.so';remote='/data/local/tmp/old-single'
  self.board.files[remote]=self.om['live_hashes'][target];self.board.mounts.append((remote,target))
  self.x.d['single_replacements']=[{'target':target,'remote':remote,'previous_root':None}]
  mounts=list(self.board.mounts);self.x.deploy(upgrade=True);self.x.rollback()
  self.assertEqual(self.board.mounts,mounts);self.assertEqual(len(self.x.d['single_replacements']),1)
 def test_broken_or_unexpected_snapshot_rejected(self):
  self.x.shell=lambda *a,**k:'ABSENT /not-requested'
  with self.assertRaisesRegex(RuntimeError,'unexpected'):self.x.snapshot_files([NEW],[NEW])
 def fresh_board(self):
  self.board.mounts=[]
  for name,h in self.om['files'].items():
   if name.startswith('payload/android/'):
    self.board.files['/system/android/'+name[len('payload/android/'):]]=h
  self.board.files[HOST]=self.om['live_hashes'][HOST]
  self.x.d=None
 def test_fresh_deployment_absent_declared_library_and_rollback(self):
  self.fresh_board();self.x.deploy()
  self.assertEqual(self.x.d['before_absent'],[NEW])
  self.x.rollback();self.assertEqual(self.x.d['status'],'rolled_back')
  self.assertIsNone(self.board.resolve(NEW));self.assertEqual(self.board.mounts,[])
  self.assertEqual(self.board.resolve(HOST),self.om['live_hashes'][HOST])
 def test_fresh_failed_child_gate_restores_absence(self):
  self.fresh_board();self.reject_new=True
  with self.assertRaisesRegex(RuntimeError,'child maps'):self.x.deploy()
  self.assertEqual(self.x.d['status'],'rolled_back')
  self.assertIsNone(self.board.resolve(NEW));self.assertEqual(self.board.mounts,[])
if __name__=='__main__':unittest.main()
