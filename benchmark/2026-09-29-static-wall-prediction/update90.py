#!/usr/bin/env python3
"""Offline outcome-informed revision; never modifies frozen task85 outputs."""
import argparse,csv,hashlib,json,re,shutil,datetime
from pathlib import Path
from collections import Counter,defaultdict
HERE=Path(__file__).resolve().parent
WORK=HERE.parents[1].parent
ROOT=Path('/Users/zhaoyue/orca/workspaces')
RUN=ROOT/'westlake-harness-walls/benchmark/2026-09-29-westlake-port/runs/r15cfull-20260929T183604/5cd1e3dd00000000000000000923012c'
TRIAGE=ROOT/'westlake-harness-b4/benchmark/2026-09-29-wikipedia-diff/r15cfull-triage.json'
BOARD=ROOT/'westlake-harness/.octos/boards/app-lighting.md'
OUT=HERE/'task90-r15c'
LIT={'aegis','fd-AppManager','fd-droidify','noice','fd-noice','fd-stk'}
VISUAL={**{k:'own-ui' for k in LIT},'fd-fitness':'crash-dialog','anki':'black','vlc':'black',**{k:'blank' for k in ['fd-binaryeye','fd-filemanager','fd-gallery','fd-notes']}}
# Match exceptions or stack frames, never class-linker method inventories.
RULES=[
 ('jobscheduler-startup','stub_ok',r'(?:NullPointerException.*(?:JobScheduler|jobScheduler)|at .*JobSchedulerExtKt\.getWmJobScheduler)', 'Reuse cc-wiki OnlineJobScheduler: non-null typed object, namespace/cancel/schedule results; background scheduling need not be functional for first screen.'),
 ('shortcutmanager','stub_ok',r'NullPointerException.*ShortcutManager', 'Return a typed non-null ShortcutManager and safe empty/boolean results; dynamic launcher shortcuts are outside first-screen scope.'),
 ('common-event-jni','needs_real',r'No implementation found for .*ActivityManagerAdapter\.native(?:Subscribe|Publish)CommonEvent', 'Restore matching RegisterNatives signatures and CommonEvent bridge; do not hide missing JNI behind a success return.'),
 ('velocitytracker-jni','needs_real',r'No implementation found for .*VelocityTracker\.', 'Restore real VelocityTracker JNI registration/implementation for the loaded framework generation.'),
 ('guest-thread-ready','needs_real',r'UnsatisfiedLinkError: current thread is not READY for guest dlopen', 'Restore guest-thread entry protocol before Flutter/native loads; connectivity alone does not repair this.'),
 ('app-native-loader','needs_real',r'(?:UnsatisfiedLinkError: .*dlopen_ns failed|relocating failed: symbol not found.*dso=/data/)', 'Resolve app-library namespace/dependencies and required bionic symbol implementations using the exact failing library.'),
 ('jna-native-resource','needs_real',r'UnsatisfiedLinkError: Native library .*libjnidispatch', 'Restore APK/native resource extraction and JNA library lookup.'),
 ('sharedpreferences-null','needs_real',r'NullPointerException:.*SharedPreferences', 'Restore Context preferences object and persistence contract; returning null or empty volatile storage is not equivalent.'),
 ('window-type-flags','needs_real',r'InvalidDisplayException:.*window type', 'Reuse verified addToDisplay/relayout mapping; r15c still fails markor, so do not mark family globally repaired.'),
 ('theme-appcompat','needs_real',r'IllegalStateException: You need to use a Theme.AppCompat', 'Restore actual theme/resource projection.'),
 ('egl-camera-jni','needs_real',r'No implementation found for .*(?:gles_jni.EGLImpl|android.hardware.Camera)', 'Restore correct EGL/camera JNI entry points; camera first-screen requirements must be checked before proposing empty enumeration.'),
 ('coroutine-class-warning','unknown',r'ClassNotFoundException: kotlinx.coroutines.CoroutineStart', 'Known tolerated adapter warning also appears on accepted STK; investigate only, not proven cause of blank UI.'),
 ('connectivity-interface-warning','unknown',r'(?:ClassNotFoundException: android.net.IConnectivityManager|ClassNotFoundException: android/net/IConnectivityManager)', 'Reuse cc-wiki OnlineConnectivityManager/classloader fix; class warning alone is not proof of the current visual blocker.'),
 ('network-permission','needs_real',r'(?:missing INTERNET permission|android_getaddrinfo failed: EPERM)', 'Require actual child supplementary gid 3003 plus installed HAP ohos.permission.INTERNET; reinstall using corrected installer and verify real request.'),
 ('application-init','unknown',r'(?:KoinApplication has not been started|lateinit property .*not been initialized|NoClassDefFoundError: com.amaze.filemanager.application.AppConfig)', 'Inspect earlier Application/provider failure; these can be downstream symptoms, not independent service fixes.'),
]
REGEX=[(f,p,re.compile(rx),a) for f,p,rx,a in RULES]
PRIOR_MAP={'app-native-loader':'native-bionic-header'}

def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def table(p,rows,fields=None):
 p.parent.mkdir(parents=True,exist_ok=True)
 fields=fields or list(rows[0])
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) or v is None else v for k,v in r.items()})
def target_processes(text,uid):
 if uid is None:return None
 rows=[]
 for n,s in enumerate(text.splitlines(),1):
  m=re.match(r'\s*(\d+)\s+(\d+)\s+(\d+)\s+(.+)',s)
  if m and int(m[3])==int(uid):rows.append({'line':n,'pid':int(m[1]),'ppid':int(m[2]),'uid':int(m[3]),'name':m[4].strip()})
 return rows

def network_candidate(visual,families):
 return visual=='own-ui' and 'network-permission' in families

def main(out=OUT,run=RUN,triage_path=TRIAGE):
 from backtest85 import verify_freeze
 freeze=verify_freeze()
 out.mkdir(parents=True,exist_ok=True)
 prior={r['app']:r for r in load(HERE/'v4-r2/predictions.json')}
 static=list(csv.DictReader((HERE/'v4-r2/hits.csv').open()))
 triage=load(triage_path);observed={r['key']:r for g in triage['runs'].values() for r in g['rows']}
 plan=load(run/'plan.json');sources=[]
 def copy(p,rel):
  dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
  sources.append({'source':str(p),'snapshot':rel,'sha256':sha(p)});return dest
 copy(triage_path,'evidence/r15c-triage.json');copy(run/'facts.txt','evidence/facts.txt');copy(run/'plan.json','evidence/plan.json')
 board=[]
 for n,line in enumerate(BOARD.read_text(errors="replace").splitlines(),1):
  if any(x in line for x in ['读图签认(#82','128KiB','128KB','PROGRESS(89)','ACK(89','PROGRESS(90)','两层','d977bd15','6f94d4f4','gid 3003']):board.append({'line':n,'text':line})
 dump(out/'evidence/board-excerpts.json',{'source':str(BOARD),'sha256':sha(BOARD),'lines':board})
 accepted_line=next(x['line'] for x in board if '读图签认(#82' in x['text'])
 rows=[];hits=[];net=[];prior_rows=[]
 for app in plan['apps']:
  key=app['key'];base=run/key;rec=load(base/'record.json');copy(base/'record.json',f'evidence/records/{key}/record.json')
  uid=rec.get('bms',{}).get('uid');ps={}
  for when in ['t5','t10','t20']:
   path=base/f'processes-{when}.txt'
   ps[when]=target_processes(path.read_text(),uid) if path.exists() else None
   if path.exists():copy(path,f'evidence/records/{key}/{path.name}')
  pids={str(x['pid']) for entries in ps.values() for x in (entries or [])}
  t=observed.get(key,{})
  if t.get('pid'):pids.add(str(t['pid']))
  visual=VISUAL.get(key,'not-adjudicated')
  logpath=base/'hilog.txt';linehits=defaultdict(list)
  if logpath.exists():
   lines=logpath.read_text(errors='replace').splitlines()
   for n,line in enumerate(lines,1):
    m=re.match(r'\S+\s+\S+\s+(\d+)\s+',line)
    if not m or m[1] not in pids or '[IFACE-' in line:continue
    for family,policy,rx,action in REGEX:
     if rx.search(line):
      if len(linehits[family])<3:linehits[family].append({'line':n,'text':line,'context':lines[n:min(n+3,len(lines))]})
   sources.append({'source':str(logpath),'snapshot':f'evidence/logs/{key}.json','sha256':sha(logpath),'partial_excerpt':True})
  dump(out/f'evidence/logs/{key}.json',{'source':str(logpath),'target_pids':sorted(pids),'families':linehits})
  actual=[]
  for family,policy,rx,action in REGEX:
   if family not in linehits:continue
   entry=linehits[family][0]
   # These are observed startup exceptions, not automatically first fatal causes.
   role='tolerated-on-accepted-ui' if key in LIT and family!='network-permission' else 'content-network-denial' if family=='network-permission' else 'startup-failure-candidate' if policy!='unknown' else 'diagnostic-only'
   h={'app':key,'family':family,'policy':policy,'stub_ok':policy=='stub_ok','needs_real':policy=='needs_real','role':role,'startup_observed':role=='startup-failure-candidate','first_line':entry['line'],'source':str(logpath)+':'+str(entry['line']),'evidence':f'evidence/logs/{key}.json','action':action}
   hits.append(h);actual.append(h)
  current=[h for h in sorted(actual,key=lambda x:x['first_line']) if h['role'] in ['startup-failure-candidate','content-network-denial']]
  old=prior.get(key);identity='exact' if old and old['apk_sha256']==rec.get('apk_sha256') else 'mismatch' if old else 'not-scanned'
  first=current[0]['family'] if current else 'none-observed-blocking' if key in LIT else 'unknown'
  direct=network_candidate(visual,linehits)
  row={'app':key,'apk_sha256':rec.get('apk_sha256'),'package':rec.get('package'),'observed_profile':'v3a+r15c be7731a4 on 5cd before network rollout','next_profile':'r16 plus dual-layer networking, pending verification','prior_static_identity':identity,'visual':visual,'visual_evidence':f'{BOARD}:{accepted_line}' if key in VISUAL else 'unknown','captured':sum(s.get('captured') is True for s in rec.get('screenshots',[])),'shot_records':len(rec.get('screenshots',[])),'alive_t5':bool(ps['t5']) if ps['t5'] is not None else None,'alive_t10':bool(ps['t10']) if ps['t10'] is not None else None,'alive_t20':bool(ps['t20']) if ps['t20'] is not None else None,'t5_processes':ps['t5'],'record':f'evidence/records/{key}/record.json','raw_triage_class':t.get('class','unknown'),'raw_triage_fatal':t.get('fatal'),'next_first_wall_candidate':first,'observed_wall_order':[h['family'] for h in current],'stub_ok':[h['family'] for h in current if h['stub_ok']],'needs_real':[h['family'] for h in current if h['needs_real']],'diagnostic_unknowns':[h['family'] for h in actual if h['policy']=='unknown'],'prior_latent_static_order':old['new_family_order'] if identity=='exact' else [],'prior_static_status':'retained as latent r13 risk; not confirmed unresolved on r15c' if old else 'outside original 32 APK scan','network_may_directly_light':direct,'network_outcome':'may-load-online-content; own UI already accepted' if direct else 'not-proven-network-only','prediction_basis':'retrospective revision; order is first matched target-PID startup evidence, not proven causal order','r16_status':'not-tested','unknown_reason':'install-or-launch failed before screenshot' if not rec.get('screenshots') else 'blank/black cause unresolved' if visual in ['blank','black'] else ''}
  rows.append(row)
  manifest=HERE/f'v3/classes/evidence/manifest-{key}.txt'
  internet='unknown';permref='unknown'
  if manifest.exists() and identity=='exact':
   ml=manifest.read_text().splitlines();found=[n for n,s in enumerate(ml,1) if 'android.permission.INTERNET' in s];internet=bool(found);permref=str(manifest)+(':'+str(found[0]) if found else '')
  net.append({'app':key,'package':rec.get('package'),'visual':visual,'apk_internet_declared':internet,'manifest_evidence':permref,'observed_network_denial':'network-permission' in linehits,'network_may_directly_light':direct,'benefit':'online-content-recovery, not a new own-UI count' if direct else 'conditional beneficiary only; other walls or evidence gaps remain','required_child_gid':3003,'required_hap_permission':'ohos.permission.INTERNET','required_reinstall':True,'network_state_permission':'ohos.permission.GET_NETWORK_INFO if APK ACCESS_NETWORK_STATE','r15c_child_gid_observed':'unknown','r15c_hap_permission_observed':'unknown','post_fix_http_result':'unknown','evidence':f'evidence/logs/{key}.json','additional_walls':[h['family'] for h in current if h['family']!='network-permission']+(['later Wiki 128KiB-stack/PNG fault reported on different 5ea profile; separate from r15c'] if key=='wikipedia' else [])})
  prior_rows.append({'app':key,'identity':identity,'previous_order':old['new_family_order'] if old else [],'revised_order':row['observed_wall_order'],'visual':visual,'resolution':'accepted first-screen errors censored, not globally repaired' if key in LIT else 'current PID evidence takes precedence; unknowns retained'})
 ranks=[]
 for family,policy,rx,action in REGEX:
  hh=[h for h in hits if h['family']==family]
  blocking=[h for h in hh if h['startup_observed']]
  content=[h for h in hh if h['role']=='content-network-denial']
  st=[s for s in static if s['family']==PRIOR_MAP.get(family,family)]
  ranks.append({'family':family,'policy':policy,'stub_ok':policy=='stub_ok','needs_real':policy=='needs_real','rank':0,'startup_affected_app_keys':len({h['app'] for h in blocking}),'startup_apps':sorted({h['app'] for h in blocking}),'content_recovery_app_keys':len({h['app'] for h in content}),'content_apps':sorted({h['app'] for h in content}),'all_observed_app_keys':len(hh),'tolerated_on_accepted_apps':[h['app'] for h in hh if h['role']=='tolerated-on-accepted-ui'],'prior_static_reference_count':sum(int(s['callsite_count']) for s in st) if st else None,'prior_static_startup_app_keys':sum(s['startup_reachable']=='yes-static' for s in st) if st else None,'count_unit':'app input key, not unique package; shared latent walls are not additive lighting gains','action':action,'evidence':[h['source'] for h in blocking+content]})
 for policy in ['stub_ok','needs_real','unknown']:
  group=sorted([r for r in ranks if r['policy']==policy],key=lambda x:(-x['startup_affected_app_keys'],-x['content_recovery_app_keys'],x['family']))
  for n,r in enumerate(group,1):r['rank']=n
  table(out/f'walls-{policy}.csv',group)
 table(out/'predictions.csv',rows);dump(out/'predictions.json',rows);table(out/'observed-wall-hits.csv',hits);table(out/'network-candidates.csv',net);table(out/'prediction-delta.csv',prior_rows);dump(out/'wall-ranking.json',ranks)
 dump(out/'network-contract.json',{'required_together':['BMS child supplementary gid 3003','installed synthesized HAP ohos.permission.INTERNET'], 'install_action':'reinstall APK with #89 corrected installer; refreshing runtime alone cannot add installed HAP permission','5ea':'outer reports components patched; app-specific network result not inferred','5cd_61b':'pending #90 rollout at prediction cutoff','components':{'appspawn-x':'d977bd15','libbms':'6f94d4f4','libapk_installer':'eb6824b4'},'direct_candidates':[r['app'] for r in net if r['network_may_directly_light']]})
 result={'task':90,'scope':'cx-bms first-step offline scan only','generated_at':datetime.datetime.now().astimezone().isoformat(),'apps':len(rows),'exact_prior_static_apks':sum(r['prior_static_identity']=='exact' for r in rows),'outside_prior_static':sum(r['prior_static_identity']=='not-scanned' for r in rows),'captured':sum(r['captured'] for r in rows),'shot_records':sum(r['shot_records'] for r in rows),'alive_t5':sum(r['alive_t5'] is True for r in rows),'alive_t5_unknown':sum(r['alive_t5'] is None for r in rows),'alive_t20':'unknown: no t20 process snapshots','outer_accepted_keys':sorted(LIT),'network_direct_candidates':[r['app'] for r in net if r['network_may_directly_light']],'prospective_hit_rate':None,'evaluation_note':'revision consumes r15c observations; score on the next run, not on its own input','prior_freeze_verified':True,'prior_frozen_at':freeze['frozen_at'],'tests':'pending'}
 dump(out/'results.json',result)
 dump(out/'input-manifest.json',{'sources':sources,'prior_predictions_sha256':sha(HERE/'v4-r2/predictions.json'),'prior_freeze_sha256':sha(HERE/'v4-r2/freeze.json'),'scanner_sha256':sha(Path(__file__))})
 print(json.dumps(result,ensure_ascii=False))
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);p.add_argument('--run',type=Path,default=RUN);p.add_argument('--triage',type=Path,default=TRIAGE);a=p.parse_args();main(a.out,a.run,a.triage)
