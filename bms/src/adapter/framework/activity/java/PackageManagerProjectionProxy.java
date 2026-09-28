/*
 * PackageManagerProjectionProxy.java
 *
 * Narrow runtime projection for package fields that the current OH BMS bridge
 * does not yet return.  The underlying BCP IPackageManager remains authoritative
 * for every operation and every other package.
 */
package adapter.activity;

import android.content.pm.ApplicationInfo;
import android.os.Bundle;
import android.os.Trace;

import org.json.JSONObject;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

final class PackageManagerProjectionProxy implements InvocationHandler {
    private static final int FLAG_EXTRACT_NATIVE_LIBS = 0x10000000;

    private final Object delegate;
    private String packageName;
    private boolean extractNativeLibs;

    private PackageManagerProjectionProxy(Object delegate, String packageName,
            boolean extractNativeLibs) {
        this.delegate = delegate;
        this.packageName = packageName;
        this.extractNativeLibs = extractNativeLibs;
    }

    static void install(ApplicationInfo launchInfo, String manifestJson) throws Exception {
        if (launchInfo == null || launchInfo.packageName == null) {
            throw new IllegalArgumentException("launch ApplicationInfo identity is missing");
        }

        boolean extract = true;
        if (manifestJson != null && !manifestJson.isEmpty()) {
            extract = new JSONObject(manifestJson).optBoolean("extractNativeLibs", true);
        }
        project(launchInfo, launchInfo.packageName, extract);

        Class<?> activityThread = Class.forName("android.app.ActivityThread");
        Class<?> packageManagerInterface =
                Class.forName("android.content.pm.IPackageManager");
        Field field = activityThread.getDeclaredField("sPackageManager");
        field.setAccessible(true);
        Object current = field.get(null);
        if (current == null) {
            throw new IllegalStateException("ActivityThread.sPackageManager is null");
        }

        if (Proxy.isProxyClass(current.getClass())) {
            InvocationHandler handler = Proxy.getInvocationHandler(current);
            if (handler instanceof PackageManagerProjectionProxy) {
                PackageManagerProjectionProxy existing =
                        (PackageManagerProjectionProxy) handler;
                existing.packageName = launchInfo.packageName;
                existing.extractNativeLibs = extract;
                System.err.println("[ZZ-PM] projection refreshed package="
                        + launchInfo.packageName + " extractNativeLibs=" + extract);
                return;
            }
        }

        PackageManagerProjectionProxy handler = new PackageManagerProjectionProxy(
                current, launchInfo.packageName, extract);
        Object proxy = Proxy.newProxyInstance(
                packageManagerInterface.getClassLoader(),
                new Class<?>[] { packageManagerInterface }, handler);
        field.set(null, proxy);
        System.err.println("[ZZ-PM] projection installed package="
                + launchInfo.packageName + " extractNativeLibs=" + extract);
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        final Object result;
        try {
            result = method.invoke(delegate, args);
        } catch (InvocationTargetException target) {
            Throwable cause = target.getCause();
            throw cause != null ? cause : target;
        }

        if ("getApplicationInfo".equals(method.getName())
                && result instanceof ApplicationInfo) {
            ApplicationInfo info = (ApplicationInfo) result;
            if (packageName.equals(info.packageName)) {
                project(info, packageName, extractNativeLibs);
                System.err.println("[ZZ-PM] projected getApplicationInfo package="
                        + packageName + " flags=0x" + Integer.toHexString(info.flags));
            }
        }
        return result;
    }

    private static void project(ApplicationInfo info, String packageName,
            boolean extractNativeLibs) throws ReflectiveOperationException {
        if (!packageName.equals(info.packageName)) return;
        if (info.metaData == null) info.metaData = new Bundle();
        if (extractNativeLibs) {
            info.flags |= FLAG_EXTRACT_NATIVE_LIBS;
            // LoadedApk.makePaths appends base.apk!/lib/<primaryCpuAbi> even
            // when FLAG_EXTRACT_NATIVE_LIBS is set.  The OH installer has
            // already materialized this exact ABI directory; retaining the
            // redundant ZIP path makes musl's dependency probe raw-close the
            // base.apk fd while it is FILE*-owned.  Nulling only the runtime
            // ABI selector suppresses that ZIP branch while nativeLibraryDir
            // remains the authoritative extracted-library search path.
            if (info.nativeLibraryDir != null
                    && new java.io.File(info.nativeLibraryDir).isDirectory()) {
                info.primaryCpuAbi = null;
                Trace.beginSection("ZZ-PM:apk-zip-disabled");
                Trace.endSection();
                System.err.println("[ZZ-PM] extracted native path selected; apk zip path disabled package="
                        + packageName + " nativeLibraryDir=" + info.nativeLibraryDir);
            }
        } else {
            info.flags &= ~FLAG_EXTRACT_NATIVE_LIBS;
        }
    }
}
