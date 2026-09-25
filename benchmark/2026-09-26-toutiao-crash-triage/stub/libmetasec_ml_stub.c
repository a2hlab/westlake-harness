/*
 * libmetasec_ml_stub.c  [#48 hollow metasec]
 *
 * A no-op replacement for the app's libmetasec_ml.so. The real ByteDance
 * metasec runs an anti-fraud init that reads Bionic pthread_internal_t layout
 * (~7 s after JNI_OnLoad) and SIGSEGVs on musl — a Bionic-bound residual that
 * no symbol-closure fix removes (partial closure -> probabilistic sixth exit,
 * full closure -> init crash; no sweet spot). #41 established metasec is not
 * required for feed + article reading, so a hollow stub that never runs real
 * init is the last non-Bionic option.
 *
 * The entire native ABI the app needs from this library (verified from the
 * toutiao APK + the real .so, benchmark scripts/scan_jni_methods.py + androguard):
 *   - the real .so exports exactly ONE dynamic symbol: JNI_OnLoad
 *     (no other lib DT_NEEDs libmetasec_ml.so, so there is no native-to-native
 *      import surface to satisfy)
 *   - the app declares exactly ONE native method backed by metasec — a single
 *     dispatcher:
 *       class  ms.bd.c.m
 *       method public static native
 *              Object a(int, int, long, String, Object)
 *       JNI    (IIJLjava/lang/String;Ljava/lang/Object;)Ljava/lang/Object;
 *     Every com.bytedance.mobsec.metasec.ml.* class is a pure-Java wrapper that
 *     funnels through ms.bd.c.m.a(cmd, ...); none has a native method.
 *
 * So the stub provides JNI_OnLoad + a no-op ms.bd.c.m.a returning null. null is
 * the conventional "SDK not ready" result these dispatchers return; the Java
 * wrappers treat it as metasec-unavailable. Two resolution paths are covered:
 *   1. Java_ms_bd_c_m_a export -> ART default resolution at first call (uses the
 *      app classloader, the reliable path).
 *   2. RegisterNatives in JNI_OnLoad (best-effort; FindClass there may miss the
 *      app class under the system classloader, which is why path 1 exists).
 *
 * No real init, no pthread reads, nothing that can SIGSEGV on musl.
 */
#include <jni.h>
#include <stddef.h>

/* The single metasec dispatcher, as a no-op. Static native -> (env, jclass, ...). */
static jobject metasec_dispatch_noop(JNIEnv *env, jclass clazz,
                                     jint a, jint b, jlong c,
                                     jstring d, jobject e)
{
    (void)env; (void)clazz; (void)a; (void)b; (void)c; (void)d; (void)e;
    return NULL; /* "metasec unavailable" — wrappers treat null as not-ready */
}

/* Path 1: ART default JNI resolution. ms.bd.c.m has one native method 'a',
 * so the short mangled name is used (ms/bd/c/m -> ms_bd_c_m, no '_' to escape). */
JNIEXPORT jobject JNICALL
Java_ms_bd_c_m_a(JNIEnv *env, jclass clazz,
                 jint a, jint b, jlong c, jstring d, jobject e)
{
    return metasec_dispatch_noop(env, clazz, a, b, c, d, e);
}

/* Path 2: explicit registration, mirroring what the real JNI_OnLoad does. */
static const JNINativeMethod g_methods[] = {
    { "a", "(IIJLjava/lang/String;Ljava/lang/Object;)Ljava/lang/Object;",
      (void *)metasec_dispatch_noop },
};

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved)
{
    JNIEnv *env = NULL;
    (void)reserved;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) == JNI_OK && env != NULL) {
        jclass cls = (*env)->FindClass(env, "ms/bd/c/m");
        if (cls != NULL) {
            (*env)->RegisterNatives(env, cls, g_methods,
                                    (jint)(sizeof(g_methods) / sizeof(g_methods[0])));
            (*env)->DeleteLocalRef(env, cls);
        }
        /* A stub must never propagate a pending exception (e.g. FindClass NoClassDefFound). */
        if ((*env)->ExceptionCheck(env)) {
            (*env)->ExceptionClear(env);
        }
    }
    return JNI_VERSION_1_6; /* report success regardless; path 1 covers resolution */
}
