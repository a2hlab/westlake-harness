#!/usr/bin/env python3
"""G30 candidate only, gated by the completed exact d205 baseline. No staging."""
import argparse,hashlib,json,os,platform,shlex,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
BASE='d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'
BASE_RECIPE='e467bf0d6ef4aa648e6ad91b31863e9a6661fa3f96f44db1001cbd68f783d883'
SOURCE_PINS={'bionic_locale_compat.c':'21e52d1e8025795b34f5d258f563699adc52c598c3abe16fc848a4fa56cbe88a','bionic_stdio_compat.c':'e5cfec3dd99abb4b5b47141568ed045e4afb7f254560876d709c61ecf98c447b','native_abi.c':'6cf69a57a5318058aea1d2ce69f3b3a2355aa11231d5261a85435508443c3335','native_abi.map':'c1070f9dafe5def0625f095f7a6341ee962b2b32bf7fc555047ba46801452948'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def deps(p):
 return [Path(x) for x in shlex.split(p.read_text().replace('\\\n',' ').split(':',1)[1])]
def main():
 a=argparse.ArgumentParser();a.add_argument('--baseline',type=Path,required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args();B=x.baseline.resolve();O=x.out.resolve();O.mkdir(parents=True,exist_ok=False);src=D/'sources/candidate';oldsrc=D/'sources/baseline'
 r={'status':'INCOMPLETE','recipe_sha256':sha(__file__),'baseline_receipt_sha256':sha(B/'receipt.json'),'commands':[],'inputs':{},'outputs':{}};dump(O/'receipt.json',r)
 def pin(p):
  p=p.absolute();assert p.is_file(),str(p);h=sha(p);key=str(p)
  if key in r['inputs']:assert r['inputs'][key]['sha256']==h,('INPUT_DRIFT',key)
  r['inputs'][key]={'sha256':h,'bytes':p.stat().st_size};return h
 def run(name,argv,env):
  dump(O/(name+'.argv.json'),{'argv':argv,'cwd':str(D),'LD_LIBRARY_PATH':env['LD_LIBRARY_PATH']})
  with (O/(name+'.stdout')).open('wb') as so,(O/(name+'.stderr')).open('wb') as se:c=subprocess.run(argv,cwd=D,env=env,stdout=so,stderr=se)
  (O/(name+'.rc')).write_text(str(c.returncode)+'\n');r['commands'].append({'name':name,'rc':c.returncode});dump(O/'receipt.json',r)
  if c.returncode:raise RuntimeError(name+' rc='+str(c.returncode))
 try:
  assert platform.system()=='Linux','requires original Linux compiler'
  b=json.loads((B/'receipt.json').read_text());assert b['status']=='BASELINE_EXACT' and b['recipe_sha256']==BASE_RECIPE
  assert b['artifact']['sha256']==pin(B/'libwestlake_native_abi.so')==BASE
  assert sha(D/'build_baseline.py')==BASE_RECIPE
  assert [c['name'] for c in b['commands']]==['compiler','compile-native_abi.o','compile-stdio.o','link'] and all(c['rc']==0 for c in b['commands'])
  for p,h in b['inputs'].items():assert pin(Path(p))==h,p
  for name in ['native_abi.o','stdio.o']:assert pin(B/name)==b['objects'][name]
  for n,h in SOURCE_PINS.items():assert pin(src/n)==h,n
  oldmap=(oldsrc/'native_abi.map').read_bytes();assert (src/'native_abi.map').read_bytes()==oldmap.replace(b'LIBC { global:',b'LIBC { global: _ctype_; strtoll_l; strtoull_l;',1)
  for p in B.glob('*.d'):
   pin(p)
   for dep in deps(p):pin(dep)
  for s in (B/'link.stdout').read_text().splitlines():
   if s.startswith('/'):pin(Path(s))
  cmd=json.loads((B/'compile-native_abi.o.argv.json').read_text());env=dict(os.environ,LD_LIBRARY_PATH=cmd['LD_LIBRARY_PATH']);tc=Path(cmd['argv'][0]).parent.parent
  # Record the compiler/linker and host runtime providers without changing any tool.
  for p in [tc/'bin/clang-15',tc/'bin/ld.lld']+list((tc/'runtime').rglob('*')):
   if p.is_file():pin(p)
  def translate(argv):return [v.replace(str(oldsrc),str(src)).replace(str(B),str(O)) for v in argv]
  for name in ['compile-native_abi.o','compile-stdio.o']:
   pin(B/(name+'.argv.json'));c=json.loads((B/(name+'.argv.json')).read_text());run(name,translate(c['argv']),env)
  # Existing objects must remain byte-identical, not just export-compatible.
  for name in ['native_abi.o','stdio.o']:assert sha(O/name)==b['objects'][name],('OLD_OBJECT_DRIFT',name)
  locale=translate(cmd['argv']);locale=[v.replace('native_abi.c','bionic_locale_compat.c').replace('native_abi.o','locale.o') for v in locale]
  run('compile-locale.o',locale,env)
  pin(B/'link.argv.json');link=translate(json.loads((B/'link.argv.json').read_text())['argv']);link.insert(link.index('-lc'),str(O/'locale.o'));run('link',link,env)
  for p in O.glob('*.d'):
   for dep in deps(p):pin(dep)
  for line in (O/'link.stdout').read_text().splitlines():
   if line.startswith('/') and not Path(line).is_relative_to(O):pin(Path(line))
  for n,h in SOURCE_PINS.items():assert sha(src/n)==h
  for p,v in r['inputs'].items():assert sha(p)==v['sha256'],('FINAL_INPUT_DRIFT',p)
  for n in ['native_abi.o','stdio.o','locale.o','libwestlake_native_abi.so']:r['outputs'][n]={'sha256':sha(O/n),'bytes':(O/n).stat().st_size}
  r['status']='BUILT_OFFLINE_PENDING_ELF_REVIEW';r['old_objects_byte_identical']=True;r['expected_export_increment']=['_ctype_@@LIBC','strtoll_l@@LIBC','strtoull_l@@LIBC'];r['runtime_verified']=False
 except Exception as e:r['error']=str(e);raise
 finally:dump(O/'receipt.json',r)
if __name__=='__main__':main()
