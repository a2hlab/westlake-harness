"""Publish exact JNI worklist, scoped evidence, ranked batches and exception drafts."""
import collections,csv,gzip,hashlib,json,sys
from pathlib import Path
from observations import missing_id
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-09-29-static-wall-prediction'
read=lambda p:json.load(gzip.open(p,'rt')) if str(p).endswith('.gz') else json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def csvwrite(name,rows,fields):
    with (HERE/name).open('w') as f:
      w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
      for row in rows:w.writerow({k:json.dumps(row.get(k),ensure_ascii=False,separators=(',',':')) if isinstance(row.get(k),(dict,list)) else row.get(k,'') for k in fields})
def classify(static,attempts,missing):
    if missing:return 'unbound_observed',('binding_gap' if static in {'registered','exported'} or attempts else 'implementation_or_binding_gap')
    if static in {'registered','exported'}:return 'implementation_present','none'
    if attempts:return 'registration_attempt_only','binding_not_confirmed'
    if static=='missing':return 'missing_static','implementation_or_binding_gap'
    return 'unknown','no_implementation_evidence'

def main():
    inv=read(HERE/'evidence/native-inventory.json.gz');obs=read(HERE/'evidence/observations.json.gz');west=read(HERE/'evidence/westlake-sources.json.gz')
    runtime=read(HERE/'evidence/runtime-tables.json.gz')
    coverage=read(HERE/'app-coverage.json');apps={}
    allrefs=collections.defaultdict(set);startup=collections.defaultdict(set);direct=collections.defaultdict(set);witnesses=collections.defaultdict(list)
    for a in coverage:
      data=read(HERE/'evidence/apps'/ (a['key']+'.json.gz'));apps[a['key']]=data
      for mid in data['all_code']:allrefs[mid].add(a['key'])
      for mid in data['app_direct_native']:direct[mid].add(a['key'])
      for mid,trace in data['startup'].items():
        startup[mid].add(a['key'])
        if len(witnesses[mid])<3:witnesses[mid].append({'key':a['key'],'evidence':f'evidence/apps/{a["key"]}.json.gz#/startup/{mid}',**trace})
    triagepath=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-b4/benchmark/2026-09-29-wikipedia-diff/r17a-triage.json')
    triage=read(triagepath);fatal=collections.defaultdict(set);fatal_evidence={}
    for run,data in triage['runs'].items():
      for row in data['rows']:
        mid=missing_id(row.get('fatal') or '')
        if mid and row.get('alive') is False and any(e['key']==row['key'] for e in obs['missing'].get(mid,[])):
          fatal[mid].add(row['key']);fatal_evidence[row['key']]={'run':run,**row}
    write('evidence/fatal-triage.json',{'source':str(triagepath),'sha256':sha(triagepath),'rows':fatal_evidence})
    source_inventory=read(OLD/'v3/evidence/source-registration-inventory.json.gz')
    aosp=collections.defaultdict(list)
    for r in source_inventory['rows']:
      if '/aosp/' in r['path']:aosp[r['class']+'.'+r['method']+r['signature']].append({'path':r['path'],'line':r['line'],'function_names':r['function_names']})
    legacy=read(OLD/'jni-allowlist.json');legacy_by=collections.defaultdict(list)
    for e in legacy['exceptions']:
      if e.get('approval')=='approved':legacy_by[e['method']].append(e)
    evidence={};rows=[];exceptions=[];strict=[]
    inventory_sha=sha(HERE/'evidence/native-inventory.json.gz')
    known_tolerated={'adapter/activity/AppSchedulerBridge.nativePrimeDefaultTypeface()J':{'reason':'Previously approved EARLY-TF failure tolerated in lit ZigZag; current ULE is not a fatal attribution.','source':str(OLD/'jni-allowlist.json')},'adapter/activity/AppSchedulerBridge.nativeGetSysProp(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;':{'reason':'Westlake AppSchedulerBridge.java catches Throwable and returns unknown for serial-number fallback (lines 910-913); no fatal attribution in r17a.','source':'/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current/framework/activity/java/AppSchedulerBridge.java:910'}}
    for m in inv['methods']:
      mid=m['id'];attempts=obs['attempts'].get(mid,[]);miss=obs['missing'].get(mid,[])
      current=[e for e in miss if 'r17a' in e['run']]
      static_status='registered' if mid in runtime['compiled_matches'] else m['status']
      status,kind=classify(static_status,attempts,miss)
      src=west['methods'].get(mid,[])
      sources=[]
      for s in src:
        for body in s['bodies']:sources.append({'file':s['path'],'registration_line':s['line'],'definition_line':body['definition_line'],'function':body['function'],'body_kind':body['body_kind'],'basis':s['basis']})
      source_kind='not_found_in_scanned_snapshots'
      if sources:source_kind='body_found' if any(s['body_kind']=='source_body_present' for s in sources) else 'literal_return_or_empty_stub'
      priority_apps=startup[mid]|fatal[mid]
      known=known_tolerated.get(mid)
      row={'id':mid,'class':m['class'],'method':m['method'],'signature':m['signature'],'status':status,'gap_kind':kind,
           'static_status':static_status,'startup_app_count':len(startup[mid]),'startup_apps':sorted(startup[mid]),'all_code_app_count':len(allrefs[mid]),'all_code_apps':sorted(allrefs[mid]),
           'app_direct_native_count':len(direct[mid]),'app_direct_native_apps':sorted(direct[mid]),'fatal_r17a_app_count':len(fatal[mid]),'fatal_r17a_apps':sorted(fatal[mid]),
           'priority_app_count':len(priority_apps),'priority_apps':sorted(priority_apps),'registration_attempt_count':len(attempts),
           'unbound_observed_apps':sorted({e['key'] for e in miss}),'unbound_r17a_apps':sorted({e['key'] for e in current}),
           'reachability':'conditional-static' if startup[mid] else 'unknown_no_bounded_path',
           'known_tolerated_helper':bool(known),'westlake_implementation':source_kind,'westlake_sources':sources,'aosp_sources':aosp.get(mid,[])+[{'path':r['path'],'line':r['line']} for r in runtime['sources'].get(mid,[])],
           'legacy_approved_exception_count':len(legacy_by[mid]),'declaration':m['declaration'],'evidence':'evidence/methods.json.gz#/'+mid}
      rows.append(row)
      if status!='implementation_present':
        ev={'static':m,'additional_compiled_proof':runtime['compiled_matches'].get(mid,[]),'registration_attempts':attempts[:3],'missing':miss[:3],'all_missing_locations':[{'key':e['key'],'path':e['path'],'line':e['line'],'run':e['run'],'pid':e['pid']} for e in miss],
            'startup_witnesses':witnesses[mid],'westlake':src,'aosp_sources':aosp.get(mid,[])+[{'path':r['path'],'line':r['line']} for r in runtime['sources'].get(mid,[])],'tolerated_helper':known}
        evidence[mid]=ev
        strict.append({'id':mid,'status':status,'gap_kind':kind,'startup_app_count':len(startup[mid]),'fatal_r17a_app_count':len(fatal[mid]),'evidence':row['evidence']})
        if not startup[mid] or known:
          exceptions.append({'id':mid,'status':status,'inventory_sha256':inventory_sha,'approval':'draft','approved_by':None,
           'kind':'tolerated-failure-review' if known else 'startup-no-path-review',
           'reachability':'unknown_no_bounded_path' if not startup[mid] else 'conditional-static',
           'reason':known['reason'] if known else 'No path in the scanned 65 original APK base dex startup graphs plus six framework edges. Callbacks, reflection, asynchronous work, split dex and the mismatched SubwaySurfers input remain unknown; this is not proof of first-screen unreachability.',
           'evidence':[row['evidence'],'app-coverage.json'],
           'legacy_approvals':[{'generation':e['generation'],'overlay_sha256':e.get('overlay_sha256'),'status':e['status'],'approved_by':e['approved_by']} for e in legacy_by[mid]]})
    gaps=[r for r in rows if r['status']!='implementation_present']
    for r in gaps:
      r['priority_group']='observed_fatal' if r['fatal_r17a_app_count'] else 'tolerated_helper_review' if r['known_tolerated_helper'] else 'observed_unbound' if r['unbound_r17a_apps'] else 'unknown_review'
    order={'observed_fatal':0,'observed_unbound':1,'unknown_review':2,'tolerated_helper_review':3}
    gaps.sort(key=lambda r:(order[r['priority_group']],-r['priority_app_count'],-r['fatal_r17a_app_count'],-r['all_code_app_count'],r['id']))
    for i,r in enumerate(gaps,1):r['rank']=i
    fields=['rank','priority_group','class','method','signature','id','status','gap_kind','static_status','priority_app_count','startup_app_count','startup_apps','fatal_r17a_app_count','fatal_r17a_apps','all_code_app_count','all_code_apps','app_direct_native_count','registration_attempt_count','unbound_observed_apps','unbound_r17a_apps','reachability','known_tolerated_helper','westlake_implementation','westlake_sources','aosp_sources','declaration','evidence']
    csvwrite('jni-gap.csv',gaps,fields);csvwrite('jni-all.csv',rows,fields)
    csvwrite('app-coverage.csv',coverage,['key','status','apk','apk_sha256','method_count','reachable_method_count','error','split_dex_scope'])
    batches=collections.defaultdict(list)
    for r in gaps:
      if r['priority_app_count']:batches[r['class']].append(r)
    b=[]
    for cls,rr in batches.items():
      b.append({'class':cls,'native_method_count':len(rr),'priority_app_count':len(set(a for r in rr for a in r['priority_apps'])),'fatal_r17a_apps':sorted(set(a for r in rr for a in r['fatal_r17a_apps'])),'methods':[r['id'] for r in rr],'westlake_source_files':sorted(set(s['file'] for r in rr for s in r['westlake_sources']))})
    b.sort(key=lambda x:(-x['priority_app_count'],-len(x['fatal_r17a_apps']),x['class']))
    csvwrite('gapfill-batches.csv',b,['class','native_method_count','priority_app_count','fatal_r17a_apps','methods','westlake_source_files'])
    write('jni-strict.json',{'inventory_sha256':inventory_sha,'package_manifest_sha256':inv['package_manifest_sha256'],'declaration_count':len(rows),'covered_count':len(rows)-len(gaps),'methods':strict,'policy':'Every non-covered declaration blocks unless an exact inventory-scoped reviewed exception is approved. Log attempts are not successful registrations.'})
    write('jni-exceptions.json',{'approval':'draft','legacy_approved_source':str(OLD/'jni-allowlist.json'),'legacy_approved_sha256':sha(OLD/'jni-allowlist.json'),'policy':'Previous approvals are preserved at source. These new exceptions widen from 20 direct-call APKs to 66-key startup/transitive scope and require review; no bounded path does not imply unreachable.','exceptions':exceptions})
    with gzip.open(HERE/'evidence/methods.json.gz','wt') as f:json.dump(evidence,f)
    summary={'declarations':len(rows),'coverage':dict(collections.Counter(r['status'] for r in rows)),'gap_count':len(gaps),'startup_gap_count':sum(r['startup_app_count']>0 for r in gaps),'priority_gap_count':sum(r['priority_app_count']>0 for r in gaps),'extra_ART_libcore_compiled_matches':len(runtime['compiled_matches']),'source_body_or_stub_gap_count':sum(bool(r['westlake_sources']) for r in gaps),'apk_coverage':dict(collections.Counter(a['status'] for a in coverage)),
     'known_answers':{r['id']:{k:r[k] for k in ['status','static_status','startup_app_count','fatal_r17a_apps','westlake_implementation','westlake_sources']} for r in rows if r['id'] in obs['missing']},
     'observed_registration_attempts':len(obs['attempts']),'explicit_unbound_methods':len(obs['missing']),'exception_drafts':len(exceptions),'r2':'Static evidence and observed target-process ULEs; conditional reachability is not an executed/fatal call proof. No board operations.',
     'limitations':['SubwaySurfers expected 5904cda2 vs available ffd32287; excluded from ranked graph counts, explicit unknown.','Base APK DEX only; split DEX is not inspected.','Application graph omits ambiguous callbacks/reflection/async edges; framework closure capped at six exact/inherited Java calls.','Framework duplicate definitions unioned; active boot classpath selection unknown.','OH_RegHook prints before real RegisterNatives; attempts are not success receipts.','r16/r17a runtime observations are scoped by run/serial/PID; they do not establish identical v3a files on every board.']}
    write('results.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['known_answers']},indent=2),flush=True)
if __name__=='__main__':main()
