#!/usr/bin/env python3
"""Task85 detector and freeze writer. Never consumes board observations."""
import collections,csv,datetime,gzip,hashlib,json,zipfile
from pathlib import Path
from scan_jni import HERE,BASE,sha,identity
from scan_io import load
from scan_reachability import scan as scan_graph,manifest
from rules85 import FAMILIES,inspect_method,elf_info,native_verdict
from finalize_v3 import csvwrite,dump
OUT=HERE/'v4-r2';PACKAGE=BASE/'westlake-generation-v3a-74d1d6d4-r8b'
COHORT=HERE/'v3/classes/cohort.json'
OLD=HERE/'v3/classes/predictions-v3a-r13.csv'
SOURCE=HERE.parents[1]/'bms/src/adapter/framework/window/java/WindowSessionAdapter.java'

def providers():
    exports=collections.defaultdict(list);inputs=[]
    for folder in ['payload/android/lib64','payload/route']:
        for path in sorted((PACKAGE/folder).glob('*.so')):
            if not path.is_file():continue
            info=elf_info(path.read_bytes());inputs.append({**identity(path),'header':info['header'],'symbol_status':info.get('symbol_status')})
            for name in info['exports']:exports[name].append(str(path.relative_to(PACKAGE)))
    dump(OUT/'provider-exports.json',{'inputs':inputs,'exports':dict(exports),'scope':'Package export presence only; effective runtime namespace/system libs/versioned bindings unknown.'})
    return exports

def native_scan(app,exports,graph):
    libs=[]
    with zipfile.ZipFile(app['apk']) as archive:
        for name in sorted(n for n in archive.namelist() if n.startswith('lib/arm64-v8a/') and n.endswith('.so')):
            data=archive.read(name);libs.append({'entry':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),**elf_info(data)})
    app_exports=set(x for lib in libs for x in lib['exports']);out=[]
    loads=[c for c in graph['extra_calls'] if c['family']=='native-load-call']
    for lib in libs:
        verdict=native_verdict(lib,exports,app_exports)
        relevant=[c for c in loads if c.get('library') and Path(lib['entry']).name in {c['library'],'lib'+c['library']+'.so'}]
        out.append({k:v for k,v in {**lib,**verdict,'startup_reachable':'yes-static' if any(c['startup_reachable']=='yes-static' for c in relevant) else 'unknown','load_calls':relevant}.items() if k not in {'exports','imports'}})
    return out

def analyze(app,exports,jni):
    graph=scan_graph({**app,'calls':[],'features':{}},OUT/'intermediate',inspect_method)
    # Explicit service class co-reference is supporting evidence, not Intent dataflow proof.
    mf=graph['manifest'];raw=(OUT/'intermediate'/('manifest-'+app['key']+'.txt')).read_text()
    # Parse manifest service names from aapt xml attribute context.
    declared=[];service=False
    import re
    for line in raw.splitlines():
        m=re.match(r'(\s*)E: ([^ ]+)',line)
        if m:service=m[2]=='service'
        elif service:
            m=re.search(r'A: [^ ]*name(?:\([^)]*\))?="([^"]+)"',line)
            if m:
                name=m[1];name=mf['package']+name if name.startswith('.') else mf['package']+'.'+name if '.' not in name else name;declared.append(name.replace('.','/'));service=False
    for row in graph['extra_calls']:
        if row['family']=='in-app-bindservice':
            row['declared_service_co_references']=sorted(set(row.get('class_constants_in_method_before_call',[]))&set(declared))
            row['intent_target']='own-app-candidate' if row['declared_service_co_references'] else 'unknown'
    natives=native_scan(app,exports,graph);evidence=[];matrix=[]
    for family in FAMILIES:
        calls=[c for c in graph['extra_calls'] if c['family']==family]
        native_hits=[n for n in natives if n['hit']] if family=='native-bionic-header' else []
        hit=bool(calls or native_hits);startup=any(c['startup_reachable']=='yes-static' for c in calls+native_hits)
        strong=any(c.get('strength')=='unsupported-source-policy-constant' for c in calls) or any(n['header_invalid'] or n['strong_unprovided'] for n in native_hits)
        row={'app':app['key'],'apk_sha256':app['sha256'],'family':family,'hit':hit,'verdict':'static-risk-candidate' if hit else 'no-static-evidence','startup_reachable':'yes-static' if startup else 'unknown','callsite_count':len(calls),'native_library_hits':len(native_hits),'strong_static_predicate':strong,'stub_ok':False,'needs_real':True,'evidence':f'evidence/{app["key"]}.json#/{family}'}
        matrix.append(row);evidence.append((family,{'calls':calls,'native_libraries':native_hits,'jni_coverage':jni if family=='velocitytracker-jni' else None,'runtime_condition':{
            'window-type-flags':'Actual r14 flag policy/type mapping and branch execution must be confirmed.',
            'in-app-bindservice':'A real own-service bind may be needed; a null/no-op stub may be insufficient. Co-reference is not target-flow proof.',
            'velocitytracker-jni':'Native wrapper registration is unresolved in pinned v3 JNI matrix, not proven missing; r14 native changes unknown.',
            'native-bionic-header':'UND symbols and input headers only. Native file selected at runtime, namespace and initializer behavior unknown.',
            'sharedpreferences-null':'Null receiver or return is a runtime contract risk, not a static fact.'}[family]}))
    dump(OUT/'evidence'/(app['key']+'.json'),{'app':app,'manifest':mf,'declared_services':declared,**dict(evidence),'all_native_headers':[{k:n[k] for k in ['entry','sha256','header','symbol_status'] if k in n} for n in natives]})
    return matrix

def main():
    OUT.mkdir(exist_ok=True);(OUT/'evidence').mkdir(exist_ok=True)
    freeze=OUT/'freeze.json'
    if freeze.exists():raise SystemExit('Frozen predictions exist; use a new version directory for revised detectors.')
    apps=load(COHORT)['apps'];assert len(apps)==32
    exports=providers();matrix=[];jni=[m for m in load(HERE/'jni-results.json')['v3-74d1d6d4']['methods'] if m['class']=='android/view/VelocityTracker']
    for app in apps:
        if sha(Path(app['apk']))!=app['sha256']:raise ValueError('APK identity changed')
        rows=analyze(app,exports,jni);matrix+=rows;print(app['key'],[(r['family'],r['startup_reachable']) for r in rows if r['hit']],flush=True)
    csvwrite(OUT/'hits.csv',matrix,list(matrix[0]));dump(OUT/'hits.json',matrix)
    prior={r['app']:r for r in csv.DictReader(OLD.open())};predictions=[]
    priority={'window-type-flags':10,'in-app-bindservice':20,'native-bionic-header':30,'velocitytracker-jni':40,'sharedpreferences-null':50}
    for app in apps:
        hits=[r for r in matrix if r['app']==app['key'] and r['hit']]
        hits.sort(key=lambda r:(r['startup_reachable']!='yes-static',not r['strong_static_predicate'],priority[r['family']]))
        old=prior[app['key']]
        predictions.append({'app':app['key'],'apk_sha256':app['sha256'],'profile':'v3a+r13 static baseline; evaluated against r14 with explicit generation caveat','predicted_first_new_family':hits[0]['family'] if hits else 'unknown','new_family_order':[r['family'] for r in hits],'startup_new_families':[r['family'] for r in hits if r['startup_reachable']=='yes-static'],'prior_startup_class_risks':json.loads(old['startup_class_risks']),'prior_unknown_class_risks':json.loads(old['unresolved_class_risks']),'prior_profile':'v3a+r13; repair status under r14 unknown','evidence':[r['evidence'] for r in hits],'ordering':'bounded startup, strong predicate, then fixed family priority; not actual execution order'})
    csvwrite(OUT/'predictions-v3a-r13.csv',predictions,list(predictions[0]));dump(OUT/'predictions.json',predictions)
    source_files=[Path(__file__),HERE/'rules85.py',HERE/'scan_reachability.py',HERE/'scan_apps.py',HERE/'scan_jni.py',SOURCE,COHORT,OLD,HERE/'jni-results.json.gz',OUT/'protocol.json']
    outputs=[OUT/'hits.csv',OUT/'hits.json',OUT/'predictions-v3a-r13.csv',OUT/'predictions.json']
    receipt={'task':85,'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':[identity(p) for p in source_files],'apks':apps,'provider_manifest_sha256':sha(OUT/'provider-exports.json'),'outputs':[identity(p) for p in outputs],'observations_read':False,'outcome_exposure':load(OUT/'protocol.json')['outcome_exposure_before_freeze'],'known_limit':'Outcome-blind for undisclosed keys, not frozen before existing r14 board run.'}
    dump(freeze,receipt);print('FROZEN',receipt['frozen_at'],flush=True)

if __name__=='__main__':main()
