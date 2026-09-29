#!/usr/bin/env python3
"""Keep actual master-batch facts, process tables and hash-bound log excerpts."""
import hashlib,json,re,shutil
from pathlib import Path
E=Path(__file__).resolve().parent
S='5ea34a4500000000000000001123012c'
BASE=E.parents[2]/'westlake-generation-state'/S
D=json.loads((E/'results.json').read_text());D['batch_16m']={}
for cohort,jar in [('b5','250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146'),('r8b','d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554')]:
 run=f'b68-final-{cohort}-16m-5ea';src=BASE/run/run/S
 if not (src/'facts.txt').exists():continue
 out=E/'evidence'/f'master-{cohort}-16m';out.mkdir(exist_ok=True)
 for name in ['facts.txt','preflight.json','summary.json','plan.json']:shutil.copyfile(src/name,out/name)
 result={'raw':str(src),'jar_sha256':jar,'facts':(src/'facts.txt').read_text(),'apps':{}}
 for key in ['fd-android','ooniprobe']:
  app=src/key;dest=out/key;dest.mkdir(exist_ok=True)
  for name in ['record.json','processes-t5.txt','processes-t20.txt']:
   if (app/name).exists():shutil.copyfile(app/name,dest/name)
  data=(app/'hilog.txt').read_bytes();text=data.decode(errors='replace');rec=json.loads((app/'record.json').read_text())
  patterns=['providers populated','nativeParseManifest','KoinApplication has not','ClassCastException','Caused by:','SQLiteConnection::nativeOpen','SQLiteConnection.nativeOpen','Opened connection','WorkManager is not initialized','[B7','[B8','nativeOpen returned','SQLITE']
  lines=[f'{i}: {s}' for i,s in enumerate(text.splitlines(),1) if 'HDC_LOG' not in s and any(p in s for p in patterns)]
  (dest/'hilog-excerpt.txt').write_text('\n'.join(lines)+'\n')
  result['apps'][key]={'providers':re.findall(r'providers populated:\s*(\d+)',text),'hilog_sha256':hashlib.sha256(data).hexdigest(),'hilog_bytes':len(data),'old_koin_wall':text.count('KoinApplication has not been started'),'application_cast_error':any('ClassCastException' in l and 'Application' in l for l in text.splitlines()),'sqlite_registration':text.count('SQLiteConnection::nativeOpen'),'sqlite_opened_connection_logs':text.count('Opened connection'),'observed_pids':rec.get('observed_pids'),'status':rec['status']}
 D['batch_16m'][cohort]=result
(E/'results.json').write_text(json.dumps(D,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(D['batch_16m'],indent=2))
