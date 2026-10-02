#!/usr/bin/env python3
"""Upstream path B (WlSettingsStub + WlSettingsProvider) on a host JVM against AOSP 14-shaped stand-ins; plus the U12
build identity where the jar is present.

The stand-ins declare only what the copied code reaches: Settings$Global/$Secure/$System each with a static
NameValueCache sNameValueCache whose final mProviderHolder holds a private IContentProvider mContentProvider
(AOSP 14 Settings.java:3059/:3065/:3103, caches :3754 System, :6261 Secure, :16755 Global), IContentProvider.call(AttributionSource, authority, method,
arg, extras) and a Bundle with putString/getString. NameValueCache.get() replays AOSP 14 getStringForUser's fast path
(:3219ff.): cp.call(attr, "settings", mCallGetCommand, name, args), value = b.getString("value"), and falls back to
query only when the Bundle is null. Known answers:
  - all 3 holders injected (the upstream log line), GET_secure/android_id -> 16 hex digits, the same on a second read,
    persisted to <dataDir>/no_backup/westlake-android-id and read back by a fresh JVM;
  - any other key (GET_global/force_resizable_activities, GET_secure/advertising_id) -> null without reaching query,
    i.e. the same null as U9's failing bridge, minus the "Can't get key" fallback.
"""
import hashlib
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
JAR = HERE / 'build/oh-adapter-runtime-u12.jar'
U12_SHA = '3bca82c5ffba6c048cbd020a626c205ebe36c687712419e6b7146aee7075d378'

CACHE = '''\
    static final android.provider.NameValueCache sNameValueCache = new android.provider.NameValueCache("GET_{t}");
    public static String getString(String name) {{ return sNameValueCache.get(name); }}'''
STUBS = {
    'android/os/Bundle.java': textwrap.dedent('''\
        package android.os;
        public class Bundle {
            private final java.util.HashMap<String, Object> m = new java.util.HashMap<>();
            public void putString(String k, String v) { m.put(k, v); }
            public void putSerializable(String k, java.io.Serializable v) { m.put(k, v); }
            public String getString(String k) { Object v = m.get(k); return v instanceof String ? (String) v : null; }
        }'''),
    'android/content/AttributionSource.java': 'package android.content; public final class AttributionSource {}',
    'android/content/ContentValues.java': 'package android.content; public final class ContentValues {}',
    'android/net/Uri.java': 'package android.net; public abstract class Uri {}',
    'android/database/Cursor.java': 'package android.database; public interface Cursor {}',
    'android/database/MatrixCursor.java': textwrap.dedent('''\
        package android.database;
        public class MatrixCursor implements Cursor { public MatrixCursor(String[] columns) {} }'''),
    'android/content/IContentProvider.java': textwrap.dedent('''\
        package android.content;
        public interface IContentProvider {
            android.os.Bundle call(AttributionSource attributionSource, String authority, String method, String arg,
                    android.os.Bundle extras);
            android.database.Cursor query(AttributionSource attributionSource, android.net.Uri url, String[] projection,
                    android.os.Bundle queryArgs, Object cancellationSignal);
        }'''),
    'android/content/ContentProvider.java': textwrap.dedent('''\
        package android.content;
        public abstract class ContentProvider {
            public abstract boolean onCreate();
            public android.os.Bundle call(String method, String arg, android.os.Bundle extras) { return null; }
            public abstract android.database.Cursor query(android.net.Uri uri, String[] projection, String selection,
                    String[] selectionArgs, String sortOrder);
            public abstract String getType(android.net.Uri uri);
            public abstract android.net.Uri insert(android.net.Uri uri, ContentValues values);
            public abstract int delete(android.net.Uri uri, String selection, String[] selectionArgs);
            public abstract int update(android.net.Uri uri, ContentValues values, String selection, String[] selectionArgs);
        }'''),
    'android/app/Application.java': textwrap.dedent('''\
        package android.app;
        public class Application {
            public java.io.File getDataDir() { return new java.io.File(System.getProperty("test.dataDir")); }
        }'''),
    'android/app/ActivityThread.java': textwrap.dedent('''\
        package android.app;
        public final class ActivityThread {
            public static Application currentApplication() { return new Application(); }
        }'''),
    'android/provider/NameValueCache.java': textwrap.dedent('''\
        package android.provider;
        public final class NameValueCache {
            static final class ContentProviderHolder { private android.content.IContentProvider mContentProvider; }
            private final ContentProviderHolder mProviderHolder = new ContentProviderHolder();
            private final String mCallGetCommand;
            public static int sQueries;
            public NameValueCache(String get) { mCallGetCommand = get; }
            public String get(String name) {
                android.content.IContentProvider cp = mProviderHolder.mContentProvider;
                if (cp == null) return "NO-PROVIDER";
                android.os.Bundle b = cp.call(new android.content.AttributionSource(), "settings", mCallGetCommand,
                        name, new android.os.Bundle());
                if (b != null) return b.getString("value");
                sQueries++;
                return cp.query(null, null, null, null, null) == null ? null : "QUERY";
            }
        }'''),
    'android/provider/Settings.java': textwrap.dedent(f'''\
        package android.provider;
        public final class Settings {{
            public static final class Global {{
        {CACHE.format(t="global")}
            }}
            public static final class Secure {{
        {CACHE.format(t="secure")}
            }}
            public static final class System {{
        {CACHE.format(t="system")}
            }}
        }}'''),
    'Harness.java': textwrap.dedent('''\
        import android.provider.Settings;
        public class Harness {
            public static void main(String[] a) {
                adapter.activity.WlSettingsStub.installSettingsContentProviderStub();
                String id = Settings.Secure.getString("android_id");
                System.out.println("ANDROID_ID " + id);
                System.out.println("AGAIN " + id.equals(Settings.Secure.getString("android_id")));
                System.out.println("GLOBAL " + Settings.Global.getString("force_resizable_activities"));
                System.out.println("ADID " + Settings.Secure.getString("advertising_id"));
                System.out.println("SYSTEM " + Settings.System.getString("time_12_24"));
                System.out.println("QUERIES " + android.provider.NameValueCache.sQueries);
            }
        }'''),
}


class HostJvm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        src = cls.tmp / 'src'
        for rel, text in STUBS.items():
            (src / rel).parent.mkdir(parents=True, exist_ok=True)
            (src / rel).write_text(text + '\n')
        files = [str(p) for p in src.rglob('*.java')]
        files += [str(HERE / 'src/adapter/activity/WlSettingsProvider.java'),
                  str(HERE / 'src/adapter/activity/WlSettingsStub.java')]
        (cls.tmp / 'out').mkdir()   # javac 1.8 (the land gate's PATH) does not create -d
        (cls.tmp / 'data').mkdir()
        subprocess.run([shutil.which('javac'), '-nowarn', '-d', str(cls.tmp / 'out'), *files], check=True,
                       capture_output=True)
        cls.runs = [subprocess.run(['java', f'-Dtest.dataDir={cls.tmp / "data"}', '-cp', str(cls.tmp / 'out'), 'Harness'],
                                   capture_output=True, text=True) for _ in range(2)]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_three_holders_injected(self):
        err = self.runs[0].stderr
        for c in ('Global', 'Secure', 'System'):
            self.assertIn(f'injected mContentProvider into android.provider.Settings${c} holder', err)
        self.assertIn('[SettingsCache] IContentProvider Proxy installed in 3 holders', err)

    def test_android_id_is_stable_and_persisted(self):
        ids = [re.search(r'ANDROID_ID (\S+)', r.stdout).group(1) for r in self.runs]
        self.assertRegex(ids[0], r'^[0-9a-f]{16}$')
        self.assertIn('AGAIN true', self.runs[0].stdout)
        self.assertEqual(ids[0], ids[1], 'a fresh process must read the persisted id back')
        saved = (self.tmp / 'data/no_backup/westlake-android-id').read_text().strip()
        self.assertEqual(saved, ids[0])

    def test_other_keys_stay_unset_without_query_fallback(self):
        out = self.runs[0].stdout
        self.assertIn('GLOBAL null', out)
        self.assertIn('ADID null', out)
        self.assertIn('SYSTEM null', out)
        self.assertIn('QUERIES 0', out)


@unittest.skipUnless(JAR.exists(), 'U12 jar not built here (build_u12.py)')
class Build(unittest.TestCase):
    def test_u12_jar_is_the_recorded_build(self):
        self.assertEqual(hashlib.sha256(JAR.read_bytes()).hexdigest(), U12_SHA)


if __name__ == '__main__':
    unittest.main()
