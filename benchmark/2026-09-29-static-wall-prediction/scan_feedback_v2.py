#!/usr/bin/env python3
"""Outcome-independent B10 feedback scan. APK identities are from frozen v2."""
import argparse,collections,concurrent.futures,gzip,hashlib,json,re,subprocess,sys,tempfile,zipfile
from pathlib import Path
from rules_feedback_v2 import inspect,activity_rows,FAMILIES
from scan_apps import HEADER,INSN,INVOKE
from scan_reachability import method_id
from scan_jni import DEXDUMP,sha
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'2026-09-30-background-start-prospective'))
from scan import lifecycle_paths,activity_nodes
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'benchmark/2026-09-30-v2-scanner-feedback'
BG=ROOT/'benchmark/2026-09-30-background-start-prospective/evidence'

def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def parse(apk):
    methods={};parents={};interfaces={};extra=[];bodies={};cls=None;ib=False
    with zipfile.ZipFile(apk) as z,tempfile.TemporaryDirectory(prefix='v2-feedback-') as td:
        for entry in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
            p=Path(td)/entry;p.write_bytes(z.read(entry))
            proc=subprocess.Popen([str(DEXDUMP),'-d',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
            current=None;insns=[]
            def flush():
                if current:
                    rows=inspect(current,entry,insns);extra.extend(rows)
                    if rows:bodies[current]=dict(dex=entry,instructions=insns)
            for n,line in enumerate(proc.stdout,1):
                if 'Class descriptor' in line:
                    cls=re.search(r"'L([^;]+);'",line)[1];interfaces.setdefault(cls,[]);ib=False
                elif 'Superclass' in line:
                    m=re.search(r"'L([^;]+);'",line)
                    if m:parents[cls]=m[1]
                elif 'Interfaces' in line:ib=True
                elif ib:
                    m=re.search(r"#\d+\s+: 'L([^;]+);'",line)
                    if m:interfaces[cls].append(m[1])
                    elif 'fields' in line or 'methods' in line:ib=False
                h=HEADER.search(line)
                if h:
                    flush();insns=[];current=method_id(h[1]);methods[current]={'edges':[]};continue
                if current is None:continue
                ins=INSN.search(line)
                if not ins:continue
                off,text=ins.groups();insns.append((off,n,text));loc=dict(dex=entry,offset=off,line=n)
                inv=INVOKE.search(text)
                if inv:
                    kind,args,owner,name,sig=inv.groups();methods[current]['edges'].append(dict(target=owner+'.'+name+sig,kind=kind,**loc))
                    if kind.startswith('invoke-static'):methods[current]['edges'].append(dict(target=owner+'.<clinit>()V',kind='class-initializer',**loc))
                c=re.search(r'new-instance v\d+, L([^;]+);',text)
                # Static field access also initializes its declaring class; old graph missed this.
                s=re.search(r'^(?:sget|sput)[^ ]* v\d+, L([^;]+);\.',text)
                if c or s:methods[current]['edges'].append(dict(target=(c or s)[1]+'.<clinit>()V',kind='class-initializer',**loc))
                c=re.search(r'const-class v\d+, L([^;]+);',text)
                if c and '.dependencies()' in current:methods[current]['edges'].append(dict(target=c[1]+'.create(Landroid/content/Context;)Ljava/lang/Object;',kind='startup-dependency',**loc))
            flush();err=proc.stderr.read()
            if proc.wait():raise RuntimeError(err)
    return methods,parents,interfaces,extra,bodies

def trace(mid,paths):
    if mid not in paths:return {'startup_reachable':'unknown','reachability_reason':'callback/dispatch/reflection/async or branch unresolved'}
    path=[];cur=mid
    while paths[cur]['parent'] is not None:
        item=paths[cur];path.append(dict(caller=item['parent'],callee=cur,**item['edge']));cur=item['parent']
    return {'startup_reachable':'conditional-static','root':paths[mid]['root'],'path':list(reversed(path))}

def scan_one(entry,out):
    key=entry['key'];old=json.loads((BG/(key+'.json')).read_text());base={'key':key,'apk_sha256':entry['apk_sha256'],'status':'unknown','activity':[],'provider':[]}
    try:
        if old['status']!='scanned' or old['apk_sha256']!=entry['apk_sha256']:raise ValueError('Pinned APK identity unavailable')
        apk=Path(old['apk'])
        if sha(apk)!=entry['apk_sha256']:raise ValueError('APK hash mismatch')
        methods,parents,interfaces,extras,bodies=parse(apk)
        prior=json.load(gzip.open(BG/(key+'-graph-result.json.gz'),'rt'))
        roots=prior['roots']
        ap,au,_=lifecycle_paths(methods,parents,interfaces,[{**r,'category':'launcher_activity'} for r in roots])
        # Restore original categories after reusing the optimized resolver.
        orig={r['method']:r for r in roots}
        for p in ap.values():p['root']=orig[p['root']['method']]
        lp,lu,_=lifecycle_paths(methods,parents,interfaces,roots)
        acts=activity_rows(extras,old['activities'],set(old['launchers']),parents,interfaces,lp)
        for r in acts:r.update(trace(r['method'],lp))
        providers=[{**r,**trace(r['method'],ap)} for r in extras if r['kind']=='provider']
        selected={r['method'] for r in acts+providers}
        # Save complete method instructions only for witnesses, not the whole APK.
        base.update(status='scanned',apk=str(apk),method_count=len(methods),reachable_method_count=len(ap),activity=acts,provider=providers,
                    launchers=old['launchers'],activities=old['activities'],roots=roots,unresolved_edges=au,
                    source_cache_sha256=sha(BG/(key+'.json')),method_bodies={m:bodies[m] for m in selected},
                    metadata={'base_apk_only':True,'split_dex':'unknown','execution':'not proven'})
    except (OSError,ValueError,RuntimeError,KeyError) as exc:base['error']=str(exc)
    p=out/'evidence'/(key+'.json.gz');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(base).encode(),mtime=0))
    print(key,base['status'],'activity',len(base['activity']),'provider',len(base['provider']),flush=True)
    return {k:v for k,v in base.items() if k not in {'method_bodies','activities','roots'}}

def main():
    pa=argparse.ArgumentParser();pa.add_argument('--out',type=Path,default=HERE);pa.add_argument('--keys',nargs='*');a=pa.parse_args()
    entries=json.loads((ROOT/'benchmark/2026-09-30-v3c-r17j-prospective/freezes/v2/predictions.json').read_text())
    if a.keys:entries=[e for e in entries if e['key'] in a.keys]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(lambda e:scan_one(e,a.out),entries))
    dump(a.out/'scan-results.json',rows)
if __name__=='__main__':main()
