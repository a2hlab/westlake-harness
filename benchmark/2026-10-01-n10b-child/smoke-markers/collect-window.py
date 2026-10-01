"""Copy facts verbatim and index screenshots; never classify UI from logs or delete raw data."""
import json,re,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if (p/'scripts/lab/u7_executor.py').exists())
root=H/'board5cd-a118aca0-r3';runner=root/'runner';out=root/'summary';out.mkdir(exist_ok=True)
rows=[];facts=[]
for p in sorted(runner.rglob('facts.txt')):
 facts.append(str(p.relative_to(R))+'\n'+p.read_text())
for p in sorted(runner.rglob('record.json')):
 d=json.loads(p.read_text());key=p.parent.name
 t20=p.parent/'t20.jpeg';log=p.parent/'hilog.txt'
 row={'key':key,'record':str(p.relative_to(R)),'t20':str(t20.relative_to(R)) if t20.exists() else None,'role':'probe' if key=='probe' else 'app','status':d.get('status'),'screenshots':d.get('screenshots'),'observed_pids':d.get('observed_pids')}
 if log.exists():
  lines=log.read_text(errors='replace').splitlines()
  row['unknown_session_id_count']=sum('unknown sessionId' in l for l in lines)
  row['native_markers']=[l for l in lines if '[N10b-' in l or 'mObject cached in runtime' in l or 'setJavaVM initialized' in l]
  row['first_observed_fatal']=next((l for l in lines if re.search(r'FATAL EXCEPTION|Reason:Signal:SIG(?:SEGV|ABRT)|JNI DETECTED ERROR',l)),None)
  if key=='cv2-org-linaro-glmark2':
   row['getlongfield_stack']=[l for l in lines if 'GetLongField' in l or 'AAssetManager_fromJava' in l or 'getSceneInfo' in l]
 rows.append(row)
(out/'facts-all.txt').write_text('\n'.join(facts))
(out/'records-index.json').write_text(json.dumps(rows,indent=2)+'\n')
reader=R.parent/'westlake-harness-wiki/benchmark/2026-10-01-wikipedia-line/read80/read80.py'
for row in rows:
 if row['key'] in ['wikipedia','fd-app','fd-shatteredpixeldungeon','cv2-com-bytehamster-flowitgame','cv2-org-andresoviedo-dddmodel2','cv2-timur-webrtc-check']:
  log=R/row['record'];log=log.parent/'hilog.txt'
  r=subprocess.run([sys.executable,str(reader),'--key',row['key'],'--hilog',str(log)],capture_output=True,text=True)
  (out/('read80-'+row['key']+'.txt')).write_text(r.stdout)
  if r.returncode:print('read80 returned',r.returncode,row['key'],r.stderr)
print('indexed',len(rows),'records',len(facts),'facts files')
