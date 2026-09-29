#!/usr/bin/env python3
"""APK-only, bounded startup call graph. Absence of a path is UNKNOWN, never no.

Roots are manifest Application/launcher Activity/provider callbacks and explicit
androidx.startup metadata. Exact calls and uniquely-resolved inheritance are
followed. Ambiguous interface/virtual targets, framework callbacks, reflection,
async work and branch feasibility are not guessed.
"""
import collections,concurrent.futures,json,re,subprocess,tempfile,zipfile
from pathlib import Path
from scan_jni import HERE,DEXDUMP,sha
from scan_apps import HEADER,INSN,INVOKE,load_apps
AAPT2=DEXDUMP.parent/'aapt2'

def manifest(apk):
 p=subprocess.run([str(AAPT2),'dump','xmltree',str(apk),'--file','AndroidManifest.xml'],capture_output=True,text=True,errors='replace',check=True)
 stack=[];nodes=[]
 for n,line in enumerate(p.stdout.splitlines(),1):
  m=re.match(r'(\s*)E: ([^ ]+)',line)
  if m:
   indent=len(m[1])
   while stack and stack[-1]['indent']>=indent:stack.pop()
   node={'tag':m[2],'indent':indent,'attrs':{},'children':[],'line':n}
   if stack:stack[-1]['children'].append(node)
   nodes.append(node);stack.append(node);continue
  m=re.match(r'\s*A: (?:(?:http://[^:]+):)?([^ (=]+)(?:\([^)]*\))?=(.*)',line)
  if m and stack:
   value=m[2];quoted=re.match(r'"([^"]*)"',value);stack[-1]['attrs'][m[1]]=quoted[1] if quoted else value
 root=next(n for n in nodes if n['tag']=='manifest');pkg=root['attrs']['package'];app=next(n for n in root['children'] if n['tag']=='application')
 def qualify(s):
  if not s:return None
  if s.startswith('.'):return pkg+s
  return s if '.' in s else pkg+'.'+s
 def enabled(n):return n['attrs'].get('enabled','true')!='false'
 main_process=app['attrs'].get('process',pkg)
 launch=[];providers=[];initializers=[]
 for n in app['children']:
  if n['tag'] in ['activity','activity-alias'] and enabled(n):
   for intent in [x for x in n['children'] if x['tag']=='intent-filter']:
    actions=[x['attrs'].get('name') for x in intent['children'] if x['tag']=='action'];cats=[x['attrs'].get('name') for x in intent['children'] if x['tag']=='category']
    if 'android.intent.action.MAIN' in actions and 'android.intent.category.LAUNCHER' in cats:launch.append({'class':qualify(n['attrs'].get('targetActivity') or n['attrs'].get('name')),'process':n['attrs'].get('process',main_process),'line':n['line']})
  if n['tag']=='provider' and enabled(n):
   prov={'class':qualify(n['attrs'].get('name')),'process':n['attrs'].get('process',main_process),'line':n['line']};providers.append(prov)
   for child in n['children']:
    if child['tag']=='meta-data' and child['attrs'].get('value')=='androidx.startup':initializers.append({'class':qualify(child['attrs'].get('name')),'provider':prov,'line':child['line']})
 return {'package':pkg,'application':qualify(app['attrs'].get('name')) or 'android.app.Application','application_process':main_process,'application_line':app['line'],'launchers':launch,'providers':providers,'initializers':initializers,'raw':p.stdout}

def method_id(header):
 left,sep,sig=header.partition(':');cls,_,name=left.rpartition('.')
 return cls.replace('.','/')+'.'+name+sig if sep else header

def compute_paths(methods,parents,interfaces,roots):
 def resolve(owner,suffix):
  seen=set()
  while owner and owner not in seen:
   seen.add(owner);target=owner+'.'+suffix
   if target in methods:return target
   owner=parents.get(owner)
  return None
 # Inverted method signatures: only used for uniquely-resolved interface calls.
 signatures=collections.defaultdict(list)
 for m in methods:signatures[m.split('.',1)[1]].append(m)
 def subtype(cls,base,seen=None):
  seen=set() if seen is None else seen
  if cls==base:return True
  if cls in seen:return False
  seen.add(cls)
  return any(subtype(x,base,seen) for x in [parents.get(cls)]+interfaces.get(cls,[]) if x)
 discovered={r['method']:{'root':r,'parent':None,'edge':None} for r in roots if r['method'] in methods};queue=collections.deque(discovered);unresolved=collections.Counter()
 while queue:
  caller=queue.popleft()
  for edge in methods[caller]['edges']:
   target=edge['target'];owner,suffix=target.split('.',1);kind=edge['kind'];resolved=None
   if kind.startswith(('invoke-static','invoke-direct','invoke-super')) or kind in {'class-initializer','startup-dependency'}:resolved=resolve(owner,suffix)
   elif kind.startswith(('invoke-virtual','invoke-interface')):
    options={m for m in signatures.get(suffix,[]) if subtype(m.split('.',1)[0],owner)}
    declared=resolve(owner,suffix)
    if declared:options.add(declared)
    if len(options)==1:resolved=next(iter(options))
    elif len(options)>1:unresolved['ambiguous_dispatch']+=1
   if resolved and resolved not in discovered:
    discovered[resolved]={'root':discovered[caller]['root'],'parent':caller,'edge':edge};queue.append(resolved)
   elif not resolved:unresolved['external_or_unresolved_call']+=1
 return discovered,dict(unresolved),resolve

def scan(app):
 apk=Path(app['apk']);key=app['key'];mf=manifest(apk);raw=mf.pop('raw');(HERE/'evidence'/f'manifest-{key}.txt').write_text(raw)
 methods={};parents={};interfaces={};cls=None;interface_block=False
 with zipfile.ZipFile(apk) as archive,tempfile.TemporaryDirectory(prefix='b10-graph-') as td:
  for entry in sorted(n for n in archive.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
   path=Path(td)/entry;path.write_bytes(archive.read(entry));proc=subprocess.Popen([str(DEXDUMP),'-d',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
   current=None
   for lineno,line in enumerate(proc.stdout,1):
    if 'Class descriptor' in line:
     cls=re.search(r"'L([^;]+);'",line)[1];interfaces.setdefault(cls,[]);interface_block=False
    elif 'Superclass' in line:
     m=re.search(r"'L([^;]+);'",line)
     if m:parents[cls]=m[1]
    elif 'Interfaces' in line:interface_block=True
    elif interface_block:
     m=re.search(r"#\d+\s+: 'L([^;]+);'",line)
     if m:interfaces[cls].append(m[1])
     elif 'fields' in line or 'methods' in line:interface_block=False
    h=HEADER.search(line)
    if h:
     current=method_id(h[1]);methods[current]={'dex':entry,'line':lineno,'edges':[]};continue
    if current is None:continue
    m=INSN.search(line)
    if not m:continue
    offset,text=m.groups();inv=INVOKE.search(text)
    if inv:
     kind,args,owner,name,sig=inv.groups();methods[current]['edges'].append({'target':owner+'.'+name+sig,'kind':kind,'dex':entry,'offset':offset,'line':lineno})
    # Constructing a class or calling a static member can trigger its <clinit>.
    c=re.search(r'new-instance v\d+, L([^;]+);',text)
    if c:methods[current]['edges'].append({'target':c[1]+'.<clinit>()V','kind':'class-initializer','dex':entry,'offset':offset,'line':lineno})
    if inv and inv[1].startswith('invoke-static'):methods[current]['edges'].append({'target':inv[3]+'.<clinit>()V','kind':'class-initializer','dex':entry,'offset':offset,'line':lineno})
    c=re.search(r'const-class v\d+, L([^;]+);',text)
    if c and '.dependencies()' in current:
     methods[current]['edges'].append({'target':c[1]+'.create(Landroid/content/Context;)Ljava/lang/Object;','kind':'startup-dependency','dex':entry,'offset':offset,'line':lineno})
   err=proc.stderr.read()
   if proc.wait():raise RuntimeError(err)
 def root_methods(name,suffixes,category,line):
  if not name:return []
  found=[];owner=name.replace('.','/')
  for suffix in suffixes:
   cur=owner;seen=set()
   while cur and cur not in seen:
    seen.add(cur);mid=cur+'.'+suffix
    if mid in methods:found.append({'method':mid,'category':category,'manifest_class':name,'manifest_line':line});break
    cur=parents.get(cur)
  return found
 roots=root_methods(mf['application'],['<clinit>()V','<init>()V','attachBaseContext(Landroid/content/Context;)V','onCreate()V'],'application',mf['application_line'])
 startup_processes={x['process'] for x in mf['launchers']} or {mf['application_process']}
 for item in mf['launchers']:roots+=root_methods(item['class'],['<clinit>()V','<init>()V','onCreate(Landroid/os/Bundle;)V','onCreate(Landroid/os/Bundle;Landroid/os/PersistableBundle;)V','onStart()V','onResume()V'],'launcher_activity',item['line'])
 for item in mf['providers']:
  if item['process'] in startup_processes:roots+=root_methods(item['class'],['<clinit>()V','<init>()V','onCreate()Z'],'provider',item['line'])
 for item in mf['initializers']:
  if item['provider']['process'] in startup_processes:roots+=root_methods(item['class'],['<clinit>()V','<init>()V','create(Landroid/content/Context;)Ljava/lang/Object;','dependencies()Ljava/util/List;'],'androidx_startup_metadata',item['line'])
 paths,unresolved,_=compute_paths(methods,parents,interfaces,roots)
 def evidence_for(mid):
  if mid not in paths:return {'startup_reachable':'unknown','reason':'No path in bounded APK graph; reflection, callbacks, ambiguous dispatch, framework bodies and async scheduling are not resolved.'}
  trace=[];cur=mid
  while paths[cur]['parent'] is not None:
   row=paths[cur];trace.append({'caller':row['parent'],'callee':cur,**row['edge']});cur=row['parent']
  trace.reverse()
  return {'startup_reachable':'yes-static','root':paths[mid]['root'],'path':trace,'reason':'Path in bounded static graph, conditional on manifest initialization and branch execution; not proof of an executed call.'}
 calls=[]
 for call in app['calls']:calls.append({'method':call['method'],'dex':call['dex'],'offset':call['offset'],'service':call['service'],**evidence_for(method_id(call['method']))})
 features={k:evidence_for(method_id(v['method'])) for k,v in app['features'].items()}
 # Feature evidence in v1 was only its first occurrence; search reachable nodes for all references.
 needles={'sqlite':'android/database/sqlite/','jna':'com/sun/jna/','koin':'org/koin/','workmanager':'androidx/work/','appcompat':'androidx/appcompat/','flutter':'io/flutter/'}
 for caller in paths:
  for edge in methods[caller]['edges']:
   for feature,needle in needles.items():
    if edge['target'].startswith(needle) and features.get(feature,{}).get('startup_reachable')!='yes-static':features[feature]={**evidence_for(caller),'reference':edge}
 result={'key':key,'apk_sha256':app['sha256'],'scanner_sha256':sha(Path(__file__)),'manifest':mf,'roots':roots,'method_count':len(methods),'reachable_method_count':len(paths),'unresolved_edges':unresolved,'calls':calls,'features':features,'scope':__doc__}
 (HERE/'evidence'/f'reachability-{key}.json').write_text(json.dumps(result,indent=2)+'\n');print(key,len(methods),len(paths),sum(x['startup_reachable']=='yes-static' for x in calls),flush=True);return result

def main():
 apps=load_apps()
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(scan,apps))
 (HERE/'reachability-results.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
