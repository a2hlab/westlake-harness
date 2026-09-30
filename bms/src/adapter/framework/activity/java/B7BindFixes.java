package adapter.activity;

import android.content.pm.ApplicationInfo;

import java.io.File;

/**
 * B7 (2026-09-29): two bind-time repairs applied to the resolved ApplicationInfo
 * before ActivityThread.handleBindApplication runs.
 *
 * 1. "user" service. ContextImpl.getSharedPreferences(File,int) consults
 *    getSystemService(UserManager.class) for credential-protected contexts
 *    (targetSdk >= 26, dataDir == credentialProtectedDataDir). This child has no
 *    system_server "user" service, so the fetcher returns null and the query NPEs
 *    (catima in Activity.attachBaseContext, fennec in Application.attachBaseContext).
 *    The existing UserManagerProjectionProxy answers only isUserUnlockingOrUnlocked.
 *
 * 2. nativeLibraryDir. For an APK without native code BMS reports no cpuAbi and no
 *    nativeLibraryPath, so PackageInfoBuilder falls back to
 *    /system/app/<pkg>/lib/armeabi-v7a, which does not exist. The app-native-loader
 *    refuses a namespace whose search path is not an existing directory, so
 *    LoadedApk.getClassLoader throws UnsatisfiedLinkError during bind (opencamera).
 *    Point it at the package's own installed code directory instead: it exists and
 *    holds no libraries, which is exactly "this app has no native code".
 */
public final class B7BindFixes {
    private B7BindFixes() {}

    public static void apply(ApplicationInfo ai) {
        // r17o: rewrite sun.security.jca.Providers.jarVerificationProviders[0] to the boot-visible BC
        // provider so getSunProvider() (JAR signature verification + SecureRandom) stops throwing
        // "Sun provider not found" on route-A (no Conscrypt). Runs first, before any app class that
        // verifies a signed JAR (droidify MainActivity.onCreate, amaze AppConfig.<clinit>, newpipe,
        // catima, antennapod). Process-global + idempotent, so doing it per-bind is harmless.
        JarVerificationProviderFix.apply();
        // r17c: load cx-t0's TLS + HTML boundary libraries (fixed child paths) from THIS class's loader
        // -- the runtime PathClassLoader. native-loader-oh only allows the legacy four soname for the
        // boot/null loader and rejects these new names, so the caller must be a runtime-JAR class. TLS
        // first, then HTML; each ships a JNI_OnLoad that registers WestlakeSSLSocket's natives /
        // rewrites Html.fromHtml to call HtmlCompatFallback. A missing lib must not fail the bind.
        loadWestlakeNativeLibs();
        // r17h (#first-frame): wrap IWindowSession as EARLY as possible -- before any Activity's
        // ViewRootImpl caches it -- so its first relayout goes through the proxy (reverse-push). This
        // is idempotent with the later install() from resolveActivityTheme; whichever wins is fine.
        try { WindowSessionProxy.install(); } catch (Throwable t) { System.err.println("[B8-WSP] early " + t); }
        try {
            UserManagerProjectionProxy.install();
        } catch (Throwable t) {
            System.err.println("[B7] user binder not installed: " + t);
        }
        try {
            fixNativeLibraryDir(ai);
        } catch (Throwable t) {
            System.err.println("[B7] nativeLibraryDir check failed: " + t);
        }
        // r17s (dlopen_ns experiment): append /system/lib64 + /system/android/lib64 to the app
        // classloader's native search path so unciv/mindustry/nextcloud can (maybe) reach their
        // missing system deps. Discriminates JAR-fixable vs native-owned; fail-safe, log-only.
        try {
            extendAppNativeLibrarySearchPath();
        } catch (Throwable t) {
            System.err.println("[B8-DLEXP] not run: " + t);
        }
        // B8 (#65): record the bound self ApplicationInfo for the self-package
        // getProviderInfo/resolveContentProvider fallback (SelfComponentFallback).
        SelfComponentFallback.bind(ai);
        // B8 (#65) items 6/7: appops/uimode/locale/account/alarm answered in process.
        B8BindExtras.installServiceStubs();
        // B8 (#70/INVENTORY 19): Flutter Impeller fallback -- add EnableImpeller=false to the app's
        // metaData Bundle so a Flutter engine that honours the opt-out uses the Skia GLES path.
        applyImpellerFallback(ai);
        // B8 (#82/r15): tolerant uncaught-exception handler. AOSP RuntimeInit's KillApplicationHandler
        // calls System.exit on ANY uncaught exception, so a crash on a background worker takes the
        // whole app down (many "exit 1"). Westlake keeps only the main thread fatal.
        installTolerantUncaughtHandler();
        // B8 (#82/r15): runtime-JAR proxies over the BCP IWindowSession (addToDisplay flag-allow +
        // relayout CLAMP48) and IActivityManager (in-app bindService). Same reflect.Proxy pattern as
        // PackageManagerProjectionProxy; each install is idempotent and defensive.
        try { WindowSessionProxy.install(); } catch (Throwable t) { System.err.println("[B8-WSP] " + t); }
        try { ActivityManagerBindProxy.install(); } catch (Throwable t) { System.err.println("[B8-AMB] " + t); }
        // r16 (#90): cc-wiki's OnlineConnectivityManager -- replaces the SystemServiceRegistry
        // connectivity (+ jobscheduler) fetchers with an online-reporting ConnectivityManager
        // subclass (Wikipedia onGoOffline, WorkManager). Called reflectively so this class does not
        // need the Westlake-sourced OnlineConnectivityManager on its compile classpath.
        try {
            Class.forName("adapter.activity.OnlineConnectivityManager").getMethod("install").invoke(null);
        } catch (Throwable t) {
            System.err.println("[B8-OCM] not installed: " + t);
        }
        // r17 (cc-wiki): answer IPackageManager.getPackagesForUid/getNameForUid for this process's own
        // uid. route-A's package projection returns nothing for self-uid, so StorageManager.getVolumeList
        // logs "Missing package names" and returns an empty StorageVolume[] without asking the (already
        // installed) child-local mount binder; amaze-filemanager's AppConfig <clinit> then indexes [0] of
        // the empty array and dies. Passthrough for every other call.
        try {
            SelfUidPackages.install(ai);
        } catch (Throwable t) {
            System.err.println("[SELF-UID] not installed: " + t);
        }
        // J2 (#newpipe): answer getPackageInfo("android") with a synthesized system package (BMS denies
        // GET_BUNDLE_INFO_PRIVILEGED). Chains over SelfUidPackages' IPackageManager proxy.
        try {
            AndroidFrameworkPackage.install();
        } catch (Throwable t) {
            System.err.println("[B8-ANDROIDPKG] not installed: " + t);
        }
        // r17d (#media_session): a MediaSessionCompat-based service (noice/fossify-musicplayer's
        // SoundPlaybackService / MediaSessionService) constructs a platform MediaSession, whose <init>
        // calls MediaSessionManager.createSession(); route-A has no MEDIA_SESSION_SERVICE, so the
        // manager is null and it NPEs before the service reaches its UI. WlMediaSession (verbatim
        // Westlake) registers a local ISessionManager (sCache binder + SystemServiceRegistry fetcher)
        // whose createSession returns a no-op ISession.
        try {
            System.err.println("[B8-MSESSION] " + adapter.compat.WlMediaSession.install());
        } catch (Throwable t) {
            System.err.println("[B8-MSESSION] not installed: " + t);
        }
        // J4 (#noice): getSystemService(MEDIA_ROUTER_SERVICE) -> MediaRouter.<init> -> rebindAsUser ->
        // registerClientAsUser on a null IMediaRouterService (route-A returns null for "media_router").
        // Same sCache-binder shape as WlMediaSession: a no-op local IMediaRouterService so Noice's
        // SystemMediaRouteProvider builds instead of NPEing before its player UI.
        try {
            System.err.println("[B8-MROUTER] " + adapter.compat.WlMediaRouter.install());
        } catch (Throwable t) {
            System.err.println("[B8-MROUTER] not installed: " + t);
        }
        // J5 (#webview): the Java half of the N3b WebView publication contract (JAVA-HANDOFF.md). Pre-bind:
        // route the webviewupdate service + WebView package answers, then nativePrime (holds the feature
        // false). Post-bind: nativePublishAfterBind on the main thread AFTER Application.onCreate, before
        // the first Activity -- a Handler.post here runs after the bind message (and thus onCreate)
        // completes. INERT with no ASX_WEBVIEW_APK: isAvailable() is false, nothing is routed/primed, the
        // feature stays false. Honors the boolean result -- feature=published alone is not success.
        try {
            adapter.core.WebViewPackageFallback.install();
            System.err.println("[B8-WEBVIEW] " + adapter.core.WestlakeWebViewInstall.install());
            if (adapter.core.WestlakeWebViewInstall.isAvailable()) {
                new android.os.Handler(android.os.Looper.getMainLooper()).post(new Runnable() {
                    @Override public void run() { adapter.core.WestlakeWebViewInstall.publishAfterBind(); }
                });
            }
        } catch (Throwable t) {
            System.err.println("[B8-WEBVIEW] not installed: " + t);
        }
        // r17t (#audio/noice): AudioProductStrategy.getAudioProductStrategies() lazy-loads via the native
        // native_list_audio_product_strategies, which route-A does not export -> the JNI throws and
        // RuntimeInit calls System.exit(1) before the UI (noice, and the same audio-JNI family reaches
        // opencamera/vlc). Pre-seed the static cache with an empty list so the getter never enters its
        // lazy branch and never touches native. Same idea as the Providers array rewrite; no ArtMethod
        // patch (which SIGSEGVs on this generation's ART).
        try {
            stubAudioProductStrategies();
        } catch (Throwable t) {
            System.err.println("[B8-AUDIO] not stubbed: " + t);
        }
        // r17e (#alarm/#vibrator): the last mile from a LocalServiceBinders binder to its Manager.
        // OH's SystemServiceRegistry fetcher for ALARM_SERVICE does not consume our in-process "alarm"
        // binder, so getSystemService(ALARM_SERVICE) returns null and k9/fd-android's
        // AndroidAlarmManager.<init> NPEs on a null .getClass(); vibrator_manager is real-routed but
        // its getVibratorIds() returns a null array (fossify-reader). Replace both SYSTEM_SERVICE_
        // FETCHERS entries with ones that build a non-null Manager.
        try {
            SystemServiceFetcherStubs.install();
        } catch (Throwable t) {
            System.err.println("[B8-FETCH] not installed: " + t);
        }
        // r17e (#AndroidKeyStore): apps calling KeyStore.getInstance("AndroidKeyStore") (fossify-tasks,
        // crypto apps) get "AndroidKeyStore not found" -- route-A has no keystore2 provider. Install
        // Westlake's software-backed provider (keys under the app's no_backup dir), reflectively.
        try {
            if (ai != null && ai.dataDir != null) {
                Class.forName("adapter.core.SoftwareAndroidKeyStore")
                        .getMethod("install", java.io.File.class)
                        .invoke(null, new java.io.File(ai.dataDir, "no_backup"));
            }
        } catch (Throwable t) {
            System.err.println("[B8-KEYSTORE] not installed: " + t);
        }
        // r17 (#93): Westlake HTTPS/TLS Java side. OhTrustBridge restores the BC JCA registrations the
        // trimmed BCP dropped (MessageDigest, AES, X.509 CertificateFactory, RSA/EC signatures, EC
        // KeyFactory) and publishes SecureRandom.WestlakeKernel + TrustManagerFactory.OH-PKIX/PKIX/X509
        // backed by the platform CA bundle (OhSystemTrustManager). WestlakeSSLSocket declares the seven
        // OpenSSL-boundary natives so cx-t0's wl_register_tls_natives binds. Called reflectively (the
        // TLS classes compile in a separate android-bootclasspath pass) at bind in the forked child --
        // clear of AppSpawnXInit's parent Security.getProviders() clinit trap (L296-303).
        try {
            Class.forName("adapter.security.WestlakeTlsInstall").getMethod("install").invoke(null);
        } catch (Throwable t) {
            System.err.println("[B8-TLS] not installed: " + t);
        }
    }

    /**
     * Non-main-thread uncaught exceptions end only that thread (logged), not the process; the main
     * thread is handed back to the original handler (AOSP's exit behaviour). Copies the intent of
     * Westlake's AppSpawnXInit tolerant handler but as a per-bind Thread default handler in the
     * runtime JAR, so no boot-image change is needed.
     */
    /**
     * r17c: System.load the TLS boundary and HTML-compat libraries by absolute child path, in order
     * (TLS first). Called from apply() so the caller class loader is the runtime PathClassLoader.
     */
    static void loadWestlakeNativeLibs() {
        // r17d: give the runtime PathClassLoader a native dependency domain first. Without a
        // librarySearchPath it has none, so native_loader rejects every System.load of a
        // /system/android/lib64 soname ("no native dependency domain for ClassLoader",
        // native_loader_registry.cpp:332). Creating the namespace explicitly is the fix.
        createNativeNamespace();
        // Framework JNI gap-fill first (56b5295c): supplies Process.getElapsedCpuTime, FileObserver,
        // Camera.getNumberOfCameras, EGLImpl._nativeClassInit and ActivityManagerAdapter.
        // nativeStopServiceAbility -- the native symbols apps reach once the receiver/broadcast guards
        // let them run past the early ULEs (catima/amaze/vector/meet/spd/opencamera).
        loadLib("/system/android/lib64/libwestlake_jni_gapfill.so");
        // TLS boundary (8ecf6250): its JNI_OnLoad registers WestlakeSSLSocket's seven natives.
        loadLib("/system/android/lib64/liboh_tls_boundary.so");
        // HTML compat (26ac847b): the native JNI_OnLoad rewrites android.text.Html.fromHtml into a call
        // to the class named by WESTLAKE_HTML_COMPAT_CLASS, gated by WESTLAKE_HTML_COMPAT=1. Both envs
        // must be set in this child BEFORE the library loads (cx-t0 handoff 2026-09-30-tls-native-handoff).
        try {
            android.system.Os.setenv("WESTLAKE_HTML_COMPAT", "1", true);
            android.system.Os.setenv("WESTLAKE_HTML_COMPAT_CLASS", "adapter.compat.HtmlCompatFallback", true);
            System.err.println("[B8-NATIVE] WESTLAKE_HTML_COMPAT env set");
        } catch (Throwable t) {
            System.err.println("[B8-NATIVE] setenv WESTLAKE_HTML_COMPAT failed: " + t);
        }
        loadLib("/system/android/lib64/libwestlake_html_compat.so");
    }

    private static void loadLib(String path) {
        try {
            System.load(path);
            System.err.println("[B8-NATIVE] loaded " + path);
        } catch (Throwable t) {
            System.err.println("[B8-NATIVE] System.load(" + path + ") failed: " + t);
        }
    }

    /**
     * r17d: reflectively call com.android.internal.os.ClassLoaderFactory.createClassloaderNamespace to
     * build a native-library namespace for the runtime PathClassLoader with librarySearchPath =
     * /system/android/lib64. The signature is OH-version-specific, so discover the method by name and
     * fill its parameters by type/position: ClassLoader -> runtime loader, int -> targetSdk, the first
     * two Strings -> the lib search + permitted paths, the next String -> the runtime JAR dexPath,
     * booleans -> false, any trailing arg -> null. A null return means success.
     */
    private static void createNativeNamespace() {
        try {
            Class<?> factory = Class.forName("com.android.internal.os.ClassLoaderFactory");
            ClassLoader runtimeCl = B7BindFixes.class.getClassLoader();
            java.lang.reflect.Method create = null;
            for (java.lang.reflect.Method m : factory.getDeclaredMethods()) {
                if (m.getName().equals("createClassloaderNamespace")) { create = m; break; }
            }
            if (create == null) {
                System.err.println("[B8-NATIVE] createClassloaderNamespace not found; libs will be rejected");
                return;
            }
            create.setAccessible(true);
            // r17j: liboh_tls_boundary dlopens the board's OpenSSL (libssl_openssl.z.so /
            // libcrypto_openssl.z.so) from these system dirs. The namespace must search AND permit them
            // or the ANL domain rejects the dlopen ("check ns accessible failed") and the TLS handshake
            // self-test fails, leaving the factory dormant (oc-t4). kBridgePermittedPaths already lists
            // platformsdk in policy; the runtime domain-creation call just was not carrying them.
            final String base = "/system/android/lib64";
            final String openssl = "/system/lib64/platformsdk:/system/lib64/chipset-sdk:/system/lib64/chipset-sdk-sp";
            final String lib = base + ":" + openssl;   // both librarySearchPath and libraryPermittedPath
            final String dexPath = runtimeJarPath(runtimeCl);
            Class<?>[] pt = create.getParameterTypes();
            Object[] args = new Object[pt.length];
            int stringSeen = 0;
            for (int i = 0; i < pt.length; i++) {
                Class<?> t = pt[i];
                if (t == ClassLoader.class) {
                    args[i] = runtimeCl;
                } else if (t == int.class) {
                    args[i] = Integer.valueOf(34);           // targetSdkVersion
                } else if (t == boolean.class) {
                    args[i] = Boolean.FALSE;                 // isShared / isForVendor
                } else if (t == String.class) {
                    // order: librarySearchPath, libraryPermittedPath, dexPath, [name...]
                    args[i] = stringSeen < 2 ? lib : (stringSeen == 2 ? dexPath : null);
                    stringSeen++;
                } else {
                    args[i] = null;
                }
            }
            Object result = create.invoke(null, args);
            if (result == null) {
                System.err.println("[B8-NATIVE] native namespace created for runtime CL (search=" + lib + ")");
            } else {
                System.err.println("[B8-NATIVE] createClassloaderNamespace returned: " + result);
            }
        } catch (Throwable t) {
            System.err.println("[B8-NATIVE] createNativeNamespace failed: " + t);
        }
    }

    /** The runtime JAR path from the PathClassLoader's toString, else the known deploy target. */
    private static String runtimeJarPath(ClassLoader cl) {
        try {
            String s = String.valueOf(cl);
            int z = s.indexOf("zip file \"");
            if (z >= 0) {
                int start = z + "zip file \"".length();
                int end = s.indexOf('"', start);
                if (end > start) return s.substring(start, end);
            }
        } catch (Throwable ignore) {
        }
        return "/system/android/framework/oh-adapter-runtime.jar";
    }

    static void installTolerantUncaughtHandler() {
        try {
            final Thread.UncaughtExceptionHandler original = Thread.getDefaultUncaughtExceptionHandler();
            final Thread mainThread = android.os.Looper.getMainLooper().getThread();
            Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
                @Override
                public void uncaughtException(Thread thread, Throwable ex) {
                    if (thread == mainThread) {
                        if (original != null) original.uncaughtException(thread, ex);
                        return;
                    }
                    System.err.println("[B8-UEH] background thread '" + thread.getName()
                            + "' uncaught, thread ended (process kept alive): " + ex);
                    ex.printStackTrace();
                }
            });
            System.err.println("[B8-UEH] tolerant uncaught-exception handler installed");
        } catch (Throwable t) {
            System.err.println("[B8-UEH] not installed: " + t);
        }
    }

    static void applyImpellerFallback(ApplicationInfo ai) {
        try {
            if (ai == null) return;
            if (ai.metaData == null) ai.metaData = new android.os.Bundle();
            if (!ai.metaData.containsKey("io.flutter.embedding.android.EnableImpeller")) {
                ai.metaData.putBoolean("io.flutter.embedding.android.EnableImpeller", false);
                System.err.println("[B8-IMPELLER] EnableImpeller=false injected into metaData");
            }
        } catch (Throwable t) {
            System.err.println("[B8-IMPELLER] not applied: " + t);
        }
    }

    static void fixNativeLibraryDir(ApplicationInfo ai) {
        if (ai == null) return;
        String current = ai.nativeLibraryDir;
        if (current != null && new File(current).isDirectory()) return;
        if (ai.sourceDir == null) return;
        File codeDir = new File(ai.sourceDir).getParentFile();
        if (codeDir == null || !codeDir.isDirectory()) return;
        File arm64 = new File(codeDir, "lib/arm64-v8a");
        String replacement = arm64.isDirectory() ? arm64.getPath() : codeDir.getPath();
        ai.nativeLibraryDir = replacement;
        System.err.println("[B7] nativeLibraryDir " + current + " does not exist; using "
                + replacement);
    }

    /**
     * r17t (#audio/noice, cc-wiki 09:06): stub android.media.audiopolicy.AudioProductStrategy so
     * getAudioProductStrategies() returns an empty list without the native list call. The class caches
     * its result in a private static field `sAudioProductStrategies` and only enters its lazy branch
     * (initializeAudioProductStrategies -> native_list_audio_product_strategies, which route-A does not
     * export -> System.exit(1)) when that field is null. Pre-seed the field with an unmodifiable empty
     * list at bind, before the app touches audio-policy, so the native path is never taken. Empty-list
     * is safe for the downstream callers (getVolumeGroupIdForAudioAttributes -> DEFAULT_GROUP, legacy
     * stream-type lookups -> none). Reflection on a boot class, same shape as fixJarVerificationProvider.
     */
    static void stubAudioProductStrategies() {
        try {
            Class<?> aps = Class.forName("android.media.audiopolicy.AudioProductStrategy");
            java.lang.reflect.Field f = aps.getDeclaredField("sAudioProductStrategies");
            f.setAccessible(true);
            if (f.get(null) != null) {
                System.err.println("[B8-AUDIO] AudioProductStrategy cache already populated; left as-is");
                return;
            }
            f.set(null, java.util.Collections.emptyList());
            System.err.println("[B8-AUDIO] AudioProductStrategy.sAudioProductStrategies pre-seeded empty "
                    + "(getAudioProductStrategies bypasses native_list_audio_product_strategies)");
        } catch (Throwable t) {
            System.err.println("[B8-AUDIO] stubAudioProductStrategies failed (non-fatal): " + t);
        }
    }

    /**
     * r17s (dlopen_ns DISCRIMINATING EXPERIMENT, cc-t3 -- NOT a confirmed fix). Several apps' own
     * native libs fail to load a system/NDK dependency that EXISTS on the image but is unreachable
     * from the app's linker namespace: unciv libgdx.so -> libstdc++.so (/system/android/lib64),
     * mindustry libarc.so -> libOpenSLES.so (/system/lib64), nextcloud libconscrypt_jni.so ->
     * liblog.so (/system/android/lib64). The app namespace's search+permitted paths are built
     * natively (native-loader-oh/appspawn-x); no runtime-JAR Java class assembles them. This probe
     * appends the two dep dirs to the app classloader's DexPathList native search path by reflection.
     * If OH's native-loader consults DexPathList.nativeLibraryPathElements for a later
     * System.loadLibrary, the deps resolve (JAR-fixable); if the frozen native namespace wins,
     * nothing changes (native-owned -> cx-t0). Fail-safe, log-only, additive.
     */
    static void extendAppNativeLibrarySearchPath() {
        final String[] extra = {"/system/lib64", "/system/android/lib64"};
        try {
            ClassLoader appCl = Thread.currentThread().getContextClassLoader();
            if (appCl == null || appCl == B7BindFixes.class.getClassLoader()) {
                System.err.println("[B8-DLEXP] app classloader unavailable (ctx=" + appCl + "); skipped");
                return;
            }
            if (!(appCl instanceof dalvik.system.BaseDexClassLoader)) {
                System.err.println("[B8-DLEXP] context classloader not BaseDexClassLoader: " + appCl.getClass());
                return;
            }
            java.lang.reflect.Field plF = dalvik.system.BaseDexClassLoader.class.getDeclaredField("pathList");
            plF.setAccessible(true);
            Object pathList = plF.get(appCl);
            java.lang.reflect.Field ndF = pathList.getClass().getDeclaredField("nativeLibraryDirectories");
            ndF.setAccessible(true);
            @SuppressWarnings("unchecked")
            java.util.List<java.io.File> dirs = (java.util.List<java.io.File>) ndF.get(pathList);
            System.err.println("[B8-DLEXP] app nativeLibraryDirectories BEFORE = " + dirs);
            boolean added = false;
            for (String d : extra) {
                boolean present = false;
                for (java.io.File e : dirs) { if (e != null && d.equals(e.getPath())) { present = true; break; } }
                if (!present) { dirs.add(new java.io.File(d)); added = true; }
            }
            if (!added) {
                System.err.println("[B8-DLEXP] app path already had the dep dirs; nothing to add");
                return;
            }
            java.lang.reflect.Field elF = null;
            try { elF = pathList.getClass().getDeclaredField("nativeLibraryPathElements"); }
            catch (NoSuchFieldException nsf) { /* older/other DexPathList */ }
            Object rebuilt = null;
            if (elF != null) {
                for (java.lang.reflect.Method m : pathList.getClass().getDeclaredMethods()) {
                    if (m.getName().equals("makePathElements")
                            && m.getParameterTypes().length == 1
                            && java.util.List.class.isAssignableFrom(m.getParameterTypes()[0])) {
                        m.setAccessible(true);
                        rebuilt = m.invoke(null, dirs);
                        break;
                    }
                }
                if (rebuilt != null) {
                    elF.setAccessible(true);
                    elF.set(pathList, rebuilt);
                    System.err.println("[B8-DLEXP] appended " + java.util.Arrays.toString(extra)
                            + " + rebuilt nativeLibraryPathElements (experiment ACTIVE)");
                    return;
                }
            }
            System.err.println("[B8-DLEXP] dirs appended but nativeLibraryPathElements NOT rebuilt (makePathElements(List) absent on "
                    + pathList.getClass() + "); loader likely ignores -> expect no change (native-owned)");
        } catch (Throwable t) {
            System.err.println("[B8-DLEXP] app native-search-path extend failed (non-fatal): " + t);
        }
    }

}
