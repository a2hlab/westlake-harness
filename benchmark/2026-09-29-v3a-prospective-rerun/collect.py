#!/usr/bin/env python3
"""Retain master facts and fatal-event excerpts; never treat a caught JNI error as fatal."""
import hashlib,json,re,shutil,sys
from pathlib import Path
E=Path(__file__).resolve().parent
S='5ea34a4500000000000000001123012c'
BASE=E.parents[2]/'westlake-generation-state'/S/'b78-v3a-13-5ea/b78-v3a-13-5ea'/S
sys.path.insert(0,str(E.parents[2]/'westlake-harness/scripts/lab'))
import run_facts
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pred=json.loads((E/'predictions-before.json').read_text())
rows=[]
for before in pred['predictions']:
 key=before['key'];src=BASE/key
 if not (src/'record.json').exists():continue
 rec=json.loads((src/'record.json').read_text());out=E/'evidence'/key;out.mkdir(parents=True,exist_ok=True)
 for name in ['record.json','processes-t5.txt','processes-t20.txt']:
  if (src/name).exists():shutil.copyfile(src/name,out/name)
 f=run_facts.facts(src);log=src/'hilog.txt';ls=log.read_text(errors='replace').splitlines() if log.exists() else []
 candidates=[];bind=[];exits=[];hits=set()
 for i,l in enumerate(ls):
  if 'HDC_LOG' in l:continue
  fatal=('J_invokeStaticMain_main_threw:' in l or 'FATAL EXCEPTION:' in l or ('UNCAUGHT in thread' in l and ('main=true' in l or "'main'" in l)))
  native_exit=(key=='fd-netguard' and 'relocating failed: symbol not found.' in l and '/eu.faircode.netguard/' in l and 's=__errno ' in l and i+1<len(ls) and 'System.exit called, status: 1' in ls[i+1] and l.split()[2]==ls[i+1].split()[2])
  if native_exit:fatal=True
  if fatal:candidates.append({'line':i+1,'text':l,'kind':'native_loader_then_exit' if native_exit else 'uncaught_java'})
  if 'ensureBindApplication FAILED' in l:bind.append({'line':i+1,'text':l})
  if rec['package'] in l and ('exit with code:' in l or 'killed by signal' in l):exits.append({'line':i+1,'text':l})
  if fatal or any(x in l for x in ['Caused by:','providers populated','nativeParseManifestJson failed','[B8-SVC]','[B8-PROV]','[B8-PM]']) or (rec['package'] in l and 'exit with code:' in l):hits.update(range(max(0,i-2),min(len(ls),i+12)))
 (out/'hilog-excerpt.txt').write_text('\n'.join(f'{i+1}: {ls[i]}' for i in sorted(hits))+'\n')
 first=candidates[0] if candidates else None
 status='fatal' if first else ('alive_at_samples' if f['alive_t5'] and f['alive_t20'] else 'unknown: no uncaught event captured')
 match='unknown: no pre-run prediction for this APK'
 if before['prediction']!='unknown':
  match='unknown: insufficient exact causal link'
  if key=='ooniprobe' and before['prediction']=='service:jobscheduler' and any('nr2.a(' in l and ':10)' in l for l in ls) and any('WorkManager is not initialized' in l for l in ls):match='hit: nr2.a line10 dereferences getSystemService(jobscheduler), per pinned APK bytecode'
 screens=[]
 for shot in rec.get('screenshots',[]):
  if not shot.get('captured'):continue
  name=Path(shot.get('path','')).name
  if name and (src/name).is_file():
   shutil.copyfile(src/name,out/name);screens.append({'path':str((out/name).relative_to(E)),'sha256':sha(out/name)})
 rows.append({'key':key,'package':rec['package'],'apk_sha256':rec.get('apk_sha256'),'facts':f,'first_fatal':first,'fatal_candidates':candidates,'bind_errors':bind,'exit_lines':exits,'runtime_status':status,'prediction':before['prediction'],'prediction_line':before.get('line'),'prediction_match':match,'raw':str(src),'hilog_sha256':sha(log) if log.exists() else None,'screens':screens})
for name in ['facts.txt','preflight.json','plan.json','summary.json']:
 if (BASE/name).exists():shutil.copyfile(BASE/name,E/name)
result={'task':78,'run':str(BASE),'profile':'v3a+r8b','prediction_frozen_at':pred['frozen_at'],'prediction_source_sha256':pred['source_sha256'],'apps':rows,'backtest':{'pre_run_predictions':sum(x['prediction']!='unknown' for x in rows),'hits':sum(x['prediction_match'].startswith('hit:') for x in rows),'no_prediction':sum(x['prediction']=='unknown' for x in rows),'scope':'Only the frozen OONI row is eligible; other APKs had no matching row. No post-run prediction filling.'},'visual_review':'outer pending; no lighting inferred from processes or focus gate'}
(E/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for r in rows:print(r['key'],r['runtime_status'],r['first_fatal']['text'] if r['first_fatal'] else '',r['prediction_match'])
