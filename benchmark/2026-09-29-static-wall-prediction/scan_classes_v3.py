#!/usr/bin/env python3
"""Offline definition availability, NOT a runtime Class.forName success test."""
import argparse,collections,csv,gzip,json,re,struct,subprocess,tempfile,zipfile
from pathlib import Path
from scan_jni import BASE,HERE,DEXDUMP,sha,identity
from scan_apps import HEADER,INSN,method_scan,load_apps
from scan_reachability import scan
OUT=HERE/'v3/classes'
FRAMEWORK=BASE/'westlake-generation-v3a-74d1d6d4-r8b/payload/android/framework'
R13=BASE/'vm-copies/r13-runtime-jar/oh-adapter-runtime.jar'
R13SHA='f132529710a8c45c2bb3579c5abe281e47616ce310228b3ddb69b83c6bc2f1e8'
PREFIX=('android/','com/android/','dalvik/','java/','javax/','org/apache/','org/xml/')

def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode();path.write_bytes(raw)
    if len(raw)>1000000:Path(str(path)+'.gz').write_bytes(gzip.compress(raw,mtime=0))

def dex_classes(data):
    if data[:4]!=b'dex\n':raise ValueError('unsupported DEX magic')
    def u32(off):return struct.unpack_from('<I',data,off)[0]
    strings=[]
    for i in range(u32(56)):
        off=u32(u32(60)+4*i)
        while data[off]&128:off+=1
        off+=1;strings.append(data[off:data.index(b'\0',off)].decode('utf-8',errors='replace'))
    types=[strings[u32(u32(68)+4*i)] for i in range(u32(64))]
    rows=[]
    for i in range(u32(96)):
        off=u32(100)+32*i;idx=u32(off);sup=u32(off+8);interfaces=u32(off+12)
        parents=([types[sup]] if sup!=0xffffffff else [])
        if interfaces:parents += [types[struct.unpack_from('<H',data,interfaces+4+2*j)[0]] for j in range(u32(interfaces))]
        rows.append({'class':types[idx][1:-1],'class_def_index':i,'class_def_offset':hex(off),'parents':[x[1:-1] for x in parents]})
    return rows

def jar_classes(path):
    rows=[]
    with zipfile.ZipFile(path) as z:
        for entry in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
            rows.extend({**r,'jar':str(path),'dex':entry} for r in dex_classes(z.read(entry)))
    return rows

def inventory():
    if sha(R13)!=R13SHA:raise ValueError('r13 hash mismatch')
    jars=[p for p in sorted(FRAMEWORK.glob('*.jar')) if p.name!='oh-adapter-runtime.jar']+[R13]
    if len(jars)<10:raise ValueError('incomplete framework inputs')
    by=collections.defaultdict(list);inputs=[]
    for jar in jars:
        rows=jar_classes(jar);inputs.append({**identity(jar),'class_definitions':len(rows)})
        for row in rows:by[row['class']].append(row)
    data={'inputs':inputs,'excluded_replaced_jar':str(FRAMEWORK/'oh-adapter-runtime.jar'),'classes':dict(by),'scope':'All supplied framework jars plus r13 replacement; union presence is not actual loader-order or initialization proof.'}
    dump(OUT/'class-inventory.json',data);return data

def r13_dump():
    target=OUT/'evidence/r13-dexdump.txt';target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(R13) as z,tempfile.TemporaryDirectory() as td:
        with target.open('w') as f:
            for entry in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
                p=Path(td)/entry;p.write_bytes(z.read(entry));subprocess.run([str(DEXDUMP),'-d',str(p)],stdout=f,check=True)
    return target

def service_requirements(path):
    # Only the pinned LocalServiceBinders.get switch pattern: service equals,
    # then literal interface passed to proxy; generic unrecognized shapes stay absent.
    rows=[];method='';service=None;pending=None;proxy_proof=[]
    for line,text in enumerate(path.read_text().splitlines(),1):
        h=HEADER.search(text)
        if h:method=h[1];service=None;pending=None
        m=re.search(r'const-string(?:/jumbo)? v\d+, "([^"]+)"',text)
        if 'LocalServiceBinders.get:' in method:
            if m:
                if re.fullmatch(r'[a-z_]+',m[1]):service=(m[1],line)
                elif m[1].startswith(('android.','com.android.')) and service:pending=(m[1],line)
            if pending and 'LocalServiceBinders;.proxy:' in text:
                rows.append({'service':service[0],'class':pending[0].replace('.','/'),'evidence':f'{path}:{pending[1]}','service_line':service[1],'proxy_call_line':line,'method':method});pending=None
        if 'LocalServiceBinders.proxy:' in method and ('Class;.forName:' in text or 'reflect/Proxy;.newProxyInstance:' in text):proxy_proof.append({'file':str(path),'line':line,'text':text.strip()})
    if not proxy_proof or not rows:raise ValueError('r13 proxy pattern not recognized')
    dump(OUT/'service-requirements.json',{'r13_sha256':sha(R13),'requirements':rows,'proxy_proof':proxy_proof});return rows

def inspect_method(method,dex,insns):
    out=[];seen=set()
    for off,line,text in insns:
        # String names are only candidates, not direct type references.
        if text.startswith('const-string'):continue
        for cls in re.findall(r'L([^;\s]+);',text):
            if not cls.startswith(PREFIX) or cls in seen:continue
            seen.add(cls);out.append({'kind':'direct-framework-reference','class':cls,'method':method,'dex':dex,'offset':off,'line':line,'text':text})
    calls,_,_=method_scan(method,insns,dex,0,set())
    for call in calls:out.append({**call,'kind':'service-call'})
    return out

def status(cls,inventory,app_defs,interface=False):
    defs=inventory['classes'].get(cls,[])
    if defs:return 'definition-present',defs
    if cls in app_defs and not interface:return 'app-definition-present',[app_defs[cls]]
    # App classloader cannot repair an interface loaded by adapter boot classes.
    return 'definition-absent',[]

def analyze(app,inv,requirements):
    if sha(Path(app['apk']))!=app['sha256']:raise ValueError('APK hash mismatch: '+app['key'])
    cache=OUT/'evidence'/('reachability-'+app['key']+'.json')
    from scan_io import load,physical
    import scan_reachability
    graph=load(cache) if physical(cache).exists() else None
    if not graph or graph.get('apk_sha256')!=app['sha256'] or graph.get('method_inspector_sha256')!=sha(Path(__file__)) or graph.get('scanner_sha256')!=sha(Path(scan_reachability.__file__)):
        graph=scan({**app,'calls':[],'features':{}},OUT/'evidence',inspect_method)
    app_defs={x['class']:x for x in jar_classes(Path(app['apk']))};rows=[]
    for call in graph['extra_calls']:
        if call['kind']=='service-call':
            matches=[r for r in requirements if r['service']==call['service']]
            if not matches:
                rows.append({**call,'class':'','availability':'unknown','definition_evidence':[],'risk':'unknown-service-interface','runtime_load':'unknown'})
            for req in matches:
                state,defs=status(req['class'],inv,app_defs,True)
                rows.append({**call,'kind':'service-interface-prerequisite','class':req['class'],'availability':state,'definition_evidence':defs,'interface_evidence':req,'runtime_load':'cannot-resolve-in-supplied-boot-jars' if state=='definition-absent' else 'unknown','risk':'ClassNotFound-risk' if state=='definition-absent' else 'none-from-definition-check'})
        else:
            state,defs=status(call['class'],inv,app_defs)
            rows.append({**call,'availability':state,'definition_evidence':defs,'runtime_load':'cannot-resolve-in-supplied-jars-or-apk' if state=='definition-absent' else 'unknown','risk':'NoClassDefFound-or-ClassNotFound-risk' if state=='definition-absent' else 'none-from-definition-check'})
    # Any manager reference also exposes a conditional service prerequisite even
    # if the bounded APK graph cannot follow framework construction or callbacks.
    from scan_apps import CLASS_SERVICE
    for call in graph['extra_calls']:
        if call['kind']!='direct-framework-reference':continue
        svc=CLASS_SERVICE.get(call['class'].rsplit('/',1)[-1])
        for req in [r for r in requirements if r['service']==svc]:
            state,defs=status(req['class'],inv,app_defs,True)
            rows.append({**call,'kind':'manager-interface-prerequisite','service':svc,'class':req['class'],'availability':state,'definition_evidence':defs,'interface_evidence':req,'runtime_load':'cannot-resolve-in-supplied-boot-jars' if state=='definition-absent' else 'unknown','risk':'ClassNotFound-risk' if state=='definition-absent' else 'none-from-definition-check','condition':'Manager reference is reachable only as recorded; adapter service lookup is conditional and framework bodies are not traversed.'})
    paths={}
    for row in rows:
        if row.get('path') or row.get('root'):
            paths.setdefault(row['method'],{k:row[k] for k in ['root','path','reason'] if k in row})
        for k in ['path','root','reason']:row.pop(k,None)
        if row.get('definition_evidence'):row['definition_evidence']={'inventory_class':row['class'],'app_definition':row['availability']=='app-definition-present'}
    data={'startup_paths':paths,'app':{k:app[k] for k in ('key','apk','sha256')},'scanner_sha256':sha(Path(__file__)),'graph_scanner_sha256':graph['scanner_sha256'],'roots':graph['roots'],'method_count':graph['method_count'],'reachable_method_count':graph['reachable_method_count'],'rows':rows,'counts':dict(collections.Counter(r['availability'] for r in rows)),'limitations':['Bounded APK graph omits ambiguous dispatch, reflection, async callbacks and framework bodies.','Definition presence does not prove superclass linkage, initialization, API compatibility or actual classloader order.','Absent class may be API-guarded or caught; a static risk is not a fatal prediction.']}
    dump(OUT/(app['key']+'.json'),data)
    row_indexes={id(r):i for i,r in enumerate(rows)}
    fields=['app','apk_sha256','kind','service','class','availability','startup_reachable','risk','method','dex','line','offset','evidence']
    for name,selected in [(app['key']+'-class-matrix.csv',rows),(app['key']+'-class-risks.csv',[r for r in rows if r['availability']!='definition-present' and r['availability']!='app-definition-present'])]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader()
            for r in selected:
                item={k:r.get(k,'') for k in fields};item.update(app=app['key'],apk_sha256=app['sha256'],evidence=f"{app['key']}.json#/rows/{row_indexes[id(r)]}");w.writerow(item)
    print(app['key'],data['counts'],'startup absent',sum(r['availability']=='definition-absent' and r['startup_reachable']=='yes-static' for r in rows),flush=True)
    return data

def main():
    p=argparse.ArgumentParser();p.add_argument('--key',default='wikipedia');p.add_argument('--apk',type=Path);p.add_argument('--cohort',type=Path);a=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    inv=inventory();req=service_requirements(r13_dump())
    dump(OUT/'service-interface-matrix.json',[{**r,'availability':status(r['class'],inv,{},True)[0]} for r in req])
    if a.cohort:
        apps=json.loads(a.cohort.read_text())['apps']
    else:
        apk=a.apk or BASE/'westlake-inputs/apks/fdroid/org.wikipedia_50606.apk';apps=[{'key':a.key,'apk':str(apk),'sha256':sha(apk)}]
    results=[]
    for app in apps:
        if app.get('apk') and Path(app['apk']).is_file():
            data=analyze(app,inv,req);results.append({'key':app['key'],'sha256':app['sha256'],'status':'scanned','counts':data['counts']})
        else:results.append({'key':app['key'],'status':'unknown-missing-input'})
    dump(OUT/('cohort-results.json' if a.cohort else 'wikipedia-summary.json'),{'results':results,'inputs':inv['inputs'],'known_answer':{'class':'android.net.IConnectivityManager','availability':status('android/net/IConnectivityManager',inv,{},True)[0]},'scope':__doc__})
if __name__=='__main__':main()
