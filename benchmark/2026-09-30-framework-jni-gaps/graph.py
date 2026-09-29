"""Bounded DEX call graph using the existing dexdump grammar, with no dispatch guesses."""
import collections,gzip,json,re,subprocess,sys,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-09-29-static-wall-prediction'))
from scan_apps import HEADER,INSN,INVOKE
from scan_reachability import method_id,compute_paths,manifest
from scan_jni import DEXDUMP,sha

def parse_zip(path, methods=None, parents=None, interfaces=None, declarations=None):
    methods={} if methods is None else methods
    parents={} if parents is None else parents
    interfaces={} if interfaces is None else interfaces
    declarations=[] if declarations is None else declarations
    with zipfile.ZipFile(path) as z,tempfile.TemporaryDirectory(prefix='jni-gap-dex-') as tmp:
      for entry in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
        dex=Path(tmp)/entry;dex.write_bytes(z.read(entry))
        proc=subprocess.Popen([str(DEXDUMP),'-d','-f',str(dex)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
        current=None;cls=None;name=None;sig=None;ib=False
        for n,line in enumerate(proc.stdout,1):
          if 'Class descriptor' in line:
            cls=re.search(r"'L([^;]+);'",line)[1];interfaces.setdefault(cls,[]);ib=False;current=None
          elif 'Superclass' in line:
            m=re.search(r"'L([^;]+);'",line)
            if m:parents[cls]=m[1]
          elif 'Interfaces' in line:ib=True
          elif ib:
            m=re.search(r"#\d+\s+: 'L([^;]+);'",line)
            if m:interfaces[cls].append(m[1])
            elif 'fields' in line or 'methods' in line:ib=False
          if re.match(r'\s+name\s+:',line):
            m=re.search(r"name\s+: '([^']+)'",line)
            if m:name=m[1]
          elif re.match(r'\s+type\s+:',line):
            m=re.search(r"type\s+: '(\([^']+)'",line)
            if m:sig=m[1]
          elif re.search(r'access\s+:.*\bNATIVE\b',line):
            declarations.append({'id':cls+'.'+name+sig,'class':cls,'method':name,'signature':sig,'jar':str(path),'dex':entry,'line':n})
          h=HEADER.search(line)
          if h:
            current=method_id(h[1]);methods.setdefault(current,{'edges':[],'dex':entry,'line':n,'archive':str(path)});continue
          if current is None or not any(x in line for x in ('invoke-','new-instance','const-class')):continue
          ins=INSN.search(line)
          if not ins:continue
          offset,text=ins.groups();inv=INVOKE.search(text)
          evidence={'dex':entry,'offset':offset,'line':n,'archive':str(path)}
          if inv:
            kind,args,owner,name,sig=inv.groups()
            methods[current]['edges'].append({'target':owner+'.'+name+sig,'kind':kind,**evidence})
            if kind.startswith('invoke-static'):
              methods[current]['edges'].append({'target':owner+'.<clinit>()V','kind':'class-initializer',**evidence})
          c=re.search(r'new-instance v\d+, L([^;]+);',text)
          if c:methods[current]['edges'].append({'target':c[1]+'.<clinit>()V','kind':'class-initializer',**evidence})
          c=re.search(r'const-class v\d+, L([^;]+);',text)
          if c and '.dependencies()' in current:
            methods[current]['edges'].append({'target':c[1]+'.create(Landroid/content/Context;)Ljava/lang/Object;','kind':'startup-dependency',**evidence})
        err=proc.stderr.read()
        if proc.wait():raise RuntimeError(str(path)+':'+entry+':'+err)
    return methods,parents,interfaces,declarations

def resolve(target,nodes,parents):
    owner,sep,suffix=target.partition('.')
    if not sep:return None
    seen=set()
    while owner and owner not in seen:
      seen.add(owner);mid=owner+'.'+suffix
      if mid in nodes:return mid
      owner=parents.get(owner)
    return None

def build_masks(methods,parents,native_ids,depth=6):
    nodes=set(methods)|set(native_ids)
    edges={mid:sorted({r for edge in m['edges'] if (r:=resolve(edge['target'],nodes,parents))}) for mid,m in methods.items()}
    masks={mid:1<<i for i,mid in enumerate(native_ids)}
    for _ in range(depth):
      old=masks;new=dict(old)
      for mid,targets in edges.items():
        v=old.get(mid,0)
        for target in targets:v|=old.get(target,0)
        if v:new[mid]=v
      masks=new
    return masks,edges

def startup_roots(mf,methods,parents):
    roots=[]
    def add(name,suffixes,category,line):
      if not name:return
      for suffix in suffixes:
        mid=resolve(name.replace('.','/')+'.'+suffix,methods,parents)
        if mid:roots.append({'method':mid,'category':category,'manifest_class':name,'manifest_line':line})
    add(mf['application'],['<clinit>()V','<init>()V','attachBaseContext(Landroid/content/Context;)V','onCreate()V'],'application',mf['application_line'])
    procs={x['process'] for x in mf['launchers']} or {mf['application_process']}
    for x in mf['launchers']:add(x['class'],['<clinit>()V','<init>()V','onCreate(Landroid/os/Bundle;)V','onCreate(Landroid/os/Bundle;Landroid/os/PersistableBundle;)V','onStart()V','onResume()V'],'launcher_activity',x['line'])
    for x in mf['providers']:
      if x['process'] in procs:add(x['class'],['<clinit>()V','<init>()V','onCreate()Z'],'provider',x['line'])
    for x in mf['initializers']:
      if x['provider']['process'] in procs:add(x['class'],['<clinit>()V','<init>()V','create(Landroid/content/Context;)Ljava/lang/Object;','dependencies()Ljava/util/List;'],'androidx_startup',x['line'])
    return roots

def bits(value):
    while value:
      low=value & -value;yield low.bit_length()-1;value ^= low

if __name__=='__main__':
    package=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3a-74d1d6d4-r8b')
    methods={};parents={};interfaces={};decl=[];inputs=[]
    for jar in sorted((package/'payload/android/framework').glob('*.jar')):
      inputs.append({'path':str(jar),'sha256':sha(jar)})
      parse_zip(jar,methods,parents,interfaces,decl)
      print(jar.name,len(methods),len(decl),flush=True)
    ids=sorted({x['id'] for x in decl})
    masks,edges=build_masks(methods,parents,ids)
    out={'native_ids':ids,'declarations':decl,'methods':methods,'parents':parents,'masks':{k:hex(v) for k,v in masks.items()},'edges':edges,'inputs':inputs,'depth':6,'definition_policy':'Union of supplied JAR definitions; active BCP selection and dynamic overrides are unresolved.'}
    with gzip.open(HERE/'evidence/framework-graph.json.gz','wt') as f:json.dump(out,f)
    print('framework native IDs',len(ids),'methods',len(methods),'APIs with native paths',len(masks),flush=True)
