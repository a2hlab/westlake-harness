#!/usr/bin/env python3
"""Run donor C++ through JNI on a real JVM; Android boundaries are typed doubles."""
import json,os,shutil,subprocess,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
JDK=Path(os.environ.get('N3B_TEST_JDK','/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home'))
sources={
'android/os/IBinder.java': 'package android.os; public interface IBinder {}',
'android/app/Application.java':'package android.app; public class Application {}',
'android/app/ActivityThread.java':'''package android.app; public class ActivityThread {
 public static Application app; public static boolean fail;
 public static Application currentApplication() { if(fail)throw new IllegalStateException("app test"); return app; }}''',
'android/os/ServiceManager.java':'''package android.os; import java.util.*;
 public class ServiceManager {
 public static Map<String,IBinder> sCache=new HashMap<>();
 public static String fault="";
 public static IBinder getService(String name) {
 if(fault.equals("lookup-throws"))throw new IllegalStateException("lookup test");
 if(fault.equals("lookup-wrong"))return new IBinder(){};
 return sCache.get(name); }
 public static class BrokenMap extends HashMap<String,IBinder>{
 public IBinder put(String k,IBinder v){throw new IllegalStateException("put test");}}
 }''',
'android/webkit/WebViewFactory.java':'''package android.webkit; public class WebViewFactory {
 public static final String WEBVIEW_UPDATE_SERVICE_NAME=new String("webviewupdate");
 public static Boolean sWebViewSupported;
 public static Object sProviderInstance=new Object(); }''',
'adapter/core/WebViewUpdateServiceAdapter.java':'''package adapter.core;
 public class WebViewUpdateServiceAdapter implements android.os.IBinder {
 public static boolean available=false, fail=false, missingInstance=false;
 public static final WebViewUpdateServiceAdapter INSTANCE=new WebViewUpdateServiceAdapter();
 public static boolean isAvailable(){if(fail)throw new IllegalStateException("availability test");return available;}
 public static WebViewUpdateServiceAdapter getInstance(){return missingInstance?null:INSTANCE;}}
''',
'adapter/core/WestlakeWebViewInstall.java':'''package adapter.core;
 import android.app.*;import android.os.*;import android.webkit.*;
 public class WestlakeWebViewInstall {
 public static native boolean nativePrime();
 public static native boolean nativePublishAfterBind();
 static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
 public static void main(String[] args) throws Exception {
 System.load(args[0]); String mode=args[1]; Object prior=WebViewFactory.sProviderInstance;
 if(mode.equals("missing-class")){check(!nativePrime(),mode);System.out.println("PASS "+mode);return;}
 WebViewUpdateServiceAdapter.available=!mode.equals("absent");
 if(mode.equals("absent")){
 check(!nativePrime()&&!nativePublishAfterBind(),"absent must fail");
 check(WebViewFactory.sWebViewSupported==null && ServiceManager.sCache.isEmpty(),"absent mutation");
 }else if(mode.equals("available-throws")){
 WebViewUpdateServiceAdapter.fail=true;check(!nativePrime(),mode);
 }else if(mode.equals("null-provider")){
 WebViewUpdateServiceAdapter.missingInstance=true;check(!nativePrime(),mode);
 }else if(mode.equals("pending-app")){
 check(nativePrime(),"prime"); check(!nativePublishAfterBind(),"pending publish");
 check(Boolean.FALSE.equals(WebViewFactory.sWebViewSupported),"early true");
 }else if(mode.equals("app-throws")){
 ActivityThread.fail=true;check(!nativePublishAfterBind(),mode);
 }else if(mode.startsWith("lookup-")){
 ActivityThread.app=new Application();ServiceManager.fault=mode;
 check(!nativePublishAfterBind(),"bad public readback accepted");
 }else if(mode.equals("put-throws")){
 ServiceManager.sCache=new ServiceManager.BrokenMap();check(!nativePrime(),mode);
 }else{
 check(nativePrime(),"prime"); check(Boolean.FALSE.equals(WebViewFactory.sWebViewSupported),"pre-bind false");
 ActivityThread.app=new Application();check(nativePublishAfterBind(),"publish");
 check(Boolean.TRUE.equals(WebViewFactory.sWebViewSupported),"published true");
 check(ServiceManager.getService(WebViewFactory.WEBVIEW_UPDATE_SERVICE_NAME)==WebViewUpdateServiceAdapter.INSTANCE,"binder identity");
 if(mode.equals("late-prime")){
 check(nativePrime(),"late prime");check(Boolean.TRUE.equals(WebViewFactory.sWebViewSupported),"late false");
 }else if(mode.equals("threads")){
 java.util.List<Throwable> failures=java.util.Collections.synchronizedList(new java.util.ArrayList<Throwable>());
 Thread[] threads=new Thread[8];
 for(int i=0;i<threads.length;i++){threads[i]=new Thread(()->{try{for(int n=0;n<30;n++){check(nativePrime(),"concurrent prime");check(nativePublishAfterBind(),"concurrent publish");}}catch(Throwable t){failures.add(t);}});threads[i].start();}
 for(Thread t:threads)t.join();check(failures.isEmpty(),"threads "+failures);check(Boolean.TRUE.equals(WebViewFactory.sWebViewSupported),"final true");
 }
 }
 check(WebViewFactory.sProviderInstance==prior,"provider instance overwritten");
 System.out.println("PASS "+mode);
 }}'''}
cases=['absent','available-throws','null-provider','pending-app','app-throws','lookup-wrong','lookup-throws','put-throws','happy','late-prime','threads','missing-class']
results=[]
with tempfile.TemporaryDirectory(prefix='n3b-jni-') as tmp:
 t=Path(tmp);classes=t/'classes';classes.mkdir()
 for name,src in sources.items():
  f=t/'src'/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(src)
 subprocess.run([str(JDK/'bin/javac'),'-d',str(classes),*map(str,(t/'src').rglob('*.java'))],check=True)
 lib=t/'publication.dylib'
 subprocess.run(['/usr/bin/clang++','-std=c++17','-dynamiclib','-pthread','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(P/'src/webview_publication.cpp'),'-o',str(lib)],check=True)
 for case in cases:
  if case=='missing-class':(classes/'adapter/core/WebViewUpdateServiceAdapter.class').unlink()
  x=subprocess.run([str(JDK/'bin/java'),'-Xcheck:jni','-cp',str(classes),'adapter.core.WestlakeWebViewInstall',str(lib),case],capture_output=True,text=True,timeout=45)
  (P/f'host-{case}.log').write_text(x.stdout+x.stderr)
  assert x.returncode==0,(case,x.stdout,x.stderr)
  assert 'WARNING in native method' not in x.stdout+x.stderr,(case,'JNI misuse')
  results.append({'case':case,'returncode':x.returncode,'passed':True,'log':f'host-{case}.log'})
  print('PASS',case)
(P/'host-tests.json').write_text(json.dumps({'boundary':'real JVM + compiled JNI; Android API classes are host test doubles, not ART/device evidence','jdk':str(JDK),'cases':results},indent=2)+'\n')
