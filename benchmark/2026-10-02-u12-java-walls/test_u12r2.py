#!/usr/bin/env python3
"""U12 r2 Java-layer fixes on a host JVM against minimal stand-ins, plus the build identity of both jars.

- GcmDefaultNonce: installed first; parameterless AES/GCM encrypt gets a 12-byte IV; Tink-style decrypt (first 12
  bytes as IV) round-trips; explicit parameters pass through unchanged; a second install() adds nothing.
- TelephonyServiceNames: registers TelephonyManager -> "phone" where the fetcher exists and the class has no name;
  skips a name without a fetcher; never overwrites an existing entry.
- ProviderAuthorityRefs: "@2131755008" is replaced by the projected authority of the same provider class; literal
  authorities and unprojected references are left alone.
- TelephonyFrameworkInitializer donor: getTelephonyServiceManager() is non-null and stable.
"""
import hashlib
import shutil
import sys
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-own-provider-local'))
from build_u11j import pinned_javac  # noqa: E402  (JDK >= 11: JAVA_HOME or mise temurin-21, as the builds)
RUNTIME_SHA = '0482c9b13fbc6ab5bce3902807eb7972736463b772773fde276cae679ce9bd4f'
STUBS_SHA = '00b304678a0d08651513e3cbc471a3ba2b04b4a7836c6d0eca57ffbc824b479e'

STUBS = {
    'android/app/SystemServiceRegistry.java': textwrap.dedent('''\
        package android.app;
        public final class SystemServiceRegistry {
            private static final java.util.Map<Class<?>, String> SYSTEM_SERVICE_NAMES = new java.util.HashMap<>();
            private static final java.util.Map<String, Object> SYSTEM_SERVICE_FETCHERS = new java.util.HashMap<>();
            public static String name(Class<?> c) { return SYSTEM_SERVICE_NAMES.get(c); }
            public static void fetcher(String n) { SYSTEM_SERVICE_FETCHERS.put(n, new Object()); }
            public static void name(Class<?> c, String n) { SYSTEM_SERVICE_NAMES.put(c, n); }
        }'''),
    'android/telephony/TelephonyManager.java': 'package android.telephony; public class TelephonyManager {}',
    'android/telephony/SubscriptionManager.java': 'package android.telephony; public class SubscriptionManager {}',
    'android/content/pm/ProviderInfo.java': textwrap.dedent('''\
        package android.content.pm;
        public class ProviderInfo {
            public String name, authority;
            public ProviderInfo(String name, String authority) { this.name = name; this.authority = authority; }
        }'''),
    'adapter/activity/SelfComponentFallback.java': textwrap.dedent('''\
        package adapter.activity;
        final class SelfComponentFallback {
            static android.content.pm.ProviderInfo manifestProvider(String className, long flags) {
                if (className.endsWith("MyContentProvider"))
                    return new android.content.pm.ProviderInfo(className, "com.nononsenseapps.notepad.MyContentAuthority");
                return null;
            }
        }'''),
    'android/os/TelephonyServiceManager.java': 'package android.os; public class TelephonyServiceManager {}',
    'Harness.java': textwrap.dedent('''\
        import android.content.pm.ProviderInfo;
        import android.telephony.*;
        import java.util.*;
        import javax.crypto.*;
        import javax.crypto.spec.*;
        public class Harness {
            static class AppBindData { List<ProviderInfo> providers; }
            public static void main(String[] a) throws Exception {
                // GCM
                SecretKey k = KeyGenerator.getInstance("AES").generateKey();
                adapter.core.GcmDefaultNonce.install(); adapter.core.GcmDefaultNonce.install();
                Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
                c.init(Cipher.ENCRYPT_MODE, k);
                byte[] iv = c.getIV(), ct = c.doFinal("hello".getBytes());
                byte[] blob = new byte[iv.length + ct.length];
                System.arraycopy(iv, 0, blob, 0, iv.length); System.arraycopy(ct, 0, blob, iv.length, ct.length);
                Cipher d = Cipher.getInstance("AES/GCM/NoPadding");
                d.init(Cipher.DECRYPT_MODE, k, new GCMParameterSpec(128, blob, 0, 12));
                System.out.println("GCM provider=" + c.getProvider().getName() + " iv=" + iv.length
                    + " roundtrip=" + new String(d.doFinal(blob, 12, blob.length - 12)));
                Cipher e = Cipher.getInstance("AES/GCM/NoPadding");
                e.init(Cipher.ENCRYPT_MODE, k, new GCMParameterSpec(128, new byte[16]));
                System.out.println("GCM explicit iv=" + e.getIV().length + " providers=" +
                    Arrays.stream(java.security.Security.getProviders()).filter(p -> p.getName().equals("WestlakeGcmNonce")).count());
                // telephony names
                android.app.SystemServiceRegistry.fetcher("phone");
                android.app.SystemServiceRegistry.name(SubscriptionManager.class, "existing");
                adapter.activity.TelephonyServiceNames.install();
                System.out.println("NAMES tm=" + android.app.SystemServiceRegistry.name(TelephonyManager.class)
                    + " sm=" + android.app.SystemServiceRegistry.name(SubscriptionManager.class));
                // authority refs
                AppBindData b = new AppBindData();
                b.providers = Arrays.asList(
                    new ProviderInfo("com.nononsenseapps.notepad.database.MyContentProvider", "@2131755008"),
                    new ProviderInfo("x.LiteralProvider", "com.example.literal"),
                    new ProviderInfo("x.UnknownProvider", "@0x7f130784"));
                adapter.activity.ProviderAuthorityRefs.resolve(b);
                for (ProviderInfo p : b.providers) System.out.println("AUTH " + p.name + " " + p.authority);
                // donor
                Object m1 = android.telephony.TelephonyFrameworkInitializer.getTelephonyServiceManager();
                Object m2 = android.telephony.TelephonyFrameworkInitializer.getTelephonyServiceManager();
                System.out.println("TSM nonnull=" + (m1 != null) + " same=" + (m1 == m2));
            }
        }'''),
}


class HostJvm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        for rel, text in STUBS.items():
            (cls.tmp / 'src' / rel).parent.mkdir(parents=True, exist_ok=True)
            (cls.tmp / 'src' / rel).write_text(text + '\n')
        files = [str(p) for p in (cls.tmp / 'src').rglob('*.java')]
        files += [str(HERE / 'src-runtime/adapter/core/GcmDefaultNonce.java'),
                  str(HERE / 'src-runtime/adapter/activity/TelephonyServiceNames.java'),
                  str(HERE / 'src-runtime/adapter/activity/ProviderAuthorityRefs.java'),
                  str(HERE / 'stubs/donor/android/telephony/TelephonyFrameworkInitializer.java')]
        (cls.tmp / 'out').mkdir()  # javac 1.8 (the land gate's PATH) does not create -d
        # JDK >= 11 on purpose: JDK 8's protected Cipher(CipherSpi, Provider, String) throws NullPointerException
        # for untrusted callers (JceSecurityManager), a desktop-JCE rule Android's libcore does not have.
        javac = pinned_javac()
        subprocess.run([javac, '-nowarn', '-d', str(cls.tmp / 'out'), *files], check=True, capture_output=True)
        r = subprocess.run([str(Path(javac).parent / 'java'), '-cp', str(cls.tmp / 'out'), 'Harness'],
                           capture_output=True, text=True)
        cls.out, cls.err = r.stdout, r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_gcm_default_nonce_is_12_and_round_trips(self):
        self.assertIn('GCM provider=WestlakeGcmNonce iv=12 roundtrip=hello', self.out, self.err)
        self.assertIn('GCM explicit iv=16 providers=1', self.out)

    def test_telephony_class_names(self):
        self.assertIn('NAMES tm=phone sm=existing', self.out, self.err)
        self.assertIn('telephony_subscription_service class->name already existing', self.err)

    def test_provider_authority_references(self):
        self.assertIn('AUTH com.nononsenseapps.notepad.database.MyContentProvider '
                      'com.nononsenseapps.notepad.MyContentAuthority', self.out, self.err)
        self.assertIn('AUTH x.LiteralProvider com.example.literal', self.out)
        self.assertIn('AUTH x.UnknownProvider @0x7f130784', self.out)
        self.assertIn('[B8-PROV-AUTH] resolved 1 resource-reference authority', self.err)

    def test_telephony_service_manager_getter(self):
        self.assertIn('TSM nonnull=true same=true', self.out, self.err)


class Build(unittest.TestCase):
    @unittest.skipUnless((HERE / 'build/oh-adapter-runtime-u12r2.jar').exists(), 'runtime jar not built here')
    def test_runtime_jar(self):
        self.assertEqual(hashlib.sha256((HERE / 'build/oh-adapter-runtime-u12r2.jar').read_bytes()).hexdigest(),
                         RUNTIME_SHA)

    @unittest.skipUnless((HERE / 'build/adapter-mainline-stubs-u12r2.jar').exists(), 'stubs jar not built here')
    def test_stubs_jar(self):
        self.assertEqual(hashlib.sha256((HERE / 'build/adapter-mainline-stubs-u12r2.jar').read_bytes()).hexdigest(),
                         STUBS_SHA)


if __name__ == '__main__':
    unittest.main()
