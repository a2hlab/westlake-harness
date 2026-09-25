/*
 * westlake_liblog_native_sink.cpp  (#44)
 *
 * Compiled INTO liblog.so so that EVERY liblog instance — the framework one and
 * any separate copy an ART classloader namespace binds for the app's own native
 * libraries (Cronet / ttnet / Lynx / metasec) — self-registers a logger at load
 * time. Without this, app-native __android_log_print/__android_log_buf_write in
 * the child fall through to liblog's default logd writer, whose socket is dead on
 * OpenHarmony, and are silently dropped (see board #41/#44).
 *
 * The registered logger:
 *   - routes every record to OH hilog via HiLogPrint (LOG_TYPE_CORE, domain
 *     0xD000F00 — the same domain AppSpawnX/android_util_Log.cpp B.37 use and
 *     which is NOT filtered out of `hilog -x`), resolved through dlopen/dlsym so
 *     liblog.so gains NO hard dependency on libhilog (keeps it loadable in every
 *     namespace, incl. ones that cannot see libhilog);
 *   - when WESTLAKE_SOURCE_LOG_STDERR=1, ALSO writes the record to fd 2 in
 *     logcat-style "<prio> <tag> : <msg>\n" so a child.stderr capture shows the
 *     app's native logs. The env is read once and cached; when unset (the
 *     default, and every #38 timing run) the stderr path is skipped entirely, so
 *     the hot path is one cached-branch + the pre-existing HiLogPrint call.
 *
 * This is the native-side equivalent of the B.37 Java fix
 * (android_util_Log.cpp Log_println_native): direct-to-HiLogPrint, bypassing the
 * broken logd transport.
 */
#include <android/log.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern "C" {

typedef int (*westlake_HiLogPrintFn)(int type, int level, unsigned int domain,
                                     const char* tag, const char* fmt, ...);

// LOG_TYPE_CORE=3; hilog levels: DEBUG=3 INFO=4 WARN=5 ERROR=6 FATAL=7.
static int westlake_oh_level(int android_prio) {
    switch (android_prio) {
        case ANDROID_LOG_VERBOSE: return 3;
        case ANDROID_LOG_DEBUG:   return 3;
        case ANDROID_LOG_INFO:    return 4;
        case ANDROID_LOG_WARN:    return 5;
        case ANDROID_LOG_ERROR:   return 6;
        case ANDROID_LOG_FATAL:   return 7;
        default:                  return 4;
    }
}

static char westlake_prio_char(int android_prio) {
    switch (android_prio) {
        case ANDROID_LOG_VERBOSE: return 'V';
        case ANDROID_LOG_DEBUG:   return 'D';
        case ANDROID_LOG_INFO:    return 'I';
        case ANDROID_LOG_WARN:    return 'W';
        case ANDROID_LOG_ERROR:   return 'E';
        case ANDROID_LOG_FATAL:   return 'F';
        default:                  return 'I';
    }
}

static westlake_HiLogPrintFn westlake_resolve_hilog(void) {
    void* h = dlopen("libhilog.so", RTLD_NOLOAD | RTLD_NOW);
    if (!h) h = dlopen("libhilog.so", RTLD_NOW);
    if (!h) h = dlopen("/system/lib64/platformsdk/libhilog.so", RTLD_NOW);
    if (!h) return (westlake_HiLogPrintFn)0;
    return (westlake_HiLogPrintFn)dlsym(h, "HiLogPrint");
}

static void westlake_native_log_sink(const struct __android_log_message* m) {
    if (m == (const struct __android_log_message*)0) return;
    const char* tag = m->tag ? m->tag : "AndroidLog";
    const char* msg = m->message ? m->message : "";

    // stderr sink — gated by WESTLAKE_SOURCE_LOG_STDERR=1, env cached once.
    static int stderr_on = -1;
    if (stderr_on == -1) {
        const char* e = getenv("WESTLAKE_SOURCE_LOG_STDERR");
        stderr_on = (e && e[0] == '1' && e[1] == '\0') ? 1 : 0;
    }
    if (stderr_on) {
        char buf[4096];
        int n = snprintf(buf, sizeof(buf), "%c %s : %s\n",
                         westlake_prio_char(m->priority), tag, msg);
        if (n > 0) {
            if (n > (int)sizeof(buf)) n = (int)sizeof(buf);
            ssize_t w = write(2, buf, (size_t)n);
            (void)w;
        }
    }

    // hilog sink — always on; HiLogPrint resolved once via dlsym (no hard dep).
    static westlake_HiLogPrintFn fn = (westlake_HiLogPrintFn)0;
    static int resolved = 0;
    if (!resolved) { fn = westlake_resolve_hilog(); resolved = 1; }
    if (fn) {
        // %{public}s: hilog redacts %s as <private> by default.
        fn(3 /*LOG_TYPE_CORE*/, westlake_oh_level(m->priority), 0xD000F00u,
           tag, "%{public}s", msg);
    }
}

__attribute__((constructor))
static void westlake_register_native_log_sink(void) {
    __android_log_set_logger(westlake_native_log_sink);
}

}  // extern "C"
