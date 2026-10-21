#!/usr/bin/env python3
"""Record unchanged original offline entry points; no VM or device invocation."""
import argparse,datetime,json,os,subprocess,sys
from pathlib import Path
from inspect_inputs import save,sha
D=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--main',type=Path,required=True);ap.add_argument('--assembly',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 main=a.main.resolve();assembly=a.assembly.resolve();out=a.out.resolve();assert out.is_relative_to(D/'.private');out.mkdir(exist_ok=False)
 s=main/'scripts/lab';c=assembly/'candidate';b=assembly/'baseline'
 commands=[('u7',[sys.executable,str(s/'u7_executor.py'),'--dry-run','--package',str(c),'--baseline-native',str(b/'native'),'--out',str(out/'u7-plan.json')]),('static',[sys.executable,str(s/'generation_static_checks.py'),'--package',str(c),'--baseline',str(b),'--policy',str(c/'g32-static-policy.unsigned.json'),'--out',str(out/'static.json')])]
 for side in ['baseline','candidate']:
  native=assembly/side/'native'
  commands.extend([('native-'+side,[sys.executable,str(s/'native_predeploy.py'),'--package',str(native),'--inputs',str(native/'native-checks/native-gates.json'),'--readelf','/opt/homebrew/bin/llvm-readelf']),('frozen-'+side,[sys.executable,str(s/'check_frozen.py'),'--package',str(native)])])
 env=os.environ.copy();env.update(WORKSPACES=str(main.parent),WESTLAKE_HARNESS=str(main),WESTLAKE_DEPLOY_REPO=str(main),PYTHONDONTWRITEBYTECODE='1');records=[]
 for name,argv in commands:
  rec={'name':name,'argv':argv,'tool_sha256':sha(argv[1]),'started_at':datetime.datetime.now().astimezone().isoformat(),'device_io':False};save(out/(name+'.argv.json'),rec)
  with (out/(name+'.stdout')).open('wb') as o,(out/(name+'.stderr')).open('wb') as e:
   try:rc=subprocess.run(argv,env=env,stdout=o,stderr=e,timeout=240).returncode
   except subprocess.TimeoutExpired:rc=124
  rec.update(rc=rc,ended_at=datetime.datetime.now().astimezone().isoformat());save(out/(name+'.receipt.json'),rec);(out/(name+'.rc')).write_text(str(rc)+'\n');records.append(rec);print(name+' rc='+str(rc),flush=True)
 save(out/'records.json',records)
if __name__=='__main__':main()
