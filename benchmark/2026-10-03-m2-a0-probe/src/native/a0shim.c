// M2 A0 probe shim (benchmark/2026-10-03-m2-a0-probe). Test-only.
// Loaded by System.loadLibrary("a0shim") into the app's own linker namespace. It opens liba0probe.so (from the same
// APK lib dir) in musl's "default" namespace, the one liboh_adapter_bridge.so and the OH platformsdk libraries are
// visible from, and calls a0_probe_start(bundle). Returns a one-line status for the Java side to print.
#include <dlfcn.h>
#include <jni.h>
#include <stdio.h>
#include <string.h>

typedef int (*StartFn)(const char*);
// The NDK sysroot libc.so stub does not export the musl namespace API; the board libc (ld-musl) does. Resolve at run time.
typedef int (*DlnsGetFn)(const char*, Dl_namespace*);
typedef void* (*DlopenNsFn)(Dl_namespace*, const char*, int);

JNIEXPORT jstring JNICALL Java_org_westlake_a0probe_MainActivity_nativeStart(JNIEnv* env, jclass clazz, jstring jdir,
                                                                             jstring jbundle)
{
    (void)clazz;
    char msg[600];
    const char* dir = (*env)->GetStringUTFChars(env, jdir, NULL);
    const char* bundle = (*env)->GetStringUTFChars(env, jbundle, NULL);
    const char* dirs[] = {dir, "/data/storage/el1/bundle/android/lib/arm64-v8a", "/data/storage/el1/bundle/libs/arm64"};
    DlnsGetFn dlnsGet = (DlnsGetFn)dlsym(RTLD_DEFAULT, "dlns_get");
    DlopenNsFn dlopenNs = (DlopenNsFn)dlsym(RTLD_DEFAULT, "dlopen_ns");
    Dl_namespace ns;
    int nsrc = (dlnsGet && dlopenNs) ? dlnsGet("default", &ns) : -200;
    void* h = NULL;
    char path[300] = "";
    for (unsigned i = 0; i < sizeof(dirs) / sizeof(dirs[0]) && h == NULL; i++) {
        if (dirs[i] == NULL) continue;
        snprintf(path, sizeof(path), "%s/liba0probe.so", dirs[i]);
        h = nsrc == 0 ? dlopenNs(&ns, path, RTLD_NOW | RTLD_LOCAL) : dlopen(path, RTLD_NOW | RTLD_LOCAL);
    }
    if (h == NULL) {
        const char* e = dlerror();
        snprintf(msg, sizeof(msg), "[A0-SHIM] dlns_get(default)=%d dlopen_ns(%s) FAILED: %s", nsrc, path, e ? e : "?");
    } else {
        StartFn start = (StartFn)dlsym(h, "a0_probe_start");
        int rc = start ? start(bundle) : -100;
        snprintf(msg, sizeof(msg), "[A0-SHIM] dlns_get(default)=%d loaded %s handle=%p a0_probe_start=%p rc=%d", nsrc,
                 path, h, (void*)start, rc);
    }
    (*env)->ReleaseStringUTFChars(env, jdir, dir);
    (*env)->ReleaseStringUTFChars(env, jbundle, bundle);
    return (*env)->NewStringUTF(env, msg);
}
