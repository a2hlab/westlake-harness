#!/usr/bin/env python3
"""Offline JNI evidence: declarations, ELF exports and concrete native tables."""
import argparse, collections, csv, hashlib, importlib.util, json, re, struct, subprocess, tempfile, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
BASE=Path('/Users/zhaoyue/orca/workspaces')
DEXDUMP=Path.home()/'Library/Android/sdk/build-tools/37.0.0/dexdump'
PACKAGES={'6cb40cd6':BASE/'westlake-generation-6cb40cd6','v3-74d1d6d4':BASE/'westlake-generation-v3-74d1d6d4'}
R8=BASE/'vm-copies/r8b-runtime-jar/oh-adapter-runtime.jar'
R8HASH='d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def identity(path):return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}
def jni_escape(s):
    out=''
    for ch in s:
        if ch in '/.':out+='_' 
        elif ch=='_':out+='_1'
        elif ch==';':out+='_2'
        elif ch=='[':out+='_3'
        elif ch.isascii() and ch.isalnum():out+=ch
        else:
            for i in range(0,len(ch.encode('utf-16-be')),2):out+='_0'+ch.encode('utf-16-be')[i:i+2].hex()
    return out

def declarations(jar):
    out=[];jar_sha=sha(jar)
    with zipfile.ZipFile(jar) as archive, tempfile.TemporaryDirectory(prefix='b10-jar-') as td:
      for entry in sorted(n for n in archive.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
        dex=Path(td)/entry;dex.write_bytes(archive.read(entry))
        p=subprocess.run([str(DEXDUMP),'-f',str(dex)],capture_output=True,text=True,errors='replace')
        if p.returncode:raise RuntimeError(p.stderr)
        cls=name=sig=None
        for n,line in enumerate(p.stdout.splitlines(),1):
            m=re.search(r"Class descriptor\s+: 'L(.+);'",line)
            if m:cls=m[1]
            m=re.search(r"name\s+: '([^']+)'",line)
            if m:name=m[1]
            m=re.search(r"type\s+: '(\([^']+)'",line)
            if m:sig=m[1]
            if re.search(r'access\s+:.*\bNATIVE\b',line):
                out.append({'class':cls,'method':name,'signature':sig,'declaration':f'{jar}!{entry}:dexdump:{n}', 'jar_sha256':jar_sha, 'id':f'{cls}.{name}{sig}'})
    return out

class ELF:
    def __init__(self,path):
        self.path=path;self.data=path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.data)
        if h[0][:6]!=b'\x7fELF\x02\x01':raise ValueError('unsupported ELF, do not guess: '+str(path))
        self.sections=[]
        for i in range(h[12]):
            v=struct.unpack_from('<IIQQQQIIQQ',self.data,h[6]+i*h[11]);self.sections.append(dict(zip(('no','type','flags','addr','offset','size','link','info','align','entsize'),v)))
        self.symbols=[];self.exports={};tables={}
        for idx,s in enumerate(self.sections):
            if s['type'] not in [2,11]:continue
            names=self.sections[s['link']];table=[]
            for j in range(0,s['size'],s['entsize']):
                no,info,other,ndx,val,size=struct.unpack_from('<IBBHQQ',self.data,s['offset']+j)
                start=names['offset']+no;end=self.data.find(b'\0',start)
                sym={'name':self.data[start:end].decode(errors='replace'),'bind':info>>4,'type':info&15,'section':ndx,'value':val,'size':size}
                table.append(sym)
                if s['type']==11 and ndx and info>>4 in [1,2] and other&3 in [0,3]:self.exports[sym['name']]=sym
            tables[idx]=table
            if s['type']==2:self.symbols=table
        if not self.symbols:self.symbols=list(self.exports.values())
        self.sym_at=collections.defaultdict(list)
        for s in self.symbols:
            if s['section']:self.sym_at[s['value']].append(s['name'])
        self.pointers={}
        for s in self.sections:
            if s['type']!=4:continue
            for j in range(0,s['size'],s['entsize']):
                off,info,add=struct.unpack_from('<QQq',self.data,s['offset']+j);kind=info&0xffffffff
                sym=tables[s['link']][info>>32]
                if kind==1027:self.pointers[off]=add
                elif kind in [257,1025] and sym['section']:self.pointers[off]=sym['value']+add
    def at(self,addr,n=256):
        for s in self.sections:
            if s['type']!=8 and s['addr']<=addr<s['addr']+s['size']:
                off=s['offset']+addr-s['addr'];return self.data[off:off+min(n,s['size']-(addr-s['addr']))]
        return b''
    def cstr(self,addr):return self.at(addr).split(b'\0',1)[0].decode('ascii',errors='replace')
    def tables(self):
        rows=[]
        for addr,target in self.pointers.items():
            if addr+8 not in self.pointers or addr+16 not in self.pointers:continue
            name=self.cstr(target);sig=self.cstr(self.pointers[addr+8])
            if not re.fullmatch(r'[A-Za-z_$][\w$]*',name) or not re.fullmatch(r'\([^)]*\)[VZBCSIJFD\[L].*',sig):continue
            fn=self.pointers[addr+16]
            syms=self.sym_at.get(fn,[])
            if not syms:continue
            rows.append({'method':name,'signature':sig,'table_address':hex(addr),'function_address':hex(fn),'function_symbols':syms})
        return rows

def source_tables(classes):
    roots=[REPO/'bms/src/adapter/framework']
    out=collections.defaultdict(list)
    files=[]
    for root in roots:
      for p in root.rglob('*'):
        if not p.is_file() or p.suffix not in ['.cpp','.cc','.c','.h']:continue
        txt=p.read_text(errors='replace')
        if 'JNINativeMethod' not in txt and 'NATIVE_METHOD' not in txt:continue
        candidates={x for x in re.findall(r'"([A-Za-z_$][\w$/]+)"',txt) if x in classes}
        stem=p.stem.replace('_','/')
        if stem in classes:candidates={stem}
        if len(candidates)!=1:continue
        cls=next(iter(candidates));files.append(identity(p))
        pattern=r'\{\s*"([\w$]+)"\s*,\s*"(\([^"\n]+)"\s*,\s*([^\n{}]+)'
        for m in re.finditer(pattern,txt):
            function=m[3].strip().rstrip(',').strip()
            tokens=re.findall(r'[A-Za-z_]\w*',function)
            tokens=[t for t in tokens if t not in ['reinterpret_cast','void','static_cast','jlong','jint']]
            out[(cls,m[1],m[2])].append({'path':str(p),'line':txt.count('\n',0,m.start())+1,'function_tokens':tokens, 'source_text':m[0].strip()})
    return out,files

def classify(decl, libraries, sources):
    cls,name,sig=decl['class'],decl['method'],decl['signature']
    short='Java_'+jni_escape(cls)+'_'+jni_escape(name)
    long=short+'__'+jni_escape(sig[1:sig.index(')')])
    exports=[];stub=[];registered=[];ambiguous=[];strong_registration=False
    reg_name='register_'+cls.replace('android/database/sqlite/', 'android/database/').replace('/','_').replace('$','_')
    for lib in libraries:
        for symname,sym in lib['exports'].items():
            if (symname==reg_name or reg_name+'EP7_JNIEnv' in symname) and sym['bind']==1:strong_registration=True
            if symname in [short,long]:exports.append({'library':lib['path'],'symbol':symname,'bind':sym['bind']})
            if (symname==reg_name or reg_name+'EP7_JNIEnv' in symname) and sym['bind']==2 and sym['size']==8 and lib['stub_bodies'].get(symname) in ['00008052c0035fd6','000080d2c0035fd6','e0031f2ac0035fd6']:
                stub.append({'library':lib['path'],'symbol':symname,'size':sym['size'],'body_hex':lib['stub_bodies'].get(symname),'basis':'weak no-op registration; does not implement the declared method'})
        for table in lib['tables_by_sig'].get((name,sig),[]):
            matches=[]
            for src in sources.get((cls,name,sig),[]):
                if Path(src['path']).name in lib['compiled_sources'] and any(re.search(r'(?<![A-Za-z_])'+re.escape(t)+r'(?:E|[^A-Za-z_]|$)', sym) for t in src['function_tokens'] for sym in table['function_symbols']):matches.append(src)
            item={'library':lib['path'],**table,'source':matches}
            if matches:registered.append(item)
            else:ambiguous.append(item)
    if exports:return 'exported',exports,'Exact JNI escaped export exists; namespace and invocation remain runtime questions.'
    if registered:return 'registered',registered,'Compiled ELF native table contains exact name/descriptor/function pointer; source establishes owning class.'
    if stub and not strong_registration:return 'stub',stub,'Only weak no-op registration found for this class; no matching export or proven real table.'
    if cls.startswith('adapter/') and not ambiguous:return 'missing',[],'No export or concrete matching native table in any packaged ELF; adapter direct-binding declaration.'
    return 'unknown',ambiguous,'No class-attributed compiled registration proof; absence of Java_ export alone does not prove a missing dynamically registered method.'

def scan(package,overlay=R8):
    meta=json.loads((package/'package.json').read_text());inputs=[];libs=[];cache={}
    for rel,expected in meta['files'].items():
        if not rel.endswith('.so'):continue
        p=package/rel;actual=sha(p)
        if actual!=expected:raise ValueError('package hash mismatch '+str(p))
        inputs.append(identity(p))
        if actual in cache:continue
        e=ELF(p);tables=e.tables();by=collections.defaultdict(list)
        for row in tables:by[(row['method'],row['signature'])].append(row)
        lib={'path':str(p),'sha256':actual,'exports':e.exports,'tables_by_sig':by,
             'compiled_sources':{s['name'] for s in e.symbols if s['type']==4},
             'stub_bodies':{n:e.at(v['value'],v['size']).hex() for n,v in e.exports.items() if 'register_' in n and v['bind']==2 and v['size']<=8}}
        libs.append(lib);cache[actual]=True
    decls={};jar_inputs=[]
    for jar in sorted((package/'payload/android/framework').rglob('*.jar')):
        actual=sha(jar);rel=str(jar.relative_to(package))
        if actual!=meta['files'][rel]:raise ValueError('JAR hash mismatch '+str(jar))
        with zipfile.ZipFile(jar) as z:
            if not any(n.endswith('.dex') for n in z.namelist()):continue
        jar_inputs.append(identity(jar))
        # Runtime overlay replaces, rather than adds duplicate classes from, B5.
        if jar.name=='oh-adapter-runtime.jar' and overlay:continue
        for d in declarations(jar):decls[d['id']]=d
    if overlay:
        if sha(overlay)!=R8HASH:raise ValueError('r8b hash mismatch')
        jar_inputs.append(identity(overlay))
        for d in declarations(overlay):decls[d['id']]=d
    sources,source_inputs=source_tables({d['class'] for d in decls.values()})
    rows=[]
    for d in sorted(decls.values(),key=lambda x:x['id']):
        status,evidence,reason=classify(d,libs,sources)
        rows.append({**d,'status':status,'evidence':evidence,'reason':reason})
    return {'scanner_sha256':sha(Path(__file__)), 'package':str(package),'package_manifest_sha256':sha(package/'package.json'),'generation':meta['generation'],'overlay':identity(overlay) if overlay else None,'inputs':inputs+jar_inputs,'source_inputs':source_inputs,'counts':dict(collections.Counter(r['status'] for r in rows)), 'methods':rows}

def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    targets={'custom':a.package} if a.package else PACKAGES
    results={}
    for name,path in targets.items():
        results[name]=scan(path);print(name,results[name]['counts'],flush=True)
    target=a.output or HERE/'jni-results.json';target.write_text(json.dumps(results,indent=2)+'\n')
    if not a.output:
        with (HERE/'jni-matrix.csv').open('w') as f:
            w=csv.writer(f);w.writerow(['generation','class','method','signature','status','declaration','reason','evidence'])
            for name,r in results.items():
                for m in r['methods']:w.writerow([name,m['class'],m['method'],m['signature'],m['status'],m['declaration'],m['reason'],json.dumps(m['evidence'],separators=(',',':'))])
if __name__=='__main__':main()
