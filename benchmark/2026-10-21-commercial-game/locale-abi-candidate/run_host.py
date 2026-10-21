#!/usr/bin/env python3
"""Compile the actual locale TU into independent host behavior tests; retain raw logs."""
import argparse,hashlib,json,subprocess,os,shutil
from pathlib import Path
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--cc',default='/usr/bin/clang');x=a.parse_args();O=x.out.resolve();O.mkdir(parents=True,exist_ok=False);src=D/'sources/candidate/bionic_locale_compat.c';test=D/'tests/locale_functions.c'
 shutil.copyfile(test,O/'locale_functions.c');shutil.copyfile(src,O/'bionic_locale_compat.c');shutil.copyfile(__file__,O/'run_host.py')
 assert sha(src)=='21e52d1e8025795b34f5d258f563699adc52c598c3abe16fc848a4fa56cbe88a'
 r={'status':'INCOMPLETE','source_sha256':sha(src),'test_sha256':sha(test),'compiler_sha256':sha(Path(x.cc)),'commands':[],'host_only':True}
 env=dict(os.environ,CLANG_MODULE_CACHE_PATH=str(O/'module-cache'))
 try:
  for name,argv in [('compiler',[x.cc,'--version']),('compile',[x.cc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-DG30_SOURCE="'+str(src)+'"',str(test),'-o',str(O/'locale-functions')]),('run',[str(O/'locale-functions')])]:
   (O/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
   with (O/(name+'.stdout')).open('wb') as so,(O/(name+'.stderr')).open('wb') as se:p=subprocess.run(argv,env=env,stdout=so,stderr=se)
   (O/(name+'.rc')).write_text(str(p.returncode)+'\n');r['commands'].append({'name':name,'rc':p.returncode})
   if p.returncode:raise RuntimeError(name+' rc='+str(p.returncode))
  assert sha(src)==r['source_sha256'] and sha(test)==r['test_sha256'];r['status']='HOST_REAL_LOCALE_FUNCTIONS_PASS'
 except Exception as e:r['error']=str(e);raise
 finally:(O/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
