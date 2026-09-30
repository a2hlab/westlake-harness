"""Static runtime requirements for task90 misses; no app keys or outcomes."""
from scan_apps import INVOKE

FAMILIES=('common-event-jni','jobscheduler-startup','shortcutmanager','guest-thread-ready','jna-native-resource','egl-camera-jni','app-native-loader')
POLICY={f:('stub_ok' if f in {'jobscheduler-startup','shortcutmanager'} else 'needs_real') for f in FAMILIES}

def inspect_method(method,dex,insns):
 out=[]
 for off,line,text in insns:
  m=INVOKE.search(text)
  if not m:continue
  _,_,owner,name,sig=m.groups();family=None
  framework_context=owner.startswith(('android/content/','android/app/','androidx/core/content/'))
  if framework_context and ((name.startswith('registerReceiver') and 'Landroid/content/BroadcastReceiver;' in sig) or (name in {'sendBroadcast','sendOrderedBroadcast','sendBroadcastAsUser','sendOrderedBroadcastAsUser'} and 'Landroid/content/Intent;' in sig)):
   family='common-event-jni'
  elif owner.startswith(('android/app/job/','androidx/work/')) and name not in {'toString','hashCode','equals'}:family='jobscheduler-startup'
  elif owner=='android/content/pm/ShortcutManager':family='shortcutmanager'
  elif owner.startswith(('io/flutter/embedding/engine/FlutterJNI','io/flutter/embedding/engine/loader/FlutterLoader')) and name in {'loadLibrary','init','ensureInitializationComplete','ensureInitializationCompleteAsync','startInitialization','attachToNative'}:family='guest-thread-ready'
  elif owner.startswith('com/sun/jna/') and name in {'<clinit>','<init>','load','loadLibrary','getInstance','getNativeSize','register'}:family='jna-native-resource'
  elif owner.startswith(('android/hardware/Camera','javax/microedition/khronos/egl/','com/google/android/gles_jni/')):family='egl-camera-jni'
  if family:out.append({'method':method,'dex':dex,'offset':off,'line':line,'instruction':text,'target':owner+'.'+name+sig,'family':family,'verdict':'conditional-runtime-requirement','missing_implementation':'unknown','runtime_condition':'Exact runtime registration/service/guest-thread state remains unknown; API use alone does not prove failure.'})
 return out
