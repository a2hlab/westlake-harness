"""Operational audit only: read frozen inputs and reports, emit evidence; no device operations."""
import collections,gzip,hashlib,io,json,struct,sys,zipfile
from pathlib import Path
import lab_paths
P=lab_paths.inputs()
d=Path.home()/'a2hlab/static'; out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
c=json.loads((P/'corpus100.json').read_text());cache=P/'audit-static100-cache';cache.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
prefixes={'react-native':'Lcom/facebook/react/','flutter':'Lio/flutter/','unity-il2cpp':'Lcom/unity3d/player/','gecko':'Lorg/mozilla/geckoview/','libgdx':'Lcom/badlogic/gdx/','arc':'Larc/','compose':'Landroidx/compose/','kotlin':'Lkotlin/','cordova':'Lorg/apache/cordova/'}
def dex_markers(b):
 assert b[:4]==b'dex\x0a',b[:8]
 sn,so,tn,to=struct.unpack_from('<4I',b,56);cn,co=struct.unpack_from('<2I',b,96)
 count=collections.Counter();examples={}
 for off in range(co,co+cn*32,32):
  ti=struct.unpack_from('<I',b,off)[0];si=struct.unpack_from('<I',b,to+ti*4)[0];sp=struct.unpack_from('<I',b,so+si*4)[0]
  while b[sp]&128:sp+=1
  sp+=1;name=b[sp:b.index(b'\0',sp)].decode('utf-8','replace')
  for k,p in prefixes.items():
   if name.startswith(p):count[k]+=1;examples.setdefault(k,name)
 return count,examples
records={};maps={};errors=[]
for key,a in c['apps'].items():
 paths={'scan':d/'scans'/f'{key}.json','oh':d/'oh'/f'{key}.json','map':d/'maps'/key/'gap-map.json'}
 if not all(p.exists() for p in paths.values()):errors.append([key,'missing outputs',[k for k,p in paths.items() if not p.exists()]]);continue
 s,o,m=[json.loads(paths[k].read_text()) for k in ['scan','oh','map']]
 apk=s['apk'];nr=s['inventory']['native_resolution'];ip=Path(a['input']);cp=cache/(apk['sha256']+'.json')
 if cp.exists():z=json.loads(cp.read_text())
 else:
  z={'sha256':sha(ip),'class_markers':{},'class_examples':{},'components':[]};counts=collections.Counter();ex={}
  def inspect(az,label):
   for n in az.namelist():
    if n.endswith('.dex'):
     bs=az.read(n);cc,ee=dex_markers(bs);counts.update(cc);ex.update(ee)
     z['components'].append({'name':label+n,'sha256':hashlib.sha256(bs).hexdigest(),'bytes':len(bs)})
  with zipfile.ZipFile(ip) as az:
   if ip.suffix=='.xapk':
    for n in sorted(az.namelist()):
     if n.endswith('.apk'):
      bs=az.read(n);z['components'].append({'name':n,'sha256':hashlib.sha256(bs).hexdigest(),'bytes':len(bs)})
      with zipfile.ZipFile(io.BytesIO(bs)) as nested:inspect(nested,n+'!')
   else:inspect(az,'')
  z['class_markers']=dict(counts);z['class_examples']=ex;cp.write_text(json.dumps(z,indent=1)+'\n')
 elfs=s['inventory']['elfs'];libs=sorted({e.get('soname') or e.get('archive_entry','').split('/')[-1] for e in elfs}); engines=[]
 for engine,lib in [('flutter','libflutter.so'),('react-native','libreactnative.so'),('unity-il2cpp','libunity.so'),('gecko','libxul.so')]:
  if lib in libs:engines.append(engine)
 if any('react' in n for n in libs) and z['class_markers'].get('react-native') and 'react-native' not in engines:engines.append('react-native')
 if 'libgdx.so' in libs or 'libarc.so' in libs:engines.append('libgdx/arc')
 old=a.get('original_stack',a['stack'])
 if len(engines)>1:stack='mixed-engines'
 elif engines:stack=engines[0]
 elif old.startswith('webview hybrid') or z['class_markers'].get('cordova'):stack='webview-hybrid'
 elif key in ['vlc','ppsspp','fd-organicmaps','fd-stk','fd-minetest','fd-mpv','co-client','co-candycrushsaga']:stack='native-engine'
 else:stack='android-jvm'
 issues=[]
 checks={'input_sha256':z['sha256']==apk['sha256'],'package':apk['package']==a['package'],'version':apk['version_name']==a['version'],'scan_map_hash':m['app']['apk_sha256']==apk['sha256'],'map_package':m['app']['package']==a['package'],'map_version':m['app']['version']==a['version'],'scan_path':apk['path']==a['input'],'launcher_present':bool(apk.get('main_activities')),'arm64_provider_exclusions_documented':all(e.get('archive_entry') in a.get('native_provider_exclusions',[]) for e in elfs if e.get('abi')=='arm64-v8a' and not e.get('abi_matches_machine',True)),'selected_elf_count':nr['selected_packaged_elf_count']==sum(e.get('abi')=='arm64-v8a' and e.get('abi_matches_machine',True) for e in elfs),'oh_app_key':set(o['apps'])=={key},'abi':nr['abi_status'] in ['target-abi-available','no-packaged-native-libraries'],'runtime_lock':s['runtime_lock_id']==json.loads((d/'runtime-lock.json').read_text())['runtime_lock_id'],'unique_row_ids':len(m['rows'])==len({r['id'] for r in m['rows']})}
 for name,ok in checks.items():
  if not ok:issues.append(name)
 if issues:errors.append([key,issues])
 rec={'input':a['input'],'package':apk['package'],'version':apk['version_name'],'source':a['source'],'original_stack':old,'stack':stack,'bundled_engines':engines,'abi_status':nr['abi_status'],'native_resolution':nr,'native_libraries':libs,'excluded_native_providers':[{'archive_entry':e.get('archive_entry'),'sha256':e['sha256'],'machine_abi':e.get('machine_abi')} for e in elfs if e.get('abi')=='arm64-v8a' and not e.get('abi_matches_machine',True)],'elf_anomalies':[{k:e.get(k) for k in ['name','archive_entry','abi','machine_abi','machine','sha256','abi_matches_machine','readelf_ok']} for e in elfs if not e.get('abi_matches_machine',True) or not e.get('readelf_ok',True)],'apk':apk,'artifact':z,'scan_summary':s['summary'],'runtime_lock_id':s['runtime_lock_id'],'outputs':{k:{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for k,p in paths.items()},'oh_summary':{k:v for k,v in o['apps'][key].items() if k!='missing'},'oh_missing':o['apps'][key]['missing'],'row_count':len(m['rows']),'verdicts':dict(collections.Counter(r['verdict'] for r in m['rows'])),'checks':checks,'clinit_findings':[f for f in s['findings'] if any(e.get('method')=='<clinit>' for e in f.get('evidence',[]) if isinstance(e,dict))]}
 records[key]=rec;maps[key]=m
 print(key,stack,nr['abi_status'],issues,flush=True)
(out/'audit.json').write_text(json.dumps({'apps':records,'errors':errors,'complete':len(records)==100 and not errors,'stack_counts':dict(collections.Counter(a['stack'] for a in records.values())),'abi_counts':dict(collections.Counter(a['abi_status'] for a in records.values()))},indent=1)+'\n')
(out/'gap-maps.json.gz').write_bytes(gzip.compress(json.dumps(maps,sort_keys=True).encode(),mtime=0))
print('SUMMARY',len(records),'errors',errors,flush=True)
