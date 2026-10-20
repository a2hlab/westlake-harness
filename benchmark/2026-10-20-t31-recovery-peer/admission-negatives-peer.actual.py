from pathlib import Path
import sys,os,json,re,hashlib
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'source'));sys.path.insert(0,str(ROOT/'source/recovery'))
import check_offline as t
case=t.Checks();case.setUp();res=[]
try:
 p,o=t.policy.validate_origin(t.DATA,case.ap,case.oa);c=dict(repo=str(t.MAIN),deploy=str(t.DATA),serial=t.policy.SERIAL,holder=t.HOLDER,start=t.NEWSTART)
 changes=[('BRIDGE_PRIVATE_SHA_BEFORE','0'*64),('SHIM_PRIVATE_META_AFTER','755:20011300:20011300:999:123'),('BRIDGE_PRIVATE_LABEL_BEFORE','u:object_r:wrong:s0'),('BOOT_AFTER','00000000-0000-0000-0000-000000000000'),('P_MNT_AFTER','mnt:[999999]')]
 for key,val in changes:
  raw,n=re.subn(r'^'+re.escape(key)+r'=[^\n]+',key+'='+val,t.RAW,flags=re.M);assert n==1
  try:t.core.fill(t.MAIN,c,t.HOLDER,raw,t.NEWSTART+5,p,o,t.DATA)
  except ValueError as e:res.append({'case':key,'status':'REJECTED','reason':str(e)})
  else:raise AssertionError(key+' accepted')
 out={'status':'PASS','cases':res,'device_calls':0,'source_sha256':hashlib.sha256((ROOT/'source/recovery/recovery_core.py').read_bytes()).hexdigest(),'limits':'Actual local admission parser on changed raw fixture. No live device or namespace filesystem transaction.'}
 (ROOT/'extra-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
finally:case.doCleanups()
