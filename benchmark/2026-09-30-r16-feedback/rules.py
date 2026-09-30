"""Outcome-informed static requirement predicates. No app-name special cases."""
import re
FAMILIES=('service-foreground-null','battery-service-null','vibrator-info-null','pendingintent-null','alarm-initialization-null','process-cpu-jni','documents-provider-permission','storage-initializer')
POLICY={f:('needs_real' if f in {'process-cpu-jni','storage-initializer','documents-provider-permission'} else 'stub_ok') for f in FAMILIES}
INVOKE=re.compile(r'(invoke-[\w/-]+)\s+\{([^}]*)\}, L([^;]+);\.(\S+):(\S+)')
def inspect_method(method,dex,insns):
 rows=[]
 for off,line,text in insns:
  m=INVOKE.search(text)
  if not m:continue
  _,_,owner,name,sig=m.groups();family=None
  if owner in {'android/app/Service','android/app/IActivityManager'} and name in {'startForeground','stopForeground','setServiceForeground','stopServiceToken'}:family='service-foreground-null'
  elif owner=='android/os/BatteryManager' and name in {'getIntProperty','getLongProperty','isCharging','computeChargeTimeRemaining'}:family='battery-service-null'
  elif owner in {'android/os/Vibrator','android/os/SystemVibrator','android/os/VibratorManager'}:family='vibrator-info-null'
  elif owner=='android/app/PendingIntent' and name in {'getBroadcast','getActivity','getService','getForegroundService'}:family='pendingintent-null'
  elif owner=='android/app/AlarmManager':family='alarm-initialization-null'
  elif owner=='android/os/Process' and name=='getElapsedCpuTime':family='process-cpu-jni'
  elif owner=='android/provider/DocumentsProvider' and name=='<init>':family='documents-provider-permission'
  elif owner in {'android/os/Environment','android/os/storage/StorageManager'} and name in {'getExternalStorageDirectory','getExternalStorageDirectories','getExternalFilesDirs','getStorageVolumes','getVolumeList','getPrimaryStorageVolume'}:family='storage-initializer'
  if family:rows.append({'method':method,'dex':dex,'offset':off,'line':line,'instruction':text,'target':owner+'.'+name+sig,'family':family,'runtime_failure':'unknown','class_initializer_context':'.<clinit>' in method})
 return rows

def manifest_providers(raw,package):
 nodes=[];current=None
 for n,line in enumerate(raw.splitlines(),1):
  m=re.match(r'(\s*)E: ([^ ]+)',line)
  if m:
   indent=len(m[1])
   if current is not None and indent<=current['indent']:
    nodes.append(current);current=None
   if m[2]=='provider':current={'indent':indent,'line':n,'name':None,'permission':None}
   continue
  if current is None:continue
  m=re.search(r'A: (?:[^ ]*:)?(name|permission)(?:\([^)]*\))?="([^"]*)"',line)
  if m:
   if m[1]=='name' and current['name'] is not None:continue
   current[m[1]]=m[2]
 if current:nodes.append(current)
 for node in nodes:
  name=node['name']
  node['class']=(package+name if name and name.startswith('.') else package+'.'+name if name and '.' not in name else name or '').replace('.','/')
 return nodes

def provider_gaps(providers,calls):
 direct={c['method'].split('.',1)[0] for c in calls if c['family']=='documents-provider-permission'}
 return [{**p,'verdict':'declared-documents-provider-missing-MANAGE_DOCUMENTS' if p['class'] in direct and p['permission']!='android.permission.MANAGE_DOCUMENTS' else 'permission-present' if p['class'] in direct else 'unknown-provider-inheritance','is_gap':p['class'] in direct and p['permission']!='android.permission.MANAGE_DOCUMENTS'} for p in providers]
