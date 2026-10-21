#!/usr/bin/env python3
"""G36 fixed-device fresh reads only; no install, launch, server reset or retry."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent
SERIAL='N100CU025C18D000128';PACKAGE='com.miHoYo.Yuanshen'
EXPECTED='abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def now():return datetime.datetime.now().astimezone().isoformat()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--main',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve();assert out.is_relative_to(D/'.private');out.mkdir(exist_ok=False)
 c=Path.home()/'.local/share/westlake/commercial-game-20261021';old=c/'android-reference-readiness-01/abi.json';adb=Path(json.loads(old.read_text())['argv'][0]);index=a.main.resolve()/'benchmark/2026-10-21-commercial-game/official-input/input-index.json';i=json.loads(index.read_text())['inputs'][0];apk=Path(i['private_alias'].replace('$COMMERCIAL_G03_PRIVATE',str(c/'official-input')))
 assert i['sha256']==EXPECTED and apk.stat().st_size==i['size']==513290344 and sha(apk)==EXPECTED
 save(out/'inputs.json',{'apk':{'path':str(apk),'sha256':EXPECTED,'bytes':apk.stat().st_size,'package':i['package']},'official_index':{'path':str(index),'sha256':sha(index)},'adb':{'path':str(adb),'sha256':sha(adb)},'adb_path_source':{'path':str(old),'sha256':sha(old)},'spec':{'path':str(D/'source-contract.spec.md'),'sha256':sha(D/'source-contract.spec.md')},'verified_at':now()});print('exact APK SHA/size verified',flush=True)
 steps=[('state',['get-state'],{0}),('serial',['get-serialno'],{0}),('boot-before',['shell','cat','/proc/sys/kernel/random/boot_id'],{0}),('sdk',['shell','getprop','ro.build.version.sdk'],{0}),('abi',['shell','getprop','ro.product.cpu.abilist'],{0}),('package-list',['shell','pm','list','packages','--user','0',PACKAGE],{0}),('package-path',['shell','pm','path','--user','0',PACKAGE],{0,1}),('storage',['shell','df','-k','/data'],{0}),('boot-after',['shell','cat','/proc/sys/kernel/random/boot_id'],{0})];records=[];status='INCOMPLETE'
 for name,args,allowed in steps:
  argv=[str(adb),'-s',SERIAL,*args];rec={'argv':argv,'started_at':now(),'timeout_seconds':15,'read_only':True};save(out/(name+'.argv.json'),rec)
  with (out/(name+'.stdout')).open('wb') as so,(out/(name+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(argv,stdout=so,stderr=se,timeout=15).returncode;timed=False
   except subprocess.TimeoutExpired:rc=124;timed=True
  rec.update(rc=rc,timed_out=timed,ended_at=now(),stdout_sha256=sha(out/(name+'.stdout')),stderr_sha256=sha(out/(name+'.stderr')));save(out/(name+'.json'),rec);records.append(rec);print(name,rc,flush=True)
  if rc not in allowed or timed:status='REFUSED_COMMAND_FAILURE';break
  text=(out/(name+'.stdout')).read_text(errors='replace').strip();err=(out/(name+'.stderr')).read_text(errors='replace').strip()
  if err or any(x in text for x in ['Error:','Exception','Failure','SecurityException']):status='REFUSED_BODY_ERROR';break
  if name=='state' and text!='device':status='REFUSED_DEVICE_STATE';break
  if name=='serial' and text!=SERIAL:status='REFUSED_DEVICE_ID';break
  if name=='package-list' and text:status='PACKAGE_ALREADY_PRESENT_STOP';break
  if name=='package-path' and (rc!=1 or text):status='PACKAGE_PRESENCE_UNKNOWN_OR_PRESENT_STOP';break
 else:
  before=(out/'boot-before.stdout').read_text().strip();after=(out/'boot-after.stdout').read_text().strip();abi=(out/'abi.stdout').read_text().strip();sdk=(out/'sdk.stdout').read_text().strip()
  status='READONLY_READY_PENDING_OUTER_REVIEW' if before and before==after and 'arm64-v8a' in abi.split(',') and sdk=='36' else 'REFUSED_BOOT_OR_PLATFORM_DRIFT'
 save(out/'result.json',{'status':status,'serial':SERIAL,'commands':len(records),'install':False,'launch':False,'lock_acquired':False,'OH_commands':0,'records':records});print(status);return 0 if status=='READONLY_READY_PENDING_OUTER_REVIEW' else 2
if __name__=='__main__':sys.exit(main())
