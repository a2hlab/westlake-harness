/*
 * libmetasec_ml_stub.c  [#48 hollow metasec — safe-value dispatcher]
 *
 * A no-op replacement for the app's libmetasec_ml.so. The real ByteDance
 * metasec runs an anti-fraud init that reads Bionic pthread_internal_t layout
 * (~7 s after JNI_OnLoad) and SIGSEGVs on musl — a Bionic-bound residual no
 * symbol-closure fix removes. #41: metasec is not required for feed + article
 * reading, so a hollow stub that never runs real init is the last non-Bionic
 * option. First trial (null dispatcher) proved metasec is fully bypassable —
 * feed + real images render — but returning null from the dispatcher NPE'd the
 * app's wrappers (Boolean.booleanValue() on null; ms.bd.c.p2.d -> MSManagerUtils.init).
 *
 * The whole native ABI is one JNI_OnLoad + one dispatcher:
 *   class  ms.bd.c.m ; method public static native
 *          Object a(int cmd, int, long, String, Object)
 * Every com.bytedance.mobsec.metasec.ml.* class is a pure-Java wrapper funneling
 * through ms.bd.c.m.a(cmd, ...). The cmd's high byte is the command family; the
 * app check-casts the Object result per cmd, so the stub must return a non-null
 * value of the TYPE each cmd expects (a null unboxes to NPE). The cmd -> return
 * type map was recovered from all 617 call sites in the toutiao APK (evidence
 * evidence/dispatch-map-48.txt, scripts/dispatch_map.py):
 *
 *   0x01xxxxxx           -> String        (402+ sites; token/string getters)
 *   0x02000006/0a,0x03000001 -> String[]  (getFeatureHash/frameSign/addSecurityFactor)
 *   0x02000007/0c,0x04000003 -> String    (getToken/versionInfo/...)
 *   0x04000001,0x04000004 -> Boolean      (unboxed .booleanValue())
 *   0x08000001..04       -> Integer       (unboxed .intValue())
 *   everything else       -> the app null-checks (if-nez) or ignores the result
 *
 * Boolean values are TRUE, not false, on purpose: f3.run (0x04000004) spins
 * `while(!a(...)) sleep(500)` — false would hang it — and p2.d (0x04000001,
 * MSManagerUtils.init) just records timing and returns the flag, where TRUE =
 * "ready/ok" avoids caller retry/degrade. Integer is 0 (neutral status).
 * Strings are "" and String[] are empty; the app compares them (they won't
 * match a real signature) and takes the benign "no-op" branch.
 *
 * No real init, no pthread reads, nothing that can SIGSEGV on musl.
 */
#include <jni.h>
#include <stddef.h>
#include <stdint.h>

/* ---- boxing helpers (the java.lang wrapper classes are always resolvable from
 *      a native called with Java frames on the stack) ---- */
static jobject box_boolean(JNIEnv *env, jboolean v)
{
    jclass c = (*env)->FindClass(env, "java/lang/Boolean");
    if (c == NULL) return NULL;
    jmethodID m = (*env)->GetStaticMethodID(env, c, "valueOf", "(Z)Ljava/lang/Boolean;");
    return m ? (*env)->CallStaticObjectMethod(env, c, m, v) : NULL;
}

static jobject box_int(JNIEnv *env, jint v)
{
    jclass c = (*env)->FindClass(env, "java/lang/Integer");
    if (c == NULL) return NULL;
    jmethodID m = (*env)->GetStaticMethodID(env, c, "valueOf", "(I)Ljava/lang/Integer;");
    return m ? (*env)->CallStaticObjectMethod(env, c, m, v) : NULL;
}

static jobject empty_string(JNIEnv *env)
{
    return (*env)->NewStringUTF(env, "");
}

static jobject empty_string_array(JNIEnv *env)
{
    jclass c = (*env)->FindClass(env, "java/lang/String");
    return c ? (*env)->NewObjectArray(env, 0, c, NULL) : NULL;
}

/* The single metasec dispatcher, returning a type-correct safe value per cmd. */
static jobject metasec_dispatch(JNIEnv *env, jclass clazz,
                                jint cmd, jint a2, jlong a3, jstring a4, jobject a5)
{
    (void)clazz; (void)a2; (void)a3; (void)a4; (void)a5;
    switch ((uint32_t)cmd) {
    /* Boolean (caller unboxes .booleanValue()); TRUE avoids retry/wait loops. */
    case 0x04000001u:
    case 0x04000004u:
        return box_boolean(env, JNI_TRUE);
    /* Integer (caller unboxes .intValue()); 0 = neutral status. */
    case 0x08000001u:
    case 0x08000002u:
    case 0x08000003u:
    case 0x08000004u:
        return box_int(env, 0);
    /* String[] (getFeatureHash / frameSign / onCallToAddSecurityFactor). */
    case 0x02000006u:
    case 0x0200000au:
    case 0x03000001u:
        return empty_string_array(env);
    /* String (getToken / versionInfo / string getters outside the 0x01 family). */
    case 0x01000001u:
    case 0x01000008u:
    case 0x02000007u:
    case 0x0200000cu:
    case 0x04000003u:
        return empty_string(env);
    default:
        /* Families: 0x01 => String, 0x08 => Integer. Everything else the app
         * null-checks (if-nez) or ignores, so null is the safe answer there. */
        switch (((uint32_t)cmd >> 24) & 0xffu) {
        case 0x01u:
            return empty_string(env);
        case 0x08u:
            return box_int(env, 0);
        default:
            return NULL;
        }
    }
}

/* Path 1: ART default JNI resolution. ms.bd.c.m has one native method 'a',
 * so the short mangled name is used (ms/bd/c/m -> ms_bd_c_m, no '_' to escape). */
JNIEXPORT jobject JNICALL
Java_ms_bd_c_m_a(JNIEnv *env, jclass clazz,
                 jint cmd, jint a2, jlong a3, jstring a4, jobject a5)
{
    return metasec_dispatch(env, clazz, cmd, a2, a3, a4, a5);
}

/* Path 2: explicit registration, mirroring the real JNI_OnLoad. */
static const JNINativeMethod g_methods[] = {
    { "a", "(IIJLjava/lang/String;Ljava/lang/Object;)Ljava/lang/Object;",
      (void *)metasec_dispatch },
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
        if ((*env)->ExceptionCheck(env)) {
            (*env)->ExceptionClear(env);
        }
    }
    return JNI_VERSION_1_6;
}
