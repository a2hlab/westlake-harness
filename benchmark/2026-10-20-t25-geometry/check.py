#!/usr/bin/env python3
"""Compile the actual C TU and execute host seams. No runtime capability claim."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
P=Path(__file__).resolve().parent
CASES=['core_formats','core_zero','core_negative','core_null','core_foreign','core_acquire','core_unwrap','core_geometry_positive','core_geometry_negative','core_format','core_release','core_first_failure','core_missing','missing_owner','wrong_owner_offset','slot_scope_drift','missing_opt','wrong_opt_offset','mixed_provider','foreign_opt','unreadable_owner','phdr_overflow','binding_success','foreign_caller','mixed_lock','mixed_unlock','wrong_geometry','unreadable_player','second_player']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args();out=a.out or Path(os.environ.get('T25_CHECK_OUT',str(P/'.private')))/('host-'+str(time.time_ns()));out.mkdir(parents=True,exist_ok=False)
 rec={'status':'INCOMPLETE','device_calls':0,'commands':[],'sources':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['geometry.c','geometry.h','test_geometry.c','check.py']}}
 def call(name,argv):
  argv=list(map(str,argv));(out/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
  with (out/(name+'.stdout')).open('wb') as so,(out/(name+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(argv,stdout=so,stderr=se,timeout=30).returncode
   except subprocess.TimeoutExpired:rc=124
  (out/(name+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':name,'rc':rc});(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');assert rc==0,(name,rc,out)
 cc=shutil.which('cc');assert cc
 call('compile',[cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-pthread',P/'test_geometry.c','-o',out/'test'])
 for c in CASES:call(c,[out/'test',c])
 rec.update(status='HOST_PASS_RUNTIME_UNKNOWN',cases=len(CASES),format_cases=6,compiler={'path':cc,'sha256':hashlib.sha256(Path(cc).read_bytes()).hexdigest()});(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'cases':len(CASES),'raw':str(out),'device_calls':0}))
if __name__=='__main__':main()
