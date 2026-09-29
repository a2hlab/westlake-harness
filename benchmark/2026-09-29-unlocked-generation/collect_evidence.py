#!/usr/bin/env python3
"""Collect bounded, hash-bound evidence; raw captures stay on the Mac/VM."""
import hashlib,json,re,shutil
from pathlib import Path
E=Path(__file__).resolve().parent;W=E.parents[2];S='5ea34a4500000000000000001123012c';BASE=W/'westlake-generation-state'/S
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(E/'screens').mkdir(exist_ok=True);(E/'evidence').mkdir(exist_ok=True)
old=json.loads((E/'results.json').read_text()) if (E/'results.json').exists() else {}
r={'task':68,'serial':S,'generation':'74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac','package':str(W/'westlake-generation-v3-74d1d6d4'),'user_override':'fd-android substitutes fd-k9; approved in conversation before board acceptance','outer_visual_review':'pending','apps':{},'sqlite_native_open':'unverified: registration found, no successful invocation receipt; later Java startup failures remain','source':json.loads((E/'source-preservation.json').read_text()),'negative_package':json.loads((E/'negative-package.json').read_text())}
r.update({k:v for k,v in old.items() if k in ['lifecycle','rollback','validation','final_state','conclusion','bridge_ab','final_helloworld','final_package','final_bridge','final_r8b_overlay','control','batch_16m']})
patterns=['providers populated','Caused by:','KoinApplication','ClassCastException','SQLiteConnection::nativeOpen','SQLiteConnection.nativeOpen','Opened connection','nativeParseManifestJson','nativeGetSysProp','J_invokeStaticMain_main_threw','exact adapter bridge admission failed','LOAD_ERROR','WLSCPL_ERROR_ARTIFACT_IDENTITY','[B43-BIND]','WorkManager is not initialized','AndroidAlarmManager','Missing method']
cases=[('control-zigzag','b68-control-d0f2-correct-5ea','zigzag','B5','white window'),('swap-helloworld','b68-swap-84695d62-5ea','helloworld','B5','own UI'),('b5-fd-android','b68-v3-74d1d6d4-5ea','fd-android','B5','desktop'),('b5-ooniprobe','b68-v3-ooni-zigzag-5ea','ooniprobe','B5','desktop'),('b5-zigzag','b68-v3-ooni-zigzag-5ea','zigzag','B5','white window'),('r8b-fd-android','b68-v3-r8b-5ea','fd-android','r8b','desktop'),('r8b-ooniprobe','b68-v3-r8b-5ea','ooniprobe','r8b','desktop'),('swap-zigzag','b68-swap-zigzag-5ea','zigzag','B5','pending'),('rollback-zigzag','b68-rollback-6cb-5ea','zigzag','B5','pending'),('final-zigzag','b68-v3-bc1d2f77-5ea','zigzag','B5','white window'),('final-fd-android','b68-v3-bc1d2f77-5ea','fd-android','B5','desktop'),('final-ooniprobe','b68-v3-bc1d2f77-5ea','ooniprobe','B5','desktop'),('final-r8b-fd-android','b68-v3-bc1d2f77-r8b-5ea','fd-android','r8b','desktop'),('final-r8b-ooniprobe','b68-v3-bc1d2f77-r8b-5ea','ooniprobe','r8b','desktop')]
for label,run,key,jar,visual in cases:
 src=BASE/run/key
 if not (src/'record.json').exists():continue
 dst=E/'evidence'/label;dst.mkdir(exist_ok=True)
 rec=json.loads((src/'record.json').read_text());log=src/'hilog.txt';text=log.read_text()
 hits=[{'line':i,'text':s} for i,s in enumerate(text.splitlines(),1) if any(k in s for k in patterns)]
 (dst/'hilog-excerpt.txt').write_text(''.join(f'{x["line"]}: {x["text"]}\n' for x in hits))
 for name in ['record.json','timeline.txt']:
  shutil.copyfile(src/name,dst/name)
 for p in src.glob('child-*-maps.txt'):shutil.copyfile(p,dst/p.name)
 for p in src.glob('child-proof-*'):
  if p.suffix in ['.sha256','.late-sha256','.maps','.late-maps']:shutil.copyfile(p,dst/p.name)
 screens={}
 for tag in ['t3','final']:
  q=E/'screens'/f'{label}-{tag}.jpeg';shutil.copyfile(src/(tag+'.jpeg'),q);screens[tag]={'path':str(q.relative_to(E)),'sha256':sha(q)}
 r['apps'][label]={'jar':jar,'package':rec['package'],'raw':str(src),'hilog_sha256':sha(log),'hilog_excerpt':str((dst/'hilog-excerpt.txt').relative_to(E)),'providers':[int(x) for x in re.findall(r'providers populated:\s*(\d+)',text)],'old_koin_wall':text.count('KoinApplication has not been started'),'application_cast_error':any('ClassCastException' in l and 'Application' in l for l in text.splitlines()),'admission_errors':{s:text.count(s) for s in ['exact adapter bridge admission failed','LOAD_ERROR','WLSCPL_ERROR_ARTIFACT_IDENTITY']},'sqlite_registration':text.count('SQLiteConnection::nativeOpen'),'sqlite_success_receipt':text.count('Opened connection'),'captured':rec.get('captured','unknown'),'capture_records':rec.get('screenshots',[]),'survivors':rec['pids_after'],'visual_inner':old.get('apps',{}).get(label,{}).get('visual_inner',visual),'screens':screens}
# Original full deployment HelloWorld evidence.
src=BASE/'attempt-1790664483304772604/helloworld';dst=E/'deployment';dst.mkdir(exist_ok=True)
for n in ['record.json','sha256.json','gate.json','maps.txt']:shutil.copyfile(src/n,dst/n)
q=E/'screens/helloworld-final.jpeg';shutil.copyfile(src/'final.jpeg',q)
r['helloworld']={'gate':json.loads((dst/'gate.json').read_text()),'visual_inner':'own UI','screen':str(q.relative_to(E)),'sha256':sha(q)}
src=BASE/'b68-v3-r8b-5ea-overlay/receipt.json';shutil.copyfile(src,E/'r8b-overlay-receipt.json');r['r8b_overlay']=json.loads(src.read_text())
(E/'results.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');print('collected',len(r['apps']),'captures')
