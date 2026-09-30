"""Post-run evidence adjudication. Does not import or inspect forecasts."""
import gzip,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
# Earliest evidenced initialization blocker; downstream symptoms remain in raw excerpts.
RULED={
'antennapod':('app-native-loader',r'Caused by:.*dlopen_ns failed','Native Conscrypt bind failure precedes downstream FeedUpdateManager NPE.'),
'fd-auxio':('velocitytracker-jni',r'No implementation found.*VelocityTracker','Main launch missing JNI; outer explicitly confirms 5cd native variant.'),
'fd-com-amaze-filemanager':('clinit-failure',r'ArrayIndexOutOfBoundsException: length=0','AppConfig initializer calls Environment with empty storage array; not missing DEX.'),
'fd-com-kunzisoft-keepass-libre':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Main ViewModel initialization cause chain.'),
'fd-droidify':('service-foreground-null',r'NullPointerException.*setServiceForeground','Outer identifies actual foreground service failure; earlier common-event warning does not by itself prove the first visual blocker.'),
'fd-android':('alarm-initialization-null',r'Caused by:.*getClass','Deepest bind cause at AndroidAlarmManager constructor; does not prove which service object is missing.'),
'fd-k9':('alarm-initialization-null',r'Caused by:.*getClass','Deepest Koin bind cause at AndroidAlarmManager constructor.'),
'fd-api':('theme-appcompat',r'Caused by:.*Theme.AppCompat','Main Activity theme failure; LocalSocket background exception is not selected.'),
'fd-app':('app-native-loader',r'Caused by:.*dlopen_ns failed','libgdx depends on unavailable libstdc++ in runtime lookup.'),
'fd-breezyweather':('app-native-loader',r'Caused by:.*dlopen_ns failed','libnrb load failure precedes lateinit instance symptom.'),
'fd-calendar':('jobscheduler-startup',r'Caused by:.*JobScheduler.cancel','JobScheduler null remains under this r16 app path.'),
'fd-catima':('service-ability-jni',r'No implementation found.*nativeStopServiceAbility','Application init hits missing stop-service JNI before later widget NPE.'),
'fd-etar':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Main startup JNI failure.'),
'fd-fennec_fdroid':('jna-native-resource',r'Caused by:.*Native library.*libjnidispatch','JNA load failure, not a successful namespace repair.'),
'fd-fluffychat':('guest-thread-ready',r'Caused by:.*current thread is not READY','Flutter guest load entrance.'),
'fd-gallery':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Application bind failure; white UI itself does not identify a renderer fault.'),
'fd-im-vector-app':('process-cpu-jni',r'No implementation found.*Process.getElapsedCpuTime','Missing Process JNI occurs during bind before later Realm native error.'),
'fd-immich':('dex-verifier',r'Caused by:.*VerifyError','Startup provider VerifyError precedes subsequent guest loader exception.'),
'fd-kitchenowl':('guest-thread-ready',r'Caused by:.*current thread is not READY','Flutter load entrance.'),
'fd-libre':('guest-thread-ready',r'Caused by:.*current thread is not READY','Flutter load entrance.'),
'fd-libretube':('application-init-size',r'Caused by:.*IllegalArgumentException: size must be','Application creation fails first; tagsoup method error occurs later.'),
'fd-meet':('process-cpu-jni',r'No implementation found.*Process.getElapsedCpuTime','Missing Process JNI in bind precedes CommonEvent launch failure.'),
'fd-minetest':('documents-provider-permission',r'Caused by:.*SecurityException: Provider must be protected','MANAGE_DOCUMENTS check breaks provider initialization before CommonEvent launch.'),
'fd-client':('documents-provider-permission',r'Caused by:.*SecurityException: Provider must be protected','Provider initialization fails before accountManager null.'),
'burgerking':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Firebase provider init fails before later NitroMmkv loader error.'),
'wikipedia':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Current r16 main launch ULE; prior WikiSite/init forecast was not this first wall.'),
'termux':('documents-provider-permission',r'Caused by:.*SecurityException: Provider must be protected','TermuxDocumentsProvider fails before downstream CommonEvent failure.'),
'fd-netguard':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Current JNI failure replaces prior bionic import prediction.'),
'newpipe':('battery-service-null',r'Caused by:.*BatteryManager.getIntProperty','Battery service null after JobScheduler path advances.'),
'markor':('window-type-flags',r'InvalidDisplayException:.*window type','Main window add rejected.'),
'opencamera':('egl-camera-jni',r'No implementation found.*Camera.getNumberOfCameras','Actual camera JNI failure.'),
'fd-musicplayer':('media-session-token',r'Caused by:.*Failed to resolve SessionToken','Application bind fails before later bitmap colorspace error.'),
'fd-organicmaps':('app-native-loader',r'Caused by:.*dlopen_ns failed','liborganicmaps/libGLESv2 failure precedes DisplayManager null.'),
'fd-plus':('system-native-manifest',r'Caused by:.*system library is absent','Native system manifest miss during bind precedes DayNightHelper null.'),
'fd-reader':('vibrator-info-null',r'NullPointerException: Attempt to get length of null array','SystemVibrator.getInfo stack in Compose startup.'),
'fd-saber':('guest-thread-ready',r'Caused by:.*current thread is not READY','Flutter load entrance.'),
'fd-seal':('main-thread-stack',r'StackOverflowError: stack size 124KB','Installation succeeded; actual run reaches stack exhaustion.'),
'fd-shatteredpixeldungeon':('egl-camera-jni',r'No implementation found.*EGLImpl','EGL JNI initialization.'),
'fd-tasks':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','TaskProvider bind failure precedes workerFactory lateinit.'),
'fd-uhabits':('pendingintent-null',r'Caused by:.*getBroadcast','PendingIntentFactory widget-update bind failure.'),
'toutiao':('app-native-loader',r'Caused by:.*dlopen_ns failed','libflipped/libstdc++ error after installation; forecast install wall did not occur.'),
'mcdonalds':('app-native-loader',r'Caused by:.*dlopen_ns failed','librealmc missing dependency in startup provider precedes application DI failure.'),
'firefox':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Firebase provider bind ULE precedes JNA startup failure.'),
'vlc':('common-event-jni',r'No implementation found.*nativePublishCommonEvent','Main common-event publication fails.'),
'localsend':('guest-thread-ready',r'Caused by:.*current thread is not READY','Flutter entrance.'),
'ppsspp':('app-native-loader',r'dlopen_ns failed','App log reports libppsspp_jni/libGLESv2 loader failure.'),
'mindustry':('app-native-loader',r'Caused by:.*dlopen_ns failed','libarc/OpenSLES failure before ExceptionInInitializerError.'),
'x':('common-event-jni',r'No implementation found.*nativeSubscribeCommonEvent','Early initialization ULE before Datadog/object graph errors; no install wall.'),
}
def main():
 path=HERE/'observations-reviewed.json';obs=json.loads(path.read_text())
 for key,(wall,pattern,note) in RULED.items():
  r=obs[key]
  assert r['visual']=='not-lit',key
  doc=json.loads(gzip.decompress((HERE/'exceptions'/f'{key}.json.gz').read_bytes()))
  hit=next((x for x in doc['snippets'] if re.search(pattern,x['text'])),None)
  if not hit:raise ValueError('Missing adjudication evidence '+key)
  r['first_wall']=wall;r['wall_reviewer']='cx-bms, post-run target-PID exception-chain review'
  r['first_wall_evidence']=[{'path':doc['source'],'line':hit['line'],'source_sha256':doc['source_sha256'],'text':hit['text'],'context':hit['next_lines']},note]
  r['wall_confidence']='evidenced initialization blocker; causal repair unverified'
 # Wrong launcher is independently adjudicated by the outer reviewer, separate from native warnings.
 r=obs['anki'];r['first_wall']='launcher-entry';r['wall_reviewer']='outer(claude)'
 r['first_wall_evidence']=['outer-adjudication.json: fourth excerpt; Anki opened LeakCanary instead of app UI','Native librsdroid failure also exists; wrong launch target precedes app lifecycle selection.']
 for key,r in obs.items():
  if r['visual']=='not-lit' and r['first_wall']=='unknown':
   r['wall_reviewer']='cx-bms: abstain'
   r['first_wall_evidence']=['Obfuscated/null/unsupported exception or tolerated warning lacks sufficient causal attribution; do not convert blank/black UI into a known wall.']
 path.write_text(json.dumps(obs,ensure_ascii=False,indent=2)+'\n')
 print('classified non-lit first walls',sum(r['visual']=='not-lit' and r['first_wall']!='unknown' for r in obs.values()))
if __name__=='__main__':main()
