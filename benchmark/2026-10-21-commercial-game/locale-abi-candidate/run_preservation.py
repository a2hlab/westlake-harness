#!/usr/bin/env python3
"""Real original native TU with host dependency seams, baseline and candidate."""
import argparse,hashlib,json,subprocess,os,shutil
from pathlib import Path
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();O=a.out.resolve();O.mkdir(parents=True,exist_ok=False);result={'status':'INCOMPLETE','seams':['host dlsym and pthread_atfork dependency injection','host __errno_location'],'production_source_changed':False,'commands':[],'source_pins':{}}
 env=dict(os.environ,CLANG_MODULE_CACHE_PATH=str(O/'module-cache'))
 try:
  test=D/'tests/native_preservation.c';shutil.copyfile(test,O/test.name)
  for v in ['baseline','candidate']:
   src=D/'sources'/v/'native_abi.c';h=sha(src);assert h=='6cf69a57a5318058aea1d2ce69f3b3a2355aa11231d5261a85435508443c3335';result['source_pins'][v]=h;shutil.copyfile(src,O/(v+'.c'))
   for n,argv in [('compile',['/usr/bin/clang','-std=c11','-Wall','-Wextra','-Werror','-O2','-DG30_SOURCE="'+str(src)+'"',str(test),'-o',str(O/v)]),('run',[str(O/v)])]:
    name=v+'-'+n;(O/(name+'.argv.json')).write_text(json.dumps(argv))
    with (O/(name+'.stdout')).open('wb') as so,(O/(name+'.stderr')).open('wb') as se:r=subprocess.run(argv,env=env,stdout=so,stderr=se)
    (O/(name+'.rc')).write_text(str(r.returncode));result['commands'].append({'name':name,'rc':r.returncode});assert r.returncode==0,name
  result['status']='BASELINE_CANDIDATE_REAL_BODY_REGRESSION_PASS';result['test_sha256']=sha(test)
 finally:(O/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
