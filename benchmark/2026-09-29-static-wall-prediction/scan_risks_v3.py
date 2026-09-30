#!/usr/bin/env python3
"""Static risk candidates only. This module never reads fatal/backtest observations."""
import argparse,collections,concurrent.futures,csv,gzip,hashlib,json,re,struct,zipfile
from pathlib import Path
from scan_jni import HERE,PACKAGES,R8HASH,REPO,sha
from scan_apps import load_apps,INVOKE
from scan_io import load,physical
from scan_reachability import scan as scan_graph
OUT=HERE/'v3'

def dump(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n')

def inspect_method(method,dex,insns):
    """Retain direct loads/guards/initializers; branchy argument flow stays unknown."""
    branches=any(t.startswith(('if-','goto','packed-switch','sparse-switch','move-exception')) for _,_,t in insns)
    regs={};rows=[]
    for offset,line,text in insns:
        m=INVOKE.search(text)
        if m:
            op,args,owner,name,sig=m.groups();kind=None
            if (owner in {'java/lang/System','java/lang/Runtime'} and name in {'load','loadLibrary','loadLibrary0','nativeLoad'}) or (name in {'loadLibrary','load'} and any(s in owner.lower() for s in ['soloader','relinker','nativeloader','sharedlibrary'])):kind='native-load'
            elif owner.startswith('org/koin/') and name.lower() in {'startkoin','getkoin','get','start','init'}:kind='koin-init-or-use'
            elif owner.startswith('androidx/work/') and name in {'initialize','getInstance','create','enqueue','a','b'}:kind='workmanager-init-or-use'
            elif owner in {'android/content/Context','android/content/ContextWrapper','android/app/Application','android/app/Activity'} and name in {'attachBaseContext','getApplicationContext','getSharedPreferences','getSystemService','bindService'}:kind='context-contract'
            if kind:
                rr=re.findall(r'v\d+',args)
                if '..' in args and len(rr)==2:rr=[f'v{i}' for i in range(int(rr[0][1:]),int(rr[1][1:])+1)]
                formals=re.findall(r'\[*L[^;]+;|\[*[ZBCSIJFD]',sig[1:sig.index(')')]);slot=0 if op.startswith('invoke-static') else 1;positions=[]
                for param in formals:
                    if param=='Ljava/lang/String;':positions.append(slot)
                    slot+=2 if param in {'J','D'} else 1
                value=regs.get(rr[positions[0]]) if len(positions)==1 and positions[0]<len(rr) and not branches else None
                rows.append({'kind':kind,'method':method,'dex':dex,'offset':offset,'line':line,
                             'target':owner+'.'+name+sig,'constant_argument':value,
                             'argument_reason':'straight-line constant' if value is not None else 'unknown: branch, computed value or wrapper; no guess',
                             'instruction':text})
        c=re.match(r'const-string(?:/jumbo)? (v\d+), "(.*)" //',text)
        if c:
            regs[c[1]]=c[2]
            for wall,needle in [('koin-initialization','KoinApplication has not been started'),
                                ('workmanager-initialization','WorkManager is not initialized properly')]:
                if needle in c[2]:rows.append({'kind':'initialization-guard','wall':wall,'method':method,'dex':dex,
                    'offset':offset,'line':line,'instruction':text,'reason':'APK guard exists; execution/branch outcome unknown'})
        elif not text.startswith(('invoke-','if-','goto','return','iput','sput','aput','monitor-','check-cast')):
            dest=re.match(r'[^ ]+ (v\d+)',text)
            if dest:regs.pop(dest[1],None)
    return rows

def dynamic(data):
    if data[:6]!=b'\x7fELF\x02\x01':return {'status':'unknown-non-ELF64'}
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',data);secs=[]
    for i in range(h[12]):
        secs.append(struct.unpack_from('<IIQQQQIIQQ',data,h[6]+i*h[11]))
    result={'status':'parsed','needed':[],'soname':None,'rpath':[]}
    for s in secs:
        if s[1]!=6:continue
        st=secs[s[6]];strings=data[st[4]:st[4]+st[5]]
        for i in range(s[4],s[4]+s[5],s[9] or 16):
            tag,value=struct.unpack_from('<qQ',data,i)
            if tag in {1,14,15,29}:
                end=strings.find(b'\0',value);text=strings[value:end].decode(errors='replace')
                if tag==1:result['needed'].append(text)
                elif tag==14:result['soname']=text
                else:result['rpath'].append(text)
    return result

def app_native(app):
    rows=[]
    with zipfile.ZipFile(app['apk']) as z:
        names=[n for n in z.namelist() if n.startswith('lib/arm64-v8a/') and n.endswith('.so')]
        for n in names:
            b=z.read(n)
            rows.append({'entry':n,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),**dynamic(b)})
    return rows

def derive(app,graph,natives,services,package_files):
    """Pure APK/package rule function; no per-app keys, fatal messages or result joins."""
    mf=graph['manifest'];features=graph['features'];extra=graph.get('extra_calls',[])
    rows=[]
    def add(wall,evidence,startup='unknown',priority=20,stub=False,condition=None):
        rows.append({'app':app['key'],'apk_sha256':app['sha256'],'wall':wall,
            'status':'risk-candidate','startup_reachable':startup,'priority':priority,
            'stub_ok':stub,'needs_real':not stub,'evidence':evidence,
            'runtime_condition':condition or 'Execution, ordering and branch outcome unknown; not proof of failure.'})
    loads=[x for x in extra if x['kind']=='native-load']
    names={Path(n['entry']).name for n in natives}
    unresolved=[]
    for n in natives:
        for needed in n.get('needed',[]):
            if needed not in names and needed not in package_files:
                unresolved.append({'entry':n['entry'],'dependency':needed,'status':'not-in-reviewed-package',
                    'reason':'System/other namespace providers not inventoried; runtime resolution unknown.'})
    missing_loads=[]
    for load in loads:
        arg=load.get('constant_argument')
        if arg and '/' not in arg:
            filename=arg if arg.endswith('.so') else 'lib'+arg+'.so'
            if filename not in names and filename not in package_files:missing_loads.append({'filename':filename,'call':load})
    if unresolved or missing_loads:
        reachable=any(x.get('startup_reachable')=='yes-static' for x in loads)
        add('dlopen-namespace',{'elf_unresolved_dependencies':unresolved,'literal_loads_absent_from_package':missing_loads,
            'load_calls':loads,'native_entry_count':len(natives)},'yes-static' if reachable else 'unknown',8,
            condition='Needs an allowed source/provider in the effective child namespace; file presence alone is insufficient.')
    if app['manifest'].get('flutter'):
        add('flutter-native-path',{'flutter_manifest':app['manifest'],'libflutter_entries':[n['entry'] for n in natives if n['entry'].endswith('/libflutter.so')],
            'load_calls':loads},features.get('flutter',{}).get('startup_reachable','unknown'),7,
            condition='Flutter may extract under app_lib; compare the effective extraction destination with allowed app paths. Namespace choice remains runtime.')
    guards=collections.defaultdict(list)
    for c in extra:
        if c['kind']=='initialization-guard':guards[c['wall']].append(c)
    for feature,wall in [('koin','koin-initialization'),('workmanager','workmanager-initialization')]:
        if feature not in app['features'] and feature not in features and not guards[wall]:continue
        ref=features.get(feature,{})
        init=[x for x in extra if x['kind']==feature+'-init-or-use']
        initializers=[i for i in mf.get('initializers',[]) if feature in i['class'].lower()]
        # Guard reachability is useful even when symbols are obfuscated.
        reachable=ref.get('startup_reachable')=='yes-static' or any(g.get('startup_reachable')=='yes-static' for g in guards[wall])
        add(wall,{'custom_application':mf['application'],'provider_classes':[p['class'] for p in mf['providers']],
            'manifest_initializers':initializers,'guard_sites':guards[wall],'init_or_use_calls':init,
            'feature_path':ref,'initialization_order':'unknown'},
            'yes-static' if reachable else 'unknown',12 if feature=='koin' else 13,
            condition='Must initialize before first use; provider metadata/custom Application presence does not prove successful onCreate/attach execution.')
    # General attach/Application/provider-phase nullable service/context contracts.
    for service in services:
        if service['app']!=app['key'] or service['status'] not in {'missing','westlake-only','unknown'}:continue
        paths=[p for p in service.get('startup_evidence',[]) if p.get('root',{}).get('category') in {'application','provider','androidx_startup_metadata'}]
        if paths and service['service']!='unknown':
            add('attach-service-contract',{'service':service['service'],'coverage':service['status'],'startup_paths':paths},
                'yes-static',5,True,'Null Binder/manager or wrong proxy return types can abort attach/Application/provider initialization.')
    context=[x for x in extra if x['kind']=='context-contract' and 'getSharedPreferences' in x['target']]
    if context:
        reachable=any(x.get('startup_reachable')=='yes-static' for x in context)
        add('attach-context-contract',{'calls':context},'yes-static' if reachable else 'unknown',22,False,
            'A non-null Context/SharedPreferences contract is required; static references do not prove a runtime null.')
    return rows

def scan_one(app,refresh):
    path=OUT/'evidence'/('reachability-'+app['key']+'.json')
    graph=None
    if not refresh and physical(path).exists():
        graph=load(path)
        if graph['apk_sha256']!=sha(Path(app['apk'])):raise ValueError('stale APK graph '+app['key'])
        if graph.get('scanner_sha256')!=sha(HERE/'scan_reachability.py') or graph.get('method_inspector_sha256')!=sha(Path(__file__)):graph=None
    if graph is None:graph=scan_graph(app,OUT/'evidence',inspect_method)
    return app,graph,app_native(app)

def main():
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');a=p.parse_args()
    apps=load_apps();services=load(HERE/'service-results.json')
    package_files={g:{Path(p).name for p in json.loads((root/'package.json').read_text())['files']} for g,root in PACKAGES.items()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:scans=list(pool.map(lambda app:scan_one(app,a.refresh),apps))
    allrows=[];inputs=[]
    for app,graph,natives in scans:
        inputs.append({'app':app['key'],'apk':app['apk'],'sha256':app['sha256'],'natives':natives})
        for gen in PACKAGES:
            for row in derive(app,graph,natives,services,package_files[gen]):
                row['profile']=gen+'+r8b';allrows.append(row)
    dump(OUT/'risk-results.json',{'rules_version':3,'kind':'static candidates, not observed runtime failures','rows':allrows,'inputs':inputs,
        'scanner_inputs':[{'path':str(p),'sha256':sha(p)} for p in [Path(__file__),HERE/'scan_reachability.py',physical(HERE/'service-results.json'),HERE/'scan_io.py']]})
    with (OUT/'risk-matrix.csv').open('w') as f:
        fields=['app','profile','apk_sha256','wall','status','startup_reachable','stub_ok','needs_real','priority','runtime_condition','evidence']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in allrows:w.writerow({k:json.dumps(row[k],separators=(',',':')) if isinstance(row[k],(dict,list)) else row[k] for k in fields})
    print('risk rows',len(allrows),collections.Counter(x['wall'] for x in allrows),flush=True)
if __name__=='__main__':main()
