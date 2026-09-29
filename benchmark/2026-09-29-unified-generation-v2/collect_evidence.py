#!/usr/bin/env python3
"""Copy bounded public evidence; retain raw capture paths and full log digests."""
import hashlib,json,re,shutil
from pathlib import Path
E=Path(__file__).resolve().parent
BASE=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state')
S='5ea34a4500000000000000001123012c'
RAW=BASE/S/'b67-v2-15728be5-5ea'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
(E/'screens').mkdir(exist_ok=True);(E/'evidence').mkdir(exist_ok=True)
result={'task':67,'serial':S,'generation':'15728be51105ef4c0df40c3dbc8cc7b15081efa8bf01866d02f9227039e490be','package':'/Users/zhaoyue/orca/workspaces/westlake-generation-v2-15728be5','apps':{},'sqlite_wall':'unverified: KoinApplication prerequisite prevents reaching nativeOpen','flutter_wall':'verified: app-domain rejection replaced by thread READY rejection','new_lit_count':0,'outer_visual_review':'pending','identity':json.loads((E/'deployment/gate.json').read_text()),'raw':str(RAW)}
for key in ['fd-android','fd-libre','zigzag']:
 src=RAW/key;dst=E/'evidence'/key;dst.mkdir(exist_ok=True)
 rec=json.loads((src/'record.json').read_text())
 for name in ['record.json','timeline.txt']:
  shutil.copyfile(src/name,dst/name)
 for p in src.glob('child-proof-*'):
  if p.suffix in ['.sha256','.late-sha256','.maps','.late-maps']:shutil.copyfile(p,dst/p.name)
 for name in ['t3','final']:
  shutil.copyfile(src/(name+'.jpeg'),E/'screens'/(key+'-'+name+'.jpeg'))
 log=src/'hilog.txt';lines=log.read_text().splitlines()
 patterns=['J_invokeStaticMain_main_threw','Caused by:','path is outside app domain','current thread is not READY','SQLiteConnection::nativeOpen','SQLiteGlobal::','B43-BIND','WLCGATE','[ROUTE-A] stock stage31','RsFrameReportExt:','directly return','SIGCHAIN','libflutter.so']
 hits=[{'line':i,'text':l} for i,l in enumerate(lines,1) if any(x in l for x in patterns)]
 (dst/'hilog-excerpt.txt').write_text(''.join(f'{x["line"]}: {x["text"]}\n' for x in hits))
 result['apps'][key]={'pid_proofs':[p.name.split('-')[2].split('.')[0] for p in src.glob('child-proof-*.late-sha256')],'survivors':rec['pids_after'],'new_faults':rec['new_faults'],'hilog':str(log),'hilog_sha256':sha(log),'evidence':hits,'screens':{n:{'path':f'screens/{key}-{n}.jpeg','sha256':sha(E/'screens'/f'{key}-{n}.jpeg')} for n in ['t3','final']},'visual_inner':'own UI' if key=='zigzag' else 'desktop','lit':key=='zigzag'}
shutil.copyfile(E/'deployment/final.jpeg',E/'screens/helloworld-final.jpeg')
result['apps']['helloworld']={'pid':9487,'visual_inner':'own UI','lit':True,'screen':'screens/helloworld-final.jpeg','sha256':sha(E/'screens/helloworld-final.jpeg')}
old=BASE/S/'b67-baseline-libre-5ea/fd-libre/hilog.txt'
if old.exists():
 hits=[{'line':i,'text':l} for i,l in enumerate(old.read_text().splitlines(),1) if 'path is outside app domain' in l]
 (E/'evidence/flutter-before.txt').write_text(''.join(f'{x["line"]}: {x["text"]}\n' for x in hits));result['flutter_baseline']={'path':str(old),'sha256':sha(old),'errors':hits}
result['validation']={'known_answers':{'total':69,'skip':2,'fail':0},'anl_host':{'checks':136,'fail':0,'negative_original_checks':136,'negative_original_fail':1},'deployment_tests':18,'generation_state_tests':2,'closure_libraries':319,'closure_edges':2830,'closure_negative_controls':json.loads((E/'closure-negatives.json').read_text())}
result['lifecycle']={}
for key in ['b6','b7']:
 d=json.loads((E/f'lifecycle-{key}.json').read_text())
 result['lifecycle'][key]=[{'scenario':r['scenario_name'],'verdict':r['verdict']} for r in d['verification']['results']]
result['lifecycle_note']='Unmodified inherited B6/B7 checks read prior reports, not this #67 report; their verdicts are preserved, not used as a substitute for fresh board evidence.'
write(E/'results.json',result)
print('Collected',len(result['apps']),'apps')
