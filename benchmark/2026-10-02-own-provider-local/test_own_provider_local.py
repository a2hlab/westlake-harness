#!/usr/bin/env python3
"""OwnProviderLocal on a host JVM, against minimal android stand-ins, with toutiao's real provider rows; plus the
U11j build identity where the jar is present.

The stand-ins declare only what OwnProviderLocal reaches by reflection (ActivityManager.IActivityManagerSingleton,
android.util.Singleton.mInstance, ActivityThread.currentActivityThread()/mBoundApplication, AppBindData.providers/
processName, ContentProviderHolder(ProviderInfo) with info/provider/mLocal/noReleaseNeeded -- the AOSP 14 names
checked in ActivityThread.java:873/:2530/:6718 and ContentProviderHolder.java:35-48). Known answers (toutiao a1112a0c
manifest): PPMP (main process) -> local holder, mLocal true, provider null; AccountSyncProvider (:push) and another
package's authority -> the delegate's answer; a second install() does not stack a second proxy.
"""
import hashlib
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
JAR = HERE / 'build/oh-adapter-runtime-u11j.jar'
U11J_SHA = '96fd4eee07906bf597754536158a06b0a8fd77106202927888440818704a9a3b'

STUBS = {
    'android/app/IApplicationThread.java': 'package android.app; public interface IApplicationThread {}',
    'android/app/IActivityManager.java': textwrap.dedent('''\
        package android.app;
        public interface IActivityManager {
            ContentProviderHolder getContentProvider(IApplicationThread caller, String callingPackage, String name,
                    int userId, boolean stable);
            String getTagForIntentSender(Object sender, String prefix);
        }'''),
    'android/util/Singleton.java': textwrap.dedent('''\
        package android.util;
        public abstract class Singleton<T> {
            private T mInstance;
            protected abstract T create();
            public final T get() { synchronized (this) { if (mInstance == null) mInstance = create(); return mInstance; } }
        }'''),
    'android/app/ActivityManager.java': textwrap.dedent('''\
        package android.app;
        public class ActivityManager {
            public static IActivityManager sReal;
            private static final android.util.Singleton<IActivityManager> IActivityManagerSingleton =
                new android.util.Singleton<IActivityManager>() { protected IActivityManager create() { return sReal; } };
            public static IActivityManager getService() { return IActivityManagerSingleton.get(); }
        }'''),
    'android/content/pm/ProviderInfo.java': textwrap.dedent('''\
        package android.content.pm;
        public class ProviderInfo {
            public String name, packageName, processName, authority;
            public boolean multiprocess;
        }'''),
    'android/app/ContentProviderHolder.java': textwrap.dedent('''\
        package android.app;
        public class ContentProviderHolder {
            public final android.content.pm.ProviderInfo info;
            public Object provider;
            public boolean noReleaseNeeded;
            public boolean mLocal;
            public ContentProviderHolder(android.content.pm.ProviderInfo info) { this.info = info; }
        }'''),
    'android/app/ActivityThread.java': textwrap.dedent('''\
        package android.app;
        public final class ActivityThread {
            static final class AppBindData {
                String processName;
                java.util.List<android.content.pm.ProviderInfo> providers;
            }
            static ActivityThread sThread;
            AppBindData mBoundApplication;
            public static ActivityThread currentActivityThread() { return sThread; }
            public static void bind(String process, java.util.List<android.content.pm.ProviderInfo> p) {
                sThread = new ActivityThread();
                sThread.mBoundApplication = new AppBindData();
                sThread.mBoundApplication.processName = process;
                sThread.mBoundApplication.providers = p;
            }
        }'''),
    'Harness.java': textwrap.dedent('''\
        import android.app.*;
        import android.content.pm.ProviderInfo;
        import java.util.*;
        public class Harness {
            static ProviderInfo p(String name, String auth, String proc) {
                ProviderInfo i = new ProviderInfo();
                i.name = name; i.authority = auth; i.processName = proc; i.packageName = "com.ss.android.article.news";
                return i;
            }
            public static void main(String[] a) {
                final ContentProviderHolder bridge = new ContentProviderHolder(new ProviderInfo());
                bridge.provider = "OH-BRIDGE";
                ActivityManager.sReal = new IActivityManager() {
                    public ContentProviderHolder getContentProvider(IApplicationThread c, String pkg, String n, int u, boolean s) { return bridge; }
                    public String getTagForIntentSender(Object o, String p) { return "delegated"; }
                };
                String P = "com.ss.android.article.news";
                ActivityThread.bind(P, Arrays.asList(
                    p("com.bytedance.mira.pm.PluginPackageManagerProvider", P + ".pm.PPMP", P),
                    p("com.bytedance.sdk.account.sync.AccountSyncProvider", P + ".AccountSyncProvider", P + ":push"),
                    p("com.tencent.tinker.lib.stub.p0.StubContentProvider", "x;" + P + ".stub.p0.STUB_AUTHORITY", null)));
                adapter.activity.OwnProviderLocal.install();
                adapter.activity.OwnProviderLocal.install();
                IActivityManager am = ActivityManager.getService();
                ContentProviderHolder own = am.getContentProvider(null, P, P + ".pm.PPMP", 0, true);
                System.out.println("PPMP local=" + own.mLocal + " provider=" + own.provider + " noRelease=" + own.noReleaseNeeded + " name=" + own.info.name);
                ContentProviderHolder split = am.getContentProvider(null, P, P + ".stub.p0.STUB_AUTHORITY", 0, true);
                System.out.println("STUB local=" + split.mLocal + " name=" + split.info.name);
                System.out.println("PUSH " + (am.getContentProvider(null, P, P + ".AccountSyncProvider", 0, true) == bridge ? "delegate" : "local"));
                System.out.println("OTHER " + (am.getContentProvider(null, P, "com.other.app.provider", 0, true) == bridge ? "delegate" : "local"));
                System.out.println("TAG " + am.getTagForIntentSender(null, null));
                Object h = java.lang.reflect.Proxy.getInvocationHandler(am);
                System.out.println("HANDLER " + h.getClass().getSimpleName());
            }
        }'''),
}


class HostJvm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        src = Path(cls.tmp, 'src')
        for rel, text in STUBS.items():
            (src / rel).parent.mkdir(parents=True, exist_ok=True)
            (src / rel).write_text(text + '\n')
        files = [str(p) for p in src.rglob('*.java')] + [str(HERE / 'src/OwnProviderLocal.java')]
        javac = shutil.which('javac')
        Path(cls.tmp, 'out').mkdir()   # javac 1.8 (the land gate's PATH) does not create -d
        subprocess.run([javac, '-nowarn', '-d', str(Path(cls.tmp, 'out')), *files], check=True, capture_output=True)
        r = subprocess.run(['java', '-cp', str(Path(cls.tmp, 'out')), 'Harness'], capture_output=True, text=True)
        cls.out, cls.err = r.stdout, r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_own_main_process_provider_gets_a_local_holder(self):
        self.assertIn('PPMP local=true provider=null noRelease=true '
                      'name=com.bytedance.mira.pm.PluginPackageManagerProvider', self.out)
        self.assertIn('STUB local=true name=com.tencent.tinker.lib.stub.p0.StubContentProvider', self.out)

    def test_other_process_and_other_package_are_delegated(self):
        self.assertIn('PUSH delegate', self.out)
        self.assertIn('OTHER delegate', self.out)
        self.assertIn('TAG delegated', self.out)

    def test_install_is_idempotent_and_logs(self):
        self.assertEqual(self.err.count('[OWN-PROV-LOCAL] installed over'), 1, self.err)
        self.assertIn('HANDLER OwnProviderLocal', self.out)
        self.assertIn('[OWN-PROV-LOCAL] com.ss.android.article.news.pm.PPMP -> local holder', self.err)


@unittest.skipUnless(JAR.exists(), 'U11j jar not built here (build_u11j.py)')
class Build(unittest.TestCase):
    def test_u11j_jar_is_the_recorded_build(self):
        self.assertEqual(hashlib.sha256(JAR.read_bytes()).hexdigest(), U11J_SHA)


if __name__ == '__main__':
    unittest.main()
