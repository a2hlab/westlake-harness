#!/usr/bin/env python3
"""Derive bounded static candidates first, then join existing observations."""
import collections,csv,json,re,subprocess
from pathlib import Path
from scan_jni import HERE,BASE,REPO,R8HASH,sha
from scan_apps import INPUT,load_apps
WL=BASE/'westlake-harness-walls/benchmark/2026-09-29-westlake-port'
INV=BASE/'westlake-harness/benchmark/2026-09-29-westlake-port/INVENTORY.md'
WLSRC=Path('/Users/zhaoyue/orca/westlake/westlake-deploy-ohos/v3-hbc')
WORKSPACE=Path('/Users/zhaoyue/orca/00.Workspace/src/adapter')
def dump(name,data):(HERE/name).write_text(json.dumps(data,indent=2)+'\n')
def csvwrite(name,rows,fields):
 with (HERE/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(r[k],separators=(',',':')) if isinstance(r[k],(dict,list)) else r[k] for k in fields})

def main():
 # Preserve accepted v3 outputs and outer approvals when an older command is reused.
 if (HERE/'v3/jni-summary.json').exists():
  from finalize_v3 import main as finalize_current
  return finalize_current()
 reach_path=HERE/'reachability-results.json';reach={x['key']:x for x in json.loads(reach_path.read_text())} if reach_path.exists() else {}
 jni=json.loads((HERE/'jni-results.json').read_text());apps=load_apps();runtime=json.loads((HERE/'evidence/runtime-disassembly.json').read_text())
 def proof(method,pattern=None):
  return [{'file':r['jar'],'sha256':r['jar_sha256'],'dex':r['dex'],'line':r['line'],'method':r['method'],'instruction':r['text']} for r in runtime if r['method'].startswith(method) and (pattern is None or pattern in r['text'])]
 registry={};regs={};last_origin=None
 for r in runtime:
  if not r['method'].startswith('android.app.SystemServiceRegistry.<clinit>'):continue
  origin=(r['jar'],r['dex'],r['method'])
  if origin!=last_origin:regs={};last_origin=origin
  t=r['text'];m=re.search(r'const-string(?:/jumbo)? (v\d+), "([^"]+)"',t);c=re.search(r'const-class (v\d+), L([^;]+);',t);n=re.search(r'new-instance (v\d+), L([^;]+);',t)
  if m:regs[m[1]]=('string',m[2],r)
  if c:regs[c[1]]=('class',c[2],r)
  if n:regs[n[1]]=('factory',n[2],r)
  call=re.search(r'invoke-static \{([^}]+)\}, Landroid/app/SystemServiceRegistry;\.registerService:',t)
  if call:
   args=re.findall(r'v\d+',call[1]);values=[regs.get(x) for x in args]
   if len(values)==3 and all(values) and [v[0] for v in values]==['string','class','factory']:
    name,cls,factory=values;registry.setdefault(name[1],[]).append({'service':name[1],'manager_class':cls[1],'factory_class':factory[1],'file':r['jar'],'sha256':r['jar_sha256'],'dex':r['dex'],'line':r['line'],'instruction':t})
 dump('evidence/service-registry.json',registry)
 lookup=proof('adapter.core.OHServiceManager.lookupAdapter')
 provided=set()
 for r in lookup:
  m=re.search(r'const-string \w+, "([a-z_]+)"',r['instruction'])
  if m:provided.add(m[1])
 installed=set()
 for r in proof('adapter.activity.B8BindExtras.<clinit>'):
  m=re.search(r'const-string \w+, "([a-z_]+)"',r['instruction'])
  if m:installed.add(m[1])
 assert installed=={'account','alarm','appops','uimode','locale'}
 invlines=INV.read_text().splitlines();wlonly={'connectivity':11,'location':13,'permissionmgr':13,'webviewupdate':12,'batteryproperties':9,'batterystats':9,'telephony.registry':8}
 def coverage(service):
  if service=='unknown':return 'unknown',[], 'Argument not resolved; no assumption about service name.'
  if service=='user':return 'r8b-stub',proof('adapter.activity.UserManagerProjectionProxy.install','"user"')+registry.get(service,[]),'Pinned r8b installs a child-local IUserManager proxy; static presence, not behavior.'
  if service in installed:return 'r8b-stub',proof('adapter.activity.B8BindExtras.<clinit>',f'"{service}"')+registry.get(service,[]),'Pinned r8b B8BindExtras installs LocalServiceBinders in ServiceManager.sCache.'
  if service in provided and service in registry:return 'provided',proof('adapter.core.OHServiceManager.lookupAdapter',f'"{service}"')+registry[service],'Non-null adapter/stub branch exists in pinned route-A JAR; not a full API implementation claim.'
  if service in wlonly:
   n=next(i+1 for i,l in enumerate(invlines) if re.match(r'\| '+str(wlonly[service])+r'\b',l))
   return 'westlake-only',[{'file':str(INV),'line':n,'text':invlines[n-1]}],'Absent from route-A lookup/cache; implementation listed in Westlake inventory, not copied into this overlay.'
  if service in {'notification','jobscheduler'}:
   return 'missing',[{'file':'evidence/runtime-disassembly.json','methods':['adapter.core.OHServiceManager.lookupAdapter','adapter.activity.B8BindExtras.<clinit>','adapter.activity.LocalServiceBinders.get'],'sha256':sha(HERE/'evidence/runtime-disassembly.json')},{'file':str(REPO/'bms/src/adapter/framework/mainline-stubs/java/android/app/job/JobSchedulerFrameworkInitializer.java'),'line':11}],'No named Binder route or r8b installation. JobScheduler additionally has a no-op service-wrapper initializer; classpath behavior is not inferred.'
  return 'unknown',[], 'Constant is resolved, but manager factory/Binder mapping has not been proved in the timebox.'
 services=[]
 for a in apps:
  grouped=collections.defaultdict(list)
  for c in a['calls']:grouped[c['service']].append(c)
  for service,calls in sorted(grouped.items()):
   status,evidence,reason=coverage(service)
   graph=reach.get(a['key'],{})
   if graph and graph['apk_sha256']!=a['sha256']:raise ValueError('reachability APK changed: '+a['key'])
   indexed={(c['dex'],c['method'],c['offset']):c for c in graph.get('calls',[])}
   paths=[{**indexed[(c['dex'],c['method'],c['offset'])],'service':service} for c in calls if indexed.get((c['dex'],c['method'],c['offset']),{}).get('startup_reachable')=='yes-static']
   services.append({'app':a['key'],'profile':'6cb40cd6+r8b / v3-74d1d6d4+r8b','service':service,'status':status,'call_count':len(calls),'reason':reason,'apk_sha256':a['sha256'],'calls':calls,'coverage_evidence':evidence,'registry':registry.get(service,[]),'startup_reachable':'yes-static' if paths else 'unknown','startup_call_count':len(paths),'startup_evidence':paths,'stub_ok':service in {'notification','jobscheduler','connectivity','location','permissionmgr','webviewupdate','batteryproperties','batterystats','telephony.registry','user','account','alarm','appops','uimode','locale'},'needs_real':service in {'activity','activity_task','window','display','input_method'},'policy_basis':'Outer #72 first-screen policy; stub must satisfy caller return-type/object contracts. Unknown reachability does not mean off-startup.'})
 csvwrite('service-matrix.csv',services,['app','profile','service','status','call_count','reason','apk_sha256','calls','coverage_evidence','registry','startup_reachable','startup_call_count','startup_evidence','stub_ok','needs_real','policy_basis']);dump('service-results.json',services)
 catalog=[]
 for service in sorted(set(s['service'] for s in services)):
  status,evidence,reason=coverage(service);catalog.append({'service':service,'status':status,'apps':sorted({s['app'] for s in services if s['service']==service}),'startup_apps':sorted({s['app'] for s in services if s['service']==service and s['startup_reachable']=='yes-static'}),'reason':reason,'evidence':evidence})
 dump('service-catalog.json',catalog)
 called={c['id'] for a in apps for c in a['native_calls']}
 call_evidence={a['key']:{'apk':a['apk'],'sha256':a['sha256'],'dexes':a['dexes'],'evidence':f'evidence/app-{a["key"]}.json'} for a in apps}
 dump('evidence/no-direct-call-scope.json',{'scope':'Exact invoke targets in every classes*.dex of 20 APKs. Does not rule out framework transitive calls, reflection or JNI lookup. No exception is approved automatically.','inputs':call_evidence})
 exceptions=[]
 for gen,data in jni.items():
  for m in data['methods']:
   if m['status'] in {'exported','registered'} or m['id'] in called or m['class'].startswith('adapter/'):continue
   # These known transitively-used classes are never exception candidates.
   if m['class'].startswith(('android/database/','android/graphics/','android/view/')):continue
   exceptions.append({'method':m['id'],'generation':data['generation'],'overlay_sha256':R8HASH,'status':m['status'],'approval':'proposed','approved_by':None,'reason':'No exact direct invoke in the scanned 20 APK dex sets; framework-transitive/reflection use remains unknown. Review required before approval.','evidence':['evidence/no-direct-call-scope.json',m['declaration']]})
 tf_log=Path('/Users/zhaoyue/orca/00.Workspace/evidence/runs/ab-compare/20260817-014130-8605-zigzag-apk-light-manual/hilog.log')
 tf_lines=tf_log.read_text(errors='replace').splitlines();tf_rows=[{'file':str(tf_log),'line':n,'text':line,'sha256':sha(tf_log)} for n,line in enumerate(tf_lines,1) if '[EARLY-TF]' in line and 'reflect FAILED' in line and 'nativePrimeDefaultTypeface' in line]
 dump('evidence/typeface-tolerated.json',{'observed':tf_rows,'outer_observation':'Outer #72 reports ZigZag was lit in this run; this scan does not re-adjudicate screenshots. Tolerance is a candidate exception, not proof for every app/generation.'})
 for gen,data in jni.items():
  for m in data['methods']:
   if m['method']=='nativePrimeDefaultTypeface' and m['class']=='adapter/activity/AppSchedulerBridge':
    exceptions.append({'method':m['id'],'generation':data['generation'],'overlay_sha256':R8HASH,'status':m['status'],'approval':'proposed','approved_by':None,'reason':'Outer-requested candidate: early Typeface reflective prime failed in a reported lit ZigZag run; failure can be tolerated on that route. Transfer to this generation/apps requires review.','evidence':tf_rows,'requester':'outer(claude), #72 second version','exception_kind':'observed-tolerated-failure'})
 dump('jni-allowlist.json',{'version':1,'draft':True,'policy':'Only approval=approved with approved_by, exact generation+overlay+method+status, reason and evidence is accepted. Any app-directly-called method is excluded. Proposals do not bypass the gate.','exceptions':exceptions})
 # Candidate ordering is a fixed heuristic, not a control-flow proof. No app-key rules.
 candidates=[];wallapps=collections.defaultdict(set);startupapps=collections.defaultdict(set);wallsource={};walltypes={}
 sqlite_src=str(WORKSPACE/'framework/android-runtime/src/android_database_SQLiteConnection.cpp')+':905'
 for gen,data in jni.items():
  sqlite=next(m for m in data['methods'] if m['class']=='android/database/sqlite/SQLiteConnection' and m['method']=='nativeOpen')
  for a in apps:
   rows=[s for s in services if s['app']==a['key']];gaps={s['service']:s for s in rows if s['status'] in {'missing','westlake-only'}};features=a['features'];manifest=a['manifest'];walls=[]
   def add(wall,priority,basis,source,confidence='candidate'):
    if wall.startswith('service:'):
     svc=next((r for r in rows if r['service']==wall.split(':',1)[1]),None);startup=svc['startup_reachable'] if svc else 'unknown';startup_evidence=svc['startup_evidence'] if svc else []
    else:
     feature={'sqlite-jni':'sqlite','jna-arm64-library':'jna','activity-theme':'appcompat'}.get(wall)
     f=reach.get(a['key'],{}).get('features',{}).get(feature,{})
     startup=f.get('startup_reachable','unknown');startup_evidence=f
    stub_ok=wall.startswith('service:');needs_real=not stub_ok
    walls.append({'wall':wall,'priority':priority,'confidence':confidence,'basis':basis,'copy_source':source,'startup_reachable':startup,'startup_evidence':startup_evidence,'stub_ok':stub_ok,'needs_real':needs_real});wallapps[(gen,wall)].add(a['key']);wallsource[(gen,wall)]=source;walltypes[(gen,wall)]=(stub_ok,needs_real)
    if startup=='yes-static':startupapps[(gen,wall)].add(a['key'])
   if sqlite['status']=='stub' and 'sqlite' in features:
    add('sqlite-jni',10 if 'koin' in features else 45,{'jni':sqlite['id'],'status':sqlite['status'],'reference':features['sqlite'],'koin_reference':'koin' in features},sqlite_src)
   if 'jna' in features:
    jnalibs=[x for x in a['native_libraries'] if 'jnidispatch' in x]
    if not any('/arm64-v8a/' in x for x in jnalibs):add('jna-arm64-library',15,{'reference':features['jna'],'packaged_jnidispatch':jnalibs},'两边都没有: requires matching APK/JNA library; no verified generic replacement')
   if 'workmanager' in features and 'jobscheduler' in gaps:
    add('service:jobscheduler',20,{'reference':features['workmanager'],'service':'missing','manifest_provider_count':manifest['provider_count']},'两边都没有: both supplied routes have no-op JobSchedulerFrameworkInitializer; real service implementation not located')
   if manifest.get('uses_appcompat'):
    add('activity-theme',30,{'dependency_only':True,'launch_activity':manifest['launch_activity'],'activity_theme':manifest.get('launch_theme_ref'),'application_theme':manifest.get('application_theme_ref'),'reason':'Theme propagation risk; dependency presence does not prove launch Activity inherits AppCompat or invalid resource.'},str(WORKSPACE/'framework/activity/java/ManifestComponentProjection.java'),'unknown')
   for s,r in sorted(gaps.items()):
    if s=='jobscheduler' and 'workmanager' in features:continue
    source=str(INV)+':'+str(r['coverage_evidence'][0]['line']) if r['status']=='westlake-only' else '两边都没有: no verified implementation located in pinned inventory'
    add('service:'+s,40 if s=='notification' else 50,{'call':r['calls'][0],'coverage':r['status']},source)
   walls.sort(key=lambda x:(x['startup_reachable']!='yes-static',x['priority'],x['wall']))
   if not walls:walls=[{'wall':'unknown','priority':99,'confidence':'unknown','basis':'No static blocking candidate proved; not a pass. Native runtime behavior is out of scope.','copy_source':'两边都没有','startup_reachable':'unknown','stub_ok':False,'needs_real':False}]
   candidates.append({'app':a['key'],'profile':gen+'+r8b','predicted_first':walls[0]['wall'],'wall_order':[w['wall'] for w in walls],'stub_ok':[w['wall'] for w in walls if w['stub_ok']],'needs_real':[w['wall'] for w in walls if w['needs_real']],'startup_known_walls':[w['wall'] for w in walls if w['startup_reachable']=='yes-static'],'runtime_followup':[{'wall':'flutter-path','stub_ok':False,'needs_real':True,'startup_reachable':'unknown','reason':'Flutter manifest/library reference; namespace/path behavior is outside offline scan scope, not a predicted static failure.'}] if manifest.get('flutter') else [],'ordering':'heuristic priority only; reachability and first execution order unproved','manifest_source':str(INPUT/'results.json'),'manifest':manifest,'features':features,'r8b_manifest':'Java ManifestJsonFallback present; native manifest JNI status remains independently reported. Effective class loading is runtime/out of scope.','walls':walls,'evidence':f'evidence/app-{a["key"]}.json'})
 csvwrite('predictions.csv',candidates,['app','profile','predicted_first','wall_order','stub_ok','needs_real','startup_known_walls','runtime_followup','ordering','manifest_source','manifest','features','r8b_manifest','walls','evidence'])
 ranked=[{'profile':g+'+r8b','wall':w,'stub_ok':walltypes[(g,w)][0],'needs_real':walltypes[(g,w)][1],'startup_affected_apps':len(startupapps[(g,w)]),'startup_apps':sorted(startupapps[(g,w)]),'full_reference_apps':len(keys),'apps':sorted(keys),'copy_source':wallsource[(g,w)],'meaning':'Startup count is static potential paths, not observed execution; unknowns deferred. Full-reference count includes off-path/unresolved references.'} for (g,w),keys in wallapps.items()]
 ranked.sort(key=lambda r:(not r['stub_ok'],-r['startup_affected_apps'],-r['full_reference_apps'],r['wall'],r['profile']));dump('wall-ranking.json',ranked)
 csvwrite('wall-ranking.csv',ranked,['profile','wall','stub_ok','needs_real','startup_affected_apps','startup_apps','full_reference_apps','apps','copy_source','meaning'])
 # Compare only after static predictions have been materialized.
 observations=[];prior=json.loads((WL/'results.json').read_text());prior_sha=sha(WL/'results.json')
 for key,a in prior['apps'].items():
  if key not in {x['key'] for x in apps}:continue
  pred=next(p for p in candidates if p['app']==key and p['profile']=='6cb40cd6+r8b')
  # Do not promote caught provider exceptions to the fatal wall.
  fatal=next((x for x in a.get('next_wall',[]) if 'J_invokeStaticMain_main_threw' in x['text']),None)
  observed='unknown';reason='No unambiguous fatal entry in saved first-cause excerpt; README and intermediate caught exceptions are insufficient.'
  if fatal:
   t=fatal['text']
   if 'SQLiteConnection.nativeOpen' in t:observed='sqlite-jni'
   elif 'Theme.AppCompat' in t:observed='activity-theme'
   elif 'com.sun.jna.Native' in t:observed='jna-arm64-library'
   elif 'path is outside app domain' in t:observed='out-of-scope:namespace'
   elif 'InflateException' in t:observed='resource-inflate'
   elif 'JobScheduler' in t:observed='service:jobscheduler'
   elif 'INotificationManager' in t:observed='service:notification'
   reason='Exact fatal entry from existing hilog; not a prospective holdout.'
  eligible=observed!='unknown' and not observed.startswith('out-of-scope:') and a.get('install',{}).get('installed_apk_sha256')==next(x['sha256'] for x in apps if x['key']==key)
  hit=eligible and pred['predicted_first']==observed
  observations.append({'task':65,'app':key,'profile':'6cb40cd6+r8b','predicted_first':pred['predicted_first'],'observed_first':observed,'eligible':eligible,'hit':hit,'reason':reason+(' Static heuristic ordered a different wall first.' if eligible and not hit else ''),'evidence':fatal,'source':str(WL/'results.json'),'source_sha256':prior_sha})
 # Required historical cohorts with unmeasured first walls/configuration mismatch.
 for task,keys,why,source in [
  (63,json.loads((INPUT/'results.json').read_text())['source']['p63_white13'],'Earlier JAR/configuration; white window/exit alone does not identify a static first wall.',str(INPUT/'results.json')),
  (69,['fd-binaryeye'],'Spawn-stage observation and manifest classification do not prove a fatal static first wall.',str(INPUT/'binaryeye-evidence')),
  (71,list(json.loads((INPUT/'p71-rerun/p71-final.json').read_text())['per_app']),'Outer corrected #71: 256K hilog buffer/private logging caused a measurement gap; first cause not measured. Do not infer JAR behavior from absent markers.',str(INPUT/'p71-rerun/p71-final.json'))]:
  for key in keys:observations.append({'task':task,'app':key,'predicted_first':next(p['predicted_first'] for p in candidates if p['app']==key and p['profile']=='6cb40cd6+r8b'),'observed_first':'unknown','eligible':False,'hit':False,'reason':why,'source':source})
 b68=BASE/'westlake-harness-bms-deploy/benchmark/2026-09-29-unlocked-generation/results.json';old=json.loads(b68.read_text())
 for key,a in old['apps'].items():
  match=next((x['key'] for x in apps if x['manifest']['package']==a.get('package')),None)
  if match:observations.append({'task':68,'app':match,'run':key,'predicted_first':next(p['predicted_first'] for p in candidates if p['app']==match and p['profile']=='v3-74d1d6d4+r8b'),'observed_first':'unknown','eligible':False,'hit':False,'reason':'Mixed B5/r8b and bridge swaps; static registration receipt is not a first fatal wall. No matched exact-package first-cause receipt accepted.','source':str(b68)})
 scored=[x for x in observations if x['eligible']];hits=sum(x['hit'] for x in scored)
 backtest={'kind':'retrospective agreement; existing evidence was already known, not prospective accuracy','hits':hits,'total':len(scored),'rate':hits/len(scored) if scored else None,'all_observations':len(observations),'unscored':len(observations)-len(scored),'rows':observations};dump('backtest.json',backtest)
 known={}
 for gen,d in jni.items():known[gen]=[{k:m[k] for k in ['id','status','evidence']} for m in d['methods'] if m['method'] in {'nativeParseManifestJson','nativeGetSysProp'} and m['class']=='adapter/activity/AppSchedulerBridge' or m['class']=='android/database/sqlite/SQLiteConnection' and m['method']=='nativeOpen']
 results={'task':72,'offline':True,'scope':'timeboxed first version; unresolved items remain unknown; no runtime behavior conclusions','jni':{'known_answers':known,'counts':{k:v['counts'] for k,v in jni.items()},'method_inventory':'jni-results.json','allowlist_proposals':len(exceptions),'approved_exceptions':0},'services':{'apps':len(apps),'rows':len(services),'counts':dict(collections.Counter(x['status'] for x in services)),'catalog':'service-catalog.json'},'predictions':{'version':2 if reach else 1,'rows':len(candidates),'ranking':ranked,'stub_ok_ranking':[r for r in ranked if r['stub_ok']],'needs_real_ranking':[r for r in ranked if r['needs_real']]},'backtest':backtest,'build':json.loads((HERE/'build-audit.json').read_text()),'screenshots':'not collected (offline); existing screen/liveness totals not re-counted, unknown','limitations':['Export/registration presence does not prove namespace resolution, hook execution or runtime behavior.','Native table owner is established using local source plus exact compiled table/function; source provenance is hashed.','Service calls include dependency/library paths; no interprocedural reachability proof.','Unknown services/native methods are not covered; draft exceptions are not active.']}
 dump('results.json',results)
 print(json.dumps({'jni':results['jni']['counts'],'services':results['services'],'predictions':len(candidates),'backtest':[hits,len(scored)],'exceptions':len(exceptions)},indent=2))
if __name__=='__main__':main()
