"""Run inside VM; read all original APK manifests without modifying them."""
import importlib.util,json,struct,sys,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
repo=ROOT.parents[2]
spec=importlib.util.spec_from_file_location('axml',repo/'bms/src/tools/task79-swap-window/shim/axmldump.py');axml=importlib.util.module_from_spec(spec);spec.loader.exec_module(axml)
sys.path.insert(0,str(ROOT.parent/'batch'));import bms_batch as b
manifest=json.loads((ROOT.parent/'batch/apps.json').read_text())['apps']
previous={x['key']:x for x in json.loads((ROOT.parent/'results.json').read_text())['apps']}
def nodes(buf):
 strings=[];off=8;stack=[];root=None
 while off+8<=len(buf):
  typ,header,size=struct.unpack_from('<HHI',buf,off)
  if size<8 or off+size>len(buf):raise ValueError('malformed AXML chunk')
  if typ==1:strings,_=axml.parse_string_pool(buf,off)
  elif typ==0x102:
   ext=off+header;_,name=struct.unpack_from('<iI',buf,ext);start,step,count=struct.unpack_from('<HHH',buf,ext+8)
   node={'tag':strings[name],'attrs':{},'children':[]};ap=ext+start
   for _ in range(count):
    ns,n,raw=struct.unpack_from('<iii',buf,ap);t=buf[ap+15];v=struct.unpack_from('<I',buf,ap+16)[0]
    node['attrs'][strings[n]]=axml.fmt_value(t,v,strings);ap+=step
   if stack:stack[-1]['children'].append(node)
   else:root=node
   stack.append(node)
  elif typ==0x103:stack.pop()
  off+=size
 return root
def normalized(pkg,name):return pkg+name if name.startswith('.') else pkg+'.'+name if '.' not in name else name
rows=[];input_root=Path.home()/'a2hlab/app-inputs'
for app in manifest:
 key=app['key'];identity_error=None
 try:resolved=b.resolve_input(input_root,app);path=Path(resolved['apk'])
 except b.AppFailure as exc:
  identity_error=str(exc);path=input_root/key/(key+'.apk')
  if not path.exists():raise
 with zipfile.ZipFile(path) as z:tree=nodes(z.read('AndroidManifest.xml'))
 pkg=tree['attrs']['package'];application=next(x for x in tree['children'] if x['tag']=='application')
 components=[]
 for node in application['children']:
  if node['tag'] not in ('activity','activity-alias'):continue
  attrs=node['attrs'];name=normalized(pkg,attrs['name']);launcher=False
  for f in node['children']:
   if f['tag']!='intent-filter':continue
   actions={x['attrs'].get('name') for x in f['children'] if x['tag']=='action'}
   categories={x['attrs'].get('name') for x in f['children'] if x['tag']=='category'}
   launcher|='android.intent.action.MAIN' in actions and 'android.intent.category.LAUNCHER' in categories
  target=attrs.get('targetActivity')
  components.append({'name':name,'alias':node['tag']=='activity-alias','target':normalized(pkg,target) if target else None,'enabled':attrs.get('enabled','true'),'launcher':launcher})
 enabled=[x for x in components if x['launcher'] and x['enabled']!='false']
 old=previous[key]['record'];selected_name=old.get('desktop_activity') or (old.get('bms') or {}).get('desktop_activity')
 selected=next((x for x in components if x['name']==selected_name),None)
 basis='BMS observed entry' if selected else 'first enabled manifest launcher'
 if selected is None:selected=enabled[0] if enabled else None
 rows.append({'key':key,'package':pkg,'apk_path':str(path),'apk_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pin_error':identity_error,'selected_entry':selected,'selection_basis':basis,'enabled_launchers':enabled,'all_aliases':[x for x in components if x['alias']]})
result={'keys':len(rows),'selected_alias_keys':[x['key'] for x in rows if x['selected_entry'] and x['selected_entry']['alias']],'enabled_launcher_alias_keys':[x['key'] for x in rows if any(y['alias'] for y in x['enabled_launchers'])],'unresolved_keys':[x['key'] for x in rows if not x['selected_entry']],'apps':rows}
(ROOT/'census.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='apps'})
