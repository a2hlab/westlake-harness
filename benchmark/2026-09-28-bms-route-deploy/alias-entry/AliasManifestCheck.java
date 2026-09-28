package adapter.activity;
import java.nio.file.*;
import java.util.*;
import android.content.pm.*;
import java.lang.reflect.*;
public final class AliasManifestCheck {
 static Object allocate(Class<?> type) throws Exception {
  Class<?> c=Class.forName("sun.misc.Unsafe");Field f=c.getDeclaredField("theUnsafe");f.setAccessible(true);
  return c.getMethod("allocateInstance",Class.class).invoke(f.get(null),type);
 }
 interface Checked {void run() throws Exception;}
 static void denied(Checked operation) throws Exception {
  try {operation.run();throw new AssertionError("identity mismatch accepted");}
  catch(SecurityException expected){}
 }
 public static void main(String[] args) throws Exception {
  int count=0,aliases=0;
  for(String line:Files.readAllLines(Paths.get(args[0]))) {
   String[] p=line.split("\t",-1);
   String actual=BinaryAndroidManifestOrientation.readAliasTarget(p[0],p[1],p[2]);
   String expected=p[3].isEmpty()?null:p[3];
   if(!Objects.equals(actual,expected))throw new AssertionError(p[1]+" expected="+expected+" actual="+actual);
   ApplicationInfo owner=(ApplicationInfo)allocate(ApplicationInfo.class);
   owner.uid=12345;owner.packageName=p[1];owner.sourceDir=p[0];
   ActivityInfo launch=(ActivityInfo)allocate(ActivityInfo.class);
   launch.applicationInfo=owner;launch.packageName=p[1];launch.name=p[2];
   launch.theme=71;launch.flags=42;launch.targetActivity="stale";
   LaunchActivityAliasProjection.apply(launch,12345);
   if(!Objects.equals(expected,launch.targetActivity)||launch.applicationInfo!=owner
       ||!p[2].equals(launch.name)||!p[1].equals(launch.packageName)||launch.theme!=71||launch.flags!=42)
    throw new AssertionError("projection changed launch identity or missed target");
   denied(()->LaunchActivityAliasProjection.apply(launch,54321));
   launch.packageName="other.package";
   denied(()->LaunchActivityAliasProjection.apply(launch,12345));
   if(actual!=null)aliases++;
   count++;
  }
  for(byte[] malformed:new byte[][]{new byte[0],new byte[]{3,0,8,0,99,0,0,0}}) {
   try {BinaryAndroidManifestOrientation.parseAliasTarget(malformed,"app.example","app.example.Main");throw new AssertionError("accepted malformed AXML");}
   catch(java.io.IOException expected){}
  }
  System.out.println("PASS "+count+" original manifest entries, "+aliases+" aliases; identity/field preservation and malformed AXML checks passed");
 }
}
