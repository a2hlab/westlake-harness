// M2 A0 probe shim (benchmark/2026-10-03-m2-a0-probe). Test-only.
// Loaded by System.loadLibrary("a0shim") into the app's own linker namespace. It opens liba0probe.so (from the same
// APK lib dir) so that the probe's NEEDED OH platformsdk libraries resolve through musl's "default" namespace (the one
// liboh_adapter_bridge.so lives in), then calls a0_probe_start(bundle). Returns a one-line status for the Java side.
//
// v2 (window 2: dlopen_ns(default, <absolute app path>) failed for every candidate dir): first create a private
// namespace on the app lib dir that inherits "default" with allow_all_shared_libs, exactly the pattern OH's own ArkWeb
// loader uses for the engine (arkweb_utils.cpp ArkWebBridgeHelperLoadLibFile: dlns_init + dlns_create +
// dlns_inherit + dlopen_ns). The window-2 path (direct dlopen_ns into default) stays as the second attempt. dlerror()
// is recorded after every attempt.
#include <dlfcn.h>
#include <jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (*StartFn)(const char*);
// The NDK sysroot libc.so stub does not export the musl namespace API; the board libc (ld-musl) does. Resolve at run time.
typedef int (*DlnsGetFn)(const char*, Dl_namespace*);
typedef void* (*DlopenNsFn)(Dl_namespace*, const char*, int);
typedef void (*DlnsInitFn)(Dl_namespace*, const char*);
typedef int (*DlnsCreateFn)(Dl_namespace*, const char*);
typedef int (*DlnsInheritFn)(Dl_namespace*, Dl_namespace*, const char*);

static void Append(char* msg, size_t cap, const char* fmt, const char* a, int b, const char* e)
{
    size_t n = strlen(msg);
    if (n < cap) snprintf(msg + n, cap - n, fmt, a, b, e ? e : "-");
}

JNIEXPORT jstring JNICALL Java_org_westlake_a0probe_MainActivity_nativeStart(JNIEnv* env, jclass clazz, jstring jdir,
                                                                             jstring jbundle)
{
    (void)clazz;
    char msg[1600] = "[A0-SHIM]";
    const char* dir = (*env)->GetStringUTFChars(env, jdir, NULL);
    const char* bundle = (*env)->GetStringUTFChars(env, jbundle, NULL);
    DlnsGetFn dlnsGet = (DlnsGetFn)dlsym(RTLD_DEFAULT, "dlns_get");
    DlopenNsFn dlopenNs = (DlopenNsFn)dlsym(RTLD_DEFAULT, "dlopen_ns");
    DlnsInitFn dlnsInit = (DlnsInitFn)dlsym(RTLD_DEFAULT, "dlns_init");
    DlnsCreateFn dlnsCreate = (DlnsCreateFn)dlsym(RTLD_DEFAULT, "dlns_create");
    DlnsInheritFn dlnsInherit = (DlnsInheritFn)dlsym(RTLD_DEFAULT, "dlns_inherit");
    void* h = NULL;
    Dl_namespace def;
    int defrc = dlnsGet ? dlnsGet("default", &def) : -200;
    Append(msg, sizeof(msg), " dir=%s dlns_get(default)=%d%s", dir, defrc, "");

    // attempt 1: private namespace on the app lib dir, inheriting default (allow_all_shared_libs)
    if (dlnsInit && dlnsCreate && dlnsInherit && dlopenNs && defrc == 0) {
        Dl_namespace ns;
        dlnsInit(&ns, "wl_a0probe");
        int crc = dlnsCreate(&ns, dir);
        int irc = dlnsInherit(&ns, &def, "allow_all_shared_libs");
        dlerror();
        h = dlopenNs(&ns, "liba0probe.so", RTLD_NOW | RTLD_LOCAL);
        char tag[96];
        snprintf(tag, sizeof(tag), " | ns wl_a0probe create=%d inherit=%d", crc, irc);
        Append(msg, sizeof(msg), "%s open=%d err=%s", tag, h != NULL, h ? NULL : dlerror());
    }
    // attempt 2 (window 2): absolute path straight into default
    if (h == NULL && dlopenNs && defrc == 0) {
        char path[400];
        snprintf(path, sizeof(path), "%s/liba0probe.so", dir);
        dlerror();
        h = dlopenNs(&def, path, RTLD_NOW | RTLD_LOCAL);
        Append(msg, sizeof(msg), " | default+abs %s open=%d err=%s", path, h != NULL, h ? NULL : dlerror());
    }
    if (h != NULL) {
        StartFn start = (StartFn)dlsym(h, "a0_probe_start");
        int rc = start ? start(bundle) : -100;
        size_t n = strlen(msg);
        snprintf(msg + n, sizeof(msg) - n, " | handle=%p a0_probe_start=%p rc=%d", h, (void*)start, rc);
    } else {
        size_t n = strlen(msg);
        snprintf(msg + n, sizeof(msg) - n, " | FAILED");
    }
    (*env)->ReleaseStringUTFChars(env, jdir, dir);
    (*env)->ReleaseStringUTFChars(env, jbundle, bundle);
    return (*env)->NewStringUTF(env, msg);
}

// Window 17: MainActivity.nativeSurfaceReady is now registered by the RUNTIME entry (libwestlake_html_compat.so), not
// here. The app-ns a0shim could not open ANativeWindow_fromSurface's bridge hook (window 16: env never set), so the
// surface conversion moved to the entry, which lives in the runtime-adjacent namespace. a0shim keeps only nativeStart.
