#!/usr/bin/env python3
"""Rust selector entry: real host build/tests in unique persistent output."""
import copy,json,os,subprocess,sys,time
from pathlib import Path
from check_receipt import verify
HERE=Path(__file__).resolve().parent
root=next(x for x in HERE.parents if (x/'scripts/lab/check_frozen.py').is_file())
group=sys.argv[1];assert group in ['pair','failures','concurrency','receipt']
out=HERE/'.private'/('selector-'+group+'-'+str(time.time_ns()))
argv=[sys.executable,str(HERE/'build_host.py'),'--out',str(out),'--source-repo',os.environ.get('R14_SOURCE_REPO',str(root)),'--group','pair' if group=='receipt' else group]
subprocess.run(argv,check=True,timeout=180)
r=verify(out)
if group=='receipt':
 for name in ['status','source','rc','budget-evidence','artifact','capability']:
  b=copy.deepcopy(r)
  if name=='status':b['status']='DEPLOYABLE'
  elif name=='source':b['sources']['window_module.c']='0'*64
  elif name=='rc':b['commands'][0]['rc']=1
  elif name=='budget-evidence':b['groups']['pair']['cases']=999
  elif name=='artifact':b['artifacts']['window_module.o']['sha256']='0'*64
  else:b['production_binding']=True
  try:verify(out,b)
  except AssertionError:pass
  else:raise AssertionError('tampered receipt accepted '+name)
 print(json.dumps({'receipt_negative_cases':6,'status':'PASS'}))
print(json.dumps({'group':group,'status':'PASS','device_calls':0}))
