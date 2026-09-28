// Copyright 2026.
//
// Late JNI overrides for the Android 11 ICU4J regex and converter bridges.
//
// The board's ART registers its built-in ICU stubs while JNI_CreateJavaVM is
// starting. AndroidRuntime::startReg runs afterwards, so these fail-hard
// RegisterNatives calls deliberately use JNI's last-writer-wins semantics.
//
// Important constraints:
//   * DEX/JAR method declarations are not changed.
//   * ICU C symbols are resolved as one version cohort from the board DSOs.
//   * No ICU C++ ABI or C++ standard-library containers cross this boundary.
//   * Regex Pattern/Matcher registration is one fail-hard cohort because their
//     native handle layouts are coupled.
//   * NativeConverter intentionally replaces 13 of 16 methods. The three
//     provider/enumeration methods remain owned by the existing ART stub.

#include <jni.h>

#include <dlfcn.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

namespace {

typedef int32_t UErrorCode;
typedef int8_t UBool;
typedef uint16_t UChar;

enum {
    U_ZERO_ERROR = 0,
    U_ILLEGAL_ARGUMENT_ERROR = 1,
    U_INVALID_CHAR_FOUND = 10,
    U_TRUNCATED_CHAR_FOUND = 11,
    U_ILLEGAL_CHAR_FOUND = 12,
    U_BUFFER_OVERFLOW_ERROR = 15,
    U_REGEX_INVALID_CAPTURE_GROUP_NAME = 0x10315,
    UREGEX_ERROR_ON_UNKNOWN_ESCAPES = 0x200,
};

enum {
    UCNV_UNASSIGNED = 0,
    UCNV_ILLEGAL = 1,
    UCNV_IRREGULAR = 2,
    UCNV_RESET = 3,
    UCNV_CLOSE = 4,
    UCNV_CLONE = 5,
};

enum {
    NATIVE_CONVERTER_REPORT = 0,
    NATIVE_CONVERTER_IGNORE = 1,
    NATIVE_CONVERTER_REPLACE = 2,
    MAX_REPLACEMENT_LENGTH = 32,
};

struct UParseError {
    int32_t line;
    int32_t offset;
    UChar pre_context[16];
    UChar post_context[16];
};

static_assert(sizeof(UErrorCode) == 4, "ICU UErrorCode ABI drift");
static_assert(sizeof(UBool) == 1, "ICU UBool ABI drift");
static_assert(sizeof(UChar) == 2, "ICU UChar ABI drift");
static_assert(sizeof(UParseError) == 72, "ICU UParseError ABI drift");
static_assert(offsetof(UParseError, line) == 0, "ICU UParseError line drift");
static_assert(offsetof(UParseError, offset) == 4,
              "ICU UParseError offset drift");
static_assert(offsetof(UParseError, pre_context) == 8,
              "ICU UParseError pre-context drift");
static_assert(offsetof(UParseError, post_context) == 40,
              "ICU UParseError post-context drift");
static_assert(sizeof(jlong) >= sizeof(void*), "JNI handle cannot hold pointer");

typedef void (*ToUCallback)(const void*, void*, const char*, int32_t,
                            int32_t, UErrorCode*);
typedef void (*FromUCallback)(const void*, void*, const UChar*, int32_t,
                              int32_t, int32_t, UErrorCode*);

struct IcuApi {
    void* uc_handle;
    void* i18n_handle;
    bool ready;
    char suffix[8];
    char uc_path[256];
    char i18n_path[256];

    void (*set_data_directory)(const char*);
    const char* (*error_name)(UErrorCode);
    void (*init)(UErrorCode*);

    void* (*ucnv_open)(const char*, UErrorCode*);
    void (*ucnv_close)(void*);
    void (*ucnv_to_unicode)(void*, UChar**, const UChar*, const char**,
                            const char*, int32_t*, UBool, UErrorCode*);
    void (*ucnv_from_unicode)(void*, char**, const char*, const UChar**,
                              const UChar*, int32_t*, UBool, UErrorCode*);
    int8_t (*ucnv_get_max_char_size)(const void*);
    int8_t (*ucnv_get_min_char_size)(const void*);
    void (*ucnv_reset_to_unicode)(void*);
    void (*ucnv_reset_from_unicode)(void*);
    void (*ucnv_get_invalid_chars)(const void*, char*, int8_t*, UErrorCode*);
    void (*ucnv_get_invalid_uchars)(const void*, UChar*, int8_t*, UErrorCode*);
    void (*ucnv_get_subst_chars)(const void*, char*, int8_t*, UErrorCode*);
    void (*ucnv_get_to_callback)(const void*, ToUCallback*, const void**);
    void (*ucnv_get_from_callback)(const void*, FromUCallback*, const void**);
    void (*ucnv_set_to_callback)(void*, ToUCallback, const void*,
                                 ToUCallback*, const void**, UErrorCode*);
    void (*ucnv_set_from_callback)(void*, FromUCallback, const void*,
                                   FromUCallback*, const void**, UErrorCode*);
    void (*ucnv_cb_to_write_uchars)(void*, const UChar*, int32_t, int32_t,
                                    UErrorCode*);
    void (*ucnv_cb_from_write_bytes)(void*, const char*, int32_t, int32_t,
                                     UErrorCode*);
    ToUCallback to_stop;
    ToUCallback to_skip;
    FromUCallback from_stop;
    FromUCallback from_skip;

    void* (*uregex_open)(const UChar*, int32_t, uint32_t, UParseError*,
                         UErrorCode*);
    void* (*uregex_clone)(const void*, UErrorCode*);
    void (*uregex_close)(void*);
    void (*uregex_set_text)(void*, const UChar*, int32_t, UErrorCode*);
    void (*uregex_set_region)(void*, int32_t, int32_t, UErrorCode*);
    UBool (*uregex_matches)(void*, int32_t, UErrorCode*);
    UBool (*uregex_looking_at)(void*, int32_t, UErrorCode*);
    UBool (*uregex_find)(void*, int32_t, UErrorCode*);
    UBool (*uregex_find_next)(void*, UErrorCode*);
    int32_t (*uregex_group_count)(void*, UErrorCode*);
    int32_t (*uregex_group_number_from_name)(void*, const UChar*, int32_t,
                                             UErrorCode*);
    int32_t (*uregex_start)(void*, int32_t, UErrorCode*);
    int32_t (*uregex_end)(void*, int32_t, UErrorCode*);
    void (*uregex_use_anchoring_bounds)(void*, UBool, UErrorCode*);
    void (*uregex_use_transparent_bounds)(void*, UBool, UErrorCode*);
    UBool (*uregex_hit_end)(const void*, UErrorCode*);
    UBool (*uregex_require_end)(const void*, UErrorCode*);
};

static IcuApi g_icu;

enum A3EntryIndex {
    ENTRY_PATTERN_COMPILE,
    ENTRY_PATTERN_OPEN_MATCHER,
    ENTRY_PATTERN_GROUP_NUMBER,
    ENTRY_PATTERN_FINALIZER,
    ENTRY_MATCHER_SET_INPUT,
    ENTRY_MATCHER_MATCHES,
    ENTRY_MATCHER_LOOKING_AT,
    ENTRY_MATCHER_FIND,
    ENTRY_MATCHER_FIND_NEXT,
    ENTRY_MATCHER_GROUP_COUNT,
    ENTRY_MATCHER_HIT_END,
    ENTRY_MATCHER_REQUIRE_END,
    ENTRY_MATCHER_ANCHORING_BOUNDS,
    ENTRY_MATCHER_TRANSPARENT_BOUNDS,
    ENTRY_MATCHER_FINALIZER,
    ENTRY_CONVERTER_OPEN,
    ENTRY_CONVERTER_CLOSE,
    ENTRY_CONVERTER_DECODE,
    ENTRY_CONVERTER_ENCODE,
    ENTRY_CONVERTER_MAX_BYTES,
    ENTRY_CONVERTER_AVERAGE_BYTES,
    ENTRY_CONVERTER_AVERAGE_CHARS,
    ENTRY_CONVERTER_RESET_TO_UNICODE,
    ENTRY_CONVERTER_RESET_FROM_UNICODE,
    ENTRY_CONVERTER_SUBSTITUTION,
    ENTRY_CONVERTER_FINALIZER,
    ENTRY_CONVERTER_DECODE_CALLBACK,
    ENTRY_CONVERTER_ENCODE_CALLBACK,
    ENTRY_COUNT,
};

enum A3LifecycleIndex {
    LIFECYCLE_PATTERN_OPEN,
    LIFECYCLE_PATTERN_CLOSE,
    LIFECYCLE_MATCHER_OPEN,
    LIFECYCLE_MATCHER_CLOSE,
    LIFECYCLE_CONVERTER_OPEN,
    LIFECYCLE_CONVERTER_CLOSE,
    LIFECYCLE_COUNT,
};

static_assert(ENTRY_COUNT == 28, "A3 provider marker count drift");
static_assert(LIFECYCLE_COUNT == 6, "A3 lifecycle counter count drift");

static int32_t g_entry_pid[ENTRY_COUNT];
static uint64_t g_lifecycle[LIFECYCLE_COUNT];

static void trace_entry_once(A3EntryIndex index, const char* method,
                             void* function) {
    const int32_t pid = static_cast<int32_t>(getpid());
    const int32_t previous = __atomic_exchange_n(
        &g_entry_pid[static_cast<size_t>(index)], pid, __ATOMIC_RELAXED);
    if (previous == pid) {
        return;
    }
    Dl_info info;
    memset(&info, 0, sizeof(info));
    const char* dso = "(unknown)";
    if (dladdr(function, &info) != 0 && info.dli_fname != nullptr) {
        dso = info.dli_fname;
    }
    fprintf(stderr,
            "[A3-ICU] ENTRY provider=A3 pid=%d method=%s fn=%p dso=%s\n",
            pid, method, function, dso);
}

static void trace_lifecycle(A3LifecycleIndex index, const char* kind,
                            const char* event) {
    uint64_t value = __atomic_add_fetch(
        &g_lifecycle[static_cast<size_t>(index)], UINT64_C(1),
        __ATOMIC_RELAXED);
    // Keep ordinary app logs bounded while still making early ownership and
    // long stress runs observable. The exact totals are available through
    // westlake_icu_snapshot_lifecycle below.
    if (value <= 4 || (value & (value - 1)) == 0) {
        fprintf(stderr,
                "[A3-ICU] LIFECYCLE pid=%d kind=%s event=%s count=%llu\n",
                static_cast<int>(getpid()), kind, event,
                static_cast<unsigned long long>(value));
    }
}

#define A3_TRACE(index, method, function)                                    \
    trace_entry_once((index), (method),                                      \
                     reinterpret_cast<void*>(&(function)))

static bool u_failure(UErrorCode status) {
    return status > U_ZERO_ERROR;
}

static void reset_icu_api(bool close_handles) {
    void* uc = g_icu.uc_handle;
    void* i18n = g_icu.i18n_handle;
    memset(&g_icu, 0, sizeof(g_icu));
    if (close_handles) {
        if (i18n != nullptr) {
            dlclose(i18n);
        }
        if (uc != nullptr) {
            dlclose(uc);
        }
    }
}

static bool copy_dl_path(void* symbol, char* out, size_t out_size) {
    Dl_info info;
    memset(&info, 0, sizeof(info));
    if (symbol == nullptr || out == nullptr || out_size == 0 ||
        dladdr(symbol, &info) == 0 || info.dli_fname == nullptr ||
        info.dli_fname[0] == '\0') {
        return false;
    }
    int written = snprintf(out, out_size, "%s", info.dli_fname);
    return written >= 0 && static_cast<size_t>(written) < out_size;
}

static void* versioned_symbol(void* handle, const char* base,
                              const char* suffix) {
    char name[128];
    int written = snprintf(name, sizeof(name), "%s%s", base, suffix);
    if (written < 0 || static_cast<size_t>(written) >= sizeof(name)) {
        return nullptr;
    }
    return dlsym(handle, name);
}

#define BIND_REQUIRED(handle, field, base, suffix)                           \
    do {                                                                      \
        g_icu.field = reinterpret_cast<decltype(g_icu.field)>(                \
            versioned_symbol((handle), (base), (suffix)));                    \
        if (g_icu.field == nullptr) {                                         \
            return false;                                                     \
        }                                                                     \
    } while (0)

static bool bind_symbol_cohort(const char* suffix) {
    BIND_REQUIRED(g_icu.uc_handle, set_data_directory, "u_setDataDirectory",
                  suffix);
    BIND_REQUIRED(g_icu.uc_handle, error_name, "u_errorName", suffix);
    BIND_REQUIRED(g_icu.uc_handle, init, "u_init", suffix);

    BIND_REQUIRED(g_icu.uc_handle, ucnv_open, "ucnv_open", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_close, "ucnv_close", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_to_unicode, "ucnv_toUnicode", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_from_unicode, "ucnv_fromUnicode",
                  suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_get_max_char_size,
                  "ucnv_getMaxCharSize", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_get_min_char_size,
                  "ucnv_getMinCharSize", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_reset_to_unicode,
                  "ucnv_resetToUnicode", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_reset_from_unicode,
                  "ucnv_resetFromUnicode", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_get_invalid_chars,
                  "ucnv_getInvalidChars", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_get_invalid_uchars,
                  "ucnv_getInvalidUChars", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_get_subst_chars,
                  "ucnv_getSubstChars", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_get_to_callback,
                  "ucnv_getToUCallBack", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_get_from_callback,
                  "ucnv_getFromUCallBack", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_set_to_callback,
                  "ucnv_setToUCallBack", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_set_from_callback,
                  "ucnv_setFromUCallBack", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_cb_to_write_uchars,
                  "ucnv_cbToUWriteUChars", suffix);
    BIND_REQUIRED(g_icu.uc_handle, ucnv_cb_from_write_bytes,
                  "ucnv_cbFromUWriteBytes", suffix);
    BIND_REQUIRED(g_icu.uc_handle, to_stop, "UCNV_TO_U_CALLBACK_STOP",
                  suffix);
    BIND_REQUIRED(g_icu.uc_handle, to_skip, "UCNV_TO_U_CALLBACK_SKIP",
                  suffix);
    BIND_REQUIRED(g_icu.uc_handle, from_stop, "UCNV_FROM_U_CALLBACK_STOP",
                  suffix);
    BIND_REQUIRED(g_icu.uc_handle, from_skip, "UCNV_FROM_U_CALLBACK_SKIP",
                  suffix);

    BIND_REQUIRED(g_icu.i18n_handle, uregex_open, "uregex_open", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_clone, "uregex_clone", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_close, "uregex_close", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_set_text, "uregex_setText",
                  suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_set_region, "uregex_setRegion",
                  suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_matches, "uregex_matches", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_looking_at, "uregex_lookingAt",
                  suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_find, "uregex_find", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_find_next, "uregex_findNext",
                  suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_group_count, "uregex_groupCount",
                  suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_group_number_from_name,
                  "uregex_groupNumberFromName", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_start, "uregex_start", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_end, "uregex_end", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_use_anchoring_bounds,
                  "uregex_useAnchoringBounds", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_use_transparent_bounds,
                  "uregex_useTransparentBounds", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_hit_end, "uregex_hitEnd", suffix);
    BIND_REQUIRED(g_icu.i18n_handle, uregex_require_end, "uregex_requireEnd",
                  suffix);
    return true;
}

#undef BIND_REQUIRED

static const char kExpectedUcPath[] =
    "/system/android/lib64/libicuuc.so";
static const char kExpectedI18nPath[] =
    "/system/android/lib64/libicui18n.so";
static const char kExpectedDataDirectory[] =
    "/system/android/etc/icu/";
static const char kExpectedDataFile[] =
    "/system/android/etc/icu/icudt72l.dat";
static const char kExpectedSuffix[] = "_72";

static int load_icu_cohort() {
    if (g_icu.ready) {
        return 0;
    }
    reset_icu_api(true);

    void* uc = dlopen(kExpectedUcPath, RTLD_NOW | RTLD_LOCAL);
    if (uc == nullptr) {
        const char* error = dlerror();
        fprintf(stderr, "[A3-ICU] ERROR dlopen exact uc=%s: %s\n",
                kExpectedUcPath, error != nullptr ? error : "(unknown)");
        return -1;
    }
    void* i18n = dlopen(kExpectedI18nPath, RTLD_NOW | RTLD_LOCAL);
    if (i18n == nullptr) {
        const char* error = dlerror();
        fprintf(stderr, "[A3-ICU] ERROR dlopen exact i18n=%s: %s\n",
                kExpectedI18nPath, error != nullptr ? error : "(unknown)");
        dlclose(uc);
        return -1;
    }

    g_icu.uc_handle = uc;
    g_icu.i18n_handle = i18n;
    if (!bind_symbol_cohort(kExpectedSuffix)) {
        fprintf(stderr,
                "[A3-ICU] ERROR incomplete exact ICU suffix cohort=%s\n",
                kExpectedSuffix);
        reset_icu_api(true);
        return -1;
    }

    snprintf(g_icu.suffix, sizeof(g_icu.suffix), "%s", kExpectedSuffix);
    if (!copy_dl_path(reinterpret_cast<void*>(g_icu.ucnv_open),
                      g_icu.uc_path, sizeof(g_icu.uc_path)) ||
        !copy_dl_path(reinterpret_cast<void*>(g_icu.uregex_open),
                      g_icu.i18n_path, sizeof(g_icu.i18n_path)) ||
        strcmp(g_icu.uc_path, kExpectedUcPath) != 0 ||
        strcmp(g_icu.i18n_path, kExpectedI18nPath) != 0) {
        fprintf(stderr,
                "[A3-ICU] ERROR dladdr path mismatch uc=%s i18n=%s\n",
                g_icu.uc_path, g_icu.i18n_path);
        reset_icu_api(true);
        return -1;
    }
    if (access(kExpectedDataFile, R_OK) != 0) {
        fprintf(stderr, "[A3-ICU] ERROR ICU data unreadable path=%s\n",
                kExpectedDataFile);
        reset_icu_api(true);
        return -1;
    }

    // This must happen before any converter or regex object is opened by this
    // bridge. u_init is the fail-close proof that the exact ICU72 cohort can
    // actually admit its on-disk data, not merely resolve its C symbols.
    g_icu.set_data_directory(kExpectedDataDirectory);
    UErrorCode status = U_ZERO_ERROR;
    g_icu.init(&status);
    if (u_failure(status)) {
        const char* name = g_icu.error_name(status);
        fprintf(stderr, "[A3-ICU] ERROR u_init%s failed: %s (%d)\n",
                kExpectedSuffix, name != nullptr ? name : "UErrorCode",
                status);
        reset_icu_api(true);
        return -1;
    }

    g_icu.ready = true;
    fprintf(stderr,
            "[A3-ICU] READY suffix=%s uc=%s i18n=%s data=%s "
            "dat=%s u_init=OK\n",
            g_icu.suffix, g_icu.uc_path, g_icu.i18n_path,
            kExpectedDataDirectory, kExpectedDataFile);
    return 0;
}

static const char* error_name(UErrorCode status) {
    if (g_icu.error_name != nullptr) {
        const char* name = g_icu.error_name(status);
        if (name != nullptr) {
            return name;
        }
    }
    return "UErrorCode";
}

static void throw_named(JNIEnv* env, const char* class_name,
                        const char* message) {
    if (env->ExceptionCheck()) {
        return;
    }
    jclass cls = env->FindClass(class_name);
    if (cls == nullptr) {
        return;
    }
    env->ThrowNew(cls, message);
    env->DeleteLocalRef(cls);
}

static void throw_icu(JNIEnv* env, const char* operation, UErrorCode status) {
    if (!u_failure(status)) {
        return;
    }
    char message[256];
    snprintf(message, sizeof(message), "%s failed: %s (%d)", operation,
             error_name(status), status);
    throw_named(env, "java/lang/RuntimeException", message);
}

static void throw_illegal_argument(JNIEnv* env, const char* message) {
    throw_named(env, "java/lang/IllegalArgumentException", message);
}

static void throw_null_pointer(JNIEnv* env, const char* message) {
    throw_named(env, "java/lang/NullPointerException", message);
}

static void throw_out_of_memory(JNIEnv* env, const char* message) {
    throw_named(env, "java/lang/OutOfMemoryError", message);
}

static void throw_pattern_syntax(JNIEnv* env, UErrorCode status,
                                 jstring pattern,
                                 const UParseError& parse_error) {
    if (env->ExceptionCheck()) {
        return;
    }
    jclass cls = env->FindClass("java/util/regex/PatternSyntaxException");
    if (cls == nullptr) {
        return;
    }
    jmethodID constructor = env->GetMethodID(
        cls, "<init>", "(Ljava/lang/String;Ljava/lang/String;I)V");
    if (constructor == nullptr) {
        env->DeleteLocalRef(cls);
        return;
    }
    char detail[192];
    snprintf(detail, sizeof(detail), "%s (%d)", error_name(status), status);
    jstring java_detail = env->NewStringUTF(detail);
    if (java_detail == nullptr) {
        env->DeleteLocalRef(cls);
        return;
    }
    jobject exception = env->NewObject(cls, constructor, java_detail, pattern,
                                       static_cast<jint>(parse_error.offset));
    if (exception != nullptr) {
        env->Throw(static_cast<jthrowable>(exception));
        env->DeleteLocalRef(exception);
    }
    env->DeleteLocalRef(java_detail);
    env->DeleteLocalRef(cls);
}

struct RegexMatcherState {
    void* regex;
    UChar* text;
    int32_t text_length;
};

static RegexMatcherState* matcher_state(JNIEnv* env, jlong address) {
    RegexMatcherState* state = reinterpret_cast<RegexMatcherState*>(
        static_cast<uintptr_t>(address));
    if (state == nullptr || state->regex == nullptr) {
        throw_illegal_argument(env, "invalid regex matcher handle");
        return nullptr;
    }
    return state;
}

static void pattern_free(void* address) {
    if (address != nullptr && g_icu.ready && g_icu.uregex_close != nullptr) {
        g_icu.uregex_close(address);
        trace_lifecycle(LIFECYCLE_PATTERN_CLOSE, "pattern", "close");
    }
}

static void matcher_free(void* address) {
    RegexMatcherState* state =
        reinterpret_cast<RegexMatcherState*>(address);
    if (state == nullptr) {
        return;
    }
    if (state->regex != nullptr && g_icu.ready &&
        g_icu.uregex_close != nullptr) {
        g_icu.uregex_close(state->regex);
        trace_lifecycle(LIFECYCLE_MATCHER_CLOSE, "matcher", "close");
    }
    free(state->text);
    free(state);
}

static jlong pattern_get_native_finalizer(JNIEnv*, jclass) {
    A3_TRACE(ENTRY_PATTERN_FINALIZER,
             "PatternNative.getNativeFinalizer", pattern_get_native_finalizer);
    return static_cast<jlong>(
        reinterpret_cast<uintptr_t>(&pattern_free));
}

static jlong matcher_get_native_finalizer(JNIEnv*, jclass) {
    A3_TRACE(ENTRY_MATCHER_FINALIZER,
             "MatcherNative.getNativeFinalizer", matcher_get_native_finalizer);
    return static_cast<jlong>(
        reinterpret_cast<uintptr_t>(&matcher_free));
}

static jlong pattern_compile(JNIEnv* env, jclass, jstring java_pattern,
                             jint java_flags) {
    A3_TRACE(ENTRY_PATTERN_COMPILE, "PatternNative.compileImpl",
             pattern_compile);
    if (java_pattern == nullptr) {
        throw_null_pointer(env, "pattern == null");
        return 0;
    }
    const jchar* pattern = env->GetStringChars(java_pattern, nullptr);
    if (pattern == nullptr) {
        return 0;
    }
    jsize pattern_length = env->GetStringLength(java_pattern);
    UParseError parse_error;
    memset(&parse_error, 0, sizeof(parse_error));
    parse_error.line = -1;
    parse_error.offset = -1;
    UErrorCode status = U_ZERO_ERROR;
    uint32_t flags = static_cast<uint32_t>(java_flags) |
                     static_cast<uint32_t>(UREGEX_ERROR_ON_UNKNOWN_ESCAPES);
    void* result = g_icu.uregex_open(
        reinterpret_cast<const UChar*>(pattern),
        static_cast<int32_t>(pattern_length), flags, &parse_error, &status);
    env->ReleaseStringChars(java_pattern, pattern);
    if (u_failure(status) || result == nullptr) {
        if (result != nullptr) {
            g_icu.uregex_close(result);
        }
        if (!u_failure(status)) {
            status = U_ILLEGAL_ARGUMENT_ERROR;
        }
        throw_pattern_syntax(env, status, java_pattern, parse_error);
        return 0;
    }
    trace_lifecycle(LIFECYCLE_PATTERN_OPEN, "pattern", "open");
    return static_cast<jlong>(reinterpret_cast<uintptr_t>(result));
}

static jlong pattern_open_matcher(JNIEnv* env, jclass, jlong address) {
    A3_TRACE(ENTRY_PATTERN_OPEN_MATCHER, "PatternNative.openMatcherImpl",
             pattern_open_matcher);
    void* pattern =
        reinterpret_cast<void*>(static_cast<uintptr_t>(address));
    if (pattern == nullptr) {
        throw_illegal_argument(env, "invalid regex pattern handle");
        return 0;
    }
    UErrorCode status = U_ZERO_ERROR;
    void* clone = g_icu.uregex_clone(pattern, &status);
    if (u_failure(status) || clone == nullptr) {
        if (clone != nullptr) {
            g_icu.uregex_close(clone);
        }
        if (!u_failure(status)) {
            status = U_ILLEGAL_ARGUMENT_ERROR;
        }
        throw_icu(env, "uregex_clone", status);
        return 0;
    }
    RegexMatcherState* state = static_cast<RegexMatcherState*>(
        calloc(1, sizeof(RegexMatcherState)));
    if (state == nullptr) {
        g_icu.uregex_close(clone);
        throw_out_of_memory(env, "regex matcher allocation failed");
        return 0;
    }
    state->regex = clone;
    trace_lifecycle(LIFECYCLE_MATCHER_OPEN, "matcher", "open");
    return static_cast<jlong>(reinterpret_cast<uintptr_t>(state));
}

static jint pattern_group_number(JNIEnv* env, jclass, jlong address,
                                 jstring java_name) {
    A3_TRACE(ENTRY_PATTERN_GROUP_NUMBER,
             "PatternNative.getMatchedGroupIndexImpl", pattern_group_number);
    void* pattern =
        reinterpret_cast<void*>(static_cast<uintptr_t>(address));
    if (pattern == nullptr) {
        throw_illegal_argument(env, "invalid regex pattern handle");
        return -1;
    }
    if (java_name == nullptr) {
        throw_null_pointer(env, "groupName == null");
        return -1;
    }
    const jchar* name = env->GetStringChars(java_name, nullptr);
    if (name == nullptr) {
        return -1;
    }
    jsize length = env->GetStringLength(java_name);
    UErrorCode status = U_ZERO_ERROR;
    int32_t result = g_icu.uregex_group_number_from_name(
        pattern, reinterpret_cast<const UChar*>(name),
        static_cast<int32_t>(length), &status);
    env->ReleaseStringChars(java_name, name);
    if (!u_failure(status)) {
        return static_cast<jint>(result);
    }
    if (status == U_REGEX_INVALID_CAPTURE_GROUP_NAME) {
        return -1;
    }
    throw_icu(env, "uregex_groupNumberFromName", status);
    return -1;
}

static bool update_offsets(JNIEnv* env, RegexMatcherState* state,
                           jintArray java_offsets) {
    if (java_offsets == nullptr) {
        throw_null_pointer(env, "offsets == null");
        return false;
    }
    UErrorCode status = U_ZERO_ERROR;
    int32_t group_count = g_icu.uregex_group_count(state->regex, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_groupCount", status);
        return false;
    }
    int64_t required = (static_cast<int64_t>(group_count) + 1) * 2;
    if (required > env->GetArrayLength(java_offsets)) {
        throw_illegal_argument(env, "offset array is too small");
        return false;
    }
    jint* offsets = env->GetIntArrayElements(java_offsets, nullptr);
    if (offsets == nullptr) {
        return false;
    }
    for (int32_t group = 0; group <= group_count; ++group) {
        status = U_ZERO_ERROR;
        int32_t start = g_icu.uregex_start(state->regex, group, &status);
        if (u_failure(status)) {
            env->ReleaseIntArrayElements(java_offsets, offsets, JNI_ABORT);
            throw_icu(env, "uregex_start", status);
            return false;
        }
        status = U_ZERO_ERROR;
        int32_t end = g_icu.uregex_end(state->regex, group, &status);
        if (u_failure(status)) {
            env->ReleaseIntArrayElements(java_offsets, offsets, JNI_ABORT);
            throw_icu(env, "uregex_end", status);
            return false;
        }
        offsets[group * 2] = static_cast<jint>(start);
        offsets[group * 2 + 1] = static_cast<jint>(end);
    }
    env->ReleaseIntArrayElements(java_offsets, offsets, 0);
    return !env->ExceptionCheck();
}

static void matcher_set_input(JNIEnv* env, jclass, jlong address,
                              jstring java_text, jint start, jint end) {
    A3_TRACE(ENTRY_MATCHER_SET_INPUT, "MatcherNative.setInputImpl",
             matcher_set_input);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return;
    }
    if (java_text == nullptr) {
        throw_null_pointer(env, "input == null");
        return;
    }
    jsize length = env->GetStringLength(java_text);
    if (start < 0 || end < start || end > length) {
        throw_illegal_argument(env, "invalid regex input region");
        return;
    }
    const jchar* chars = env->GetStringChars(java_text, nullptr);
    if (chars == nullptr) {
        return;
    }
    size_t allocation =
        (static_cast<size_t>(length) + 1) * sizeof(UChar);
    UChar* copy = static_cast<UChar*>(malloc(allocation));
    if (copy == nullptr) {
        env->ReleaseStringChars(java_text, chars);
        throw_out_of_memory(env, "regex input allocation failed");
        return;
    }
    if (length > 0) {
        memcpy(copy, chars, static_cast<size_t>(length) * sizeof(UChar));
    }
    copy[length] = 0;
    env->ReleaseStringChars(java_text, chars);

    UErrorCode status = U_ZERO_ERROR;
    g_icu.uregex_set_text(state->regex, copy, static_cast<int32_t>(length),
                          &status);
    if (u_failure(status)) {
        free(copy);
        throw_icu(env, "uregex_setText", status);
        return;
    }

    // uregex_setText retains the pointer. Publish the new owned storage before
    // the mandatory region call so even an exceptional region failure cannot
    // leave ICU pointing at freed memory.
    UChar* old_text = state->text;
    state->text = copy;
    state->text_length = static_cast<int32_t>(length);
    free(old_text);

    status = U_ZERO_ERROR;
    g_icu.uregex_set_region(state->regex, static_cast<int32_t>(start),
                            static_cast<int32_t>(end), &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_setRegion", status);
    }
}

static jboolean matcher_matches(JNIEnv* env, jclass, jlong address,
                                jintArray offsets) {
    A3_TRACE(ENTRY_MATCHER_MATCHES, "MatcherNative.matchesImpl",
             matcher_matches);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return JNI_FALSE;
    }
    UErrorCode status = U_ZERO_ERROR;
    UBool result = g_icu.uregex_matches(state->regex, -1, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_matches", status);
        return JNI_FALSE;
    }
    if (result != 0 && !update_offsets(env, state, offsets)) {
        return JNI_FALSE;
    }
    return result != 0 ? JNI_TRUE : JNI_FALSE;
}

static jboolean matcher_looking_at(JNIEnv* env, jclass, jlong address,
                                   jintArray offsets) {
    A3_TRACE(ENTRY_MATCHER_LOOKING_AT, "MatcherNative.lookingAtImpl",
             matcher_looking_at);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return JNI_FALSE;
    }
    UErrorCode status = U_ZERO_ERROR;
    UBool result = g_icu.uregex_looking_at(state->regex, -1, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_lookingAt", status);
        return JNI_FALSE;
    }
    if (result != 0 && !update_offsets(env, state, offsets)) {
        return JNI_FALSE;
    }
    return result != 0 ? JNI_TRUE : JNI_FALSE;
}

static jboolean matcher_find(JNIEnv* env, jclass, jlong address,
                             jint start_index, jintArray offsets) {
    A3_TRACE(ENTRY_MATCHER_FIND, "MatcherNative.findImpl", matcher_find);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return JNI_FALSE;
    }
    UErrorCode status = U_ZERO_ERROR;
    UBool result = g_icu.uregex_find(
        state->regex, static_cast<int32_t>(start_index), &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_find", status);
        return JNI_FALSE;
    }
    if (result != 0 && !update_offsets(env, state, offsets)) {
        return JNI_FALSE;
    }
    return result != 0 ? JNI_TRUE : JNI_FALSE;
}

static jboolean matcher_find_next(JNIEnv* env, jclass, jlong address,
                                  jintArray offsets) {
    A3_TRACE(ENTRY_MATCHER_FIND_NEXT, "MatcherNative.findNextImpl",
             matcher_find_next);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return JNI_FALSE;
    }
    UErrorCode status = U_ZERO_ERROR;
    UBool result = g_icu.uregex_find_next(state->regex, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_findNext", status);
        return JNI_FALSE;
    }
    if (result != 0 && !update_offsets(env, state, offsets)) {
        return JNI_FALSE;
    }
    return result != 0 ? JNI_TRUE : JNI_FALSE;
}

static jint matcher_group_count(JNIEnv* env, jclass, jlong address) {
    A3_TRACE(ENTRY_MATCHER_GROUP_COUNT, "MatcherNative.groupCountImpl",
             matcher_group_count);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return 0;
    }
    UErrorCode status = U_ZERO_ERROR;
    int32_t result = g_icu.uregex_group_count(state->regex, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_groupCount", status);
        return 0;
    }
    return static_cast<jint>(result);
}

static jboolean matcher_hit_end(JNIEnv* env, jclass, jlong address) {
    A3_TRACE(ENTRY_MATCHER_HIT_END, "MatcherNative.hitEndImpl",
             matcher_hit_end);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return JNI_FALSE;
    }
    UErrorCode status = U_ZERO_ERROR;
    UBool result = g_icu.uregex_hit_end(state->regex, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_hitEnd", status);
        return JNI_FALSE;
    }
    return result != 0 ? JNI_TRUE : JNI_FALSE;
}

static jboolean matcher_require_end(JNIEnv* env, jclass, jlong address) {
    A3_TRACE(ENTRY_MATCHER_REQUIRE_END, "MatcherNative.requireEndImpl",
             matcher_require_end);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return JNI_FALSE;
    }
    UErrorCode status = U_ZERO_ERROR;
    UBool result = g_icu.uregex_require_end(state->regex, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_requireEnd", status);
        return JNI_FALSE;
    }
    return result != 0 ? JNI_TRUE : JNI_FALSE;
}

static void matcher_use_anchoring_bounds(JNIEnv* env, jclass, jlong address,
                                         jboolean value) {
    A3_TRACE(ENTRY_MATCHER_ANCHORING_BOUNDS,
             "MatcherNative.useAnchoringBoundsImpl",
             matcher_use_anchoring_bounds);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return;
    }
    UErrorCode status = U_ZERO_ERROR;
    g_icu.uregex_use_anchoring_bounds(
        state->regex, value == JNI_TRUE ? 1 : 0, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_useAnchoringBounds", status);
    }
}

static void matcher_use_transparent_bounds(JNIEnv* env, jclass, jlong address,
                                           jboolean value) {
    A3_TRACE(ENTRY_MATCHER_TRANSPARENT_BOUNDS,
             "MatcherNative.useTransparentBoundsImpl",
             matcher_use_transparent_bounds);
    RegexMatcherState* state = matcher_state(env, address);
    if (state == nullptr) {
        return;
    }
    UErrorCode status = U_ZERO_ERROR;
    g_icu.uregex_use_transparent_bounds(
        state->regex, value == JNI_TRUE ? 1 : 0, &status);
    if (u_failure(status)) {
        throw_icu(env, "uregex_useTransparentBounds", status);
    }
}

struct DecoderCallbackContext {
    UChar replacement_chars[MAX_REPLACEMENT_LENGTH];
    size_t replacement_count;
    ToUCallback on_unmappable_input;
    ToUCallback on_malformed_input;
};

struct EncoderCallbackContext {
    char replacement_bytes[MAX_REPLACEMENT_LENGTH];
    size_t replacement_count;
    FromUCallback on_unmappable_input;
    FromUCallback on_malformed_input;
};

static void decoder_ignore_callback(const void*, void*, const char*, int32_t,
                                    int32_t, UErrorCode* status) {
    if (status != nullptr) {
        *status = U_ZERO_ERROR;
    }
}

static void decoder_replace_callback(const void* raw_context, void* args,
                                     const char*, int32_t, int32_t,
                                     UErrorCode* status) {
    const DecoderCallbackContext* context =
        static_cast<const DecoderCallbackContext*>(raw_context);
    if (context == nullptr || status == nullptr) {
        return;
    }
    *status = U_ZERO_ERROR;
    g_icu.ucnv_cb_to_write_uchars(
        args, context->replacement_chars,
        static_cast<int32_t>(context->replacement_count), 0, status);
}

static void encoder_replace_callback(const void* raw_context, void* args,
                                     const UChar*, int32_t, int32_t, int32_t,
                                     UErrorCode* status) {
    const EncoderCallbackContext* context =
        static_cast<const EncoderCallbackContext*>(raw_context);
    if (context == nullptr || status == nullptr) {
        return;
    }
    *status = U_ZERO_ERROR;
    g_icu.ucnv_cb_from_write_bytes(
        args, context->replacement_bytes,
        static_cast<int32_t>(context->replacement_count), 0, status);
}

static void charset_decoder_callback(const void* raw_context, void* args,
                                     const char* code_units, int32_t length,
                                     int32_t reason, UErrorCode* status) {
    const DecoderCallbackContext* context =
        static_cast<const DecoderCallbackContext*>(raw_context);
    if (context == nullptr || status == nullptr) {
        return;
    }
    switch (reason) {
        case UCNV_UNASSIGNED:
            context->on_unmappable_input(context, args, code_units, length,
                                         reason, status);
            return;
        case UCNV_ILLEGAL:
        case UCNV_IRREGULAR:
            context->on_malformed_input(context, args, code_units, length,
                                        reason, status);
            return;
        case UCNV_CLOSE:
            free(const_cast<void*>(raw_context));
            return;
        case UCNV_RESET:
        case UCNV_CLONE:
        default:
            *status = U_ILLEGAL_ARGUMENT_ERROR;
            return;
    }
}

static void charset_encoder_callback(const void* raw_context, void* args,
                                     const UChar* code_units, int32_t length,
                                     int32_t code_point, int32_t reason,
                                     UErrorCode* status) {
    const EncoderCallbackContext* context =
        static_cast<const EncoderCallbackContext*>(raw_context);
    if (context == nullptr || status == nullptr) {
        return;
    }
    switch (reason) {
        case UCNV_UNASSIGNED:
            context->on_unmappable_input(context, args, code_units, length,
                                         code_point, reason, status);
            return;
        case UCNV_ILLEGAL:
        case UCNV_IRREGULAR:
            context->on_malformed_input(context, args, code_units, length,
                                        code_point, reason, status);
            return;
        case UCNV_CLOSE:
            free(const_cast<void*>(raw_context));
            return;
        case UCNV_RESET:
        case UCNV_CLONE:
        default:
            *status = U_ILLEGAL_ARGUMENT_ERROR;
            return;
    }
}

static ToUCallback to_callback_for_mode(JNIEnv* env, jint mode) {
    switch (mode) {
        case NATIVE_CONVERTER_REPORT:
            return g_icu.to_stop;
        case NATIVE_CONVERTER_IGNORE:
            return decoder_ignore_callback;
        case NATIVE_CONVERTER_REPLACE:
            return decoder_replace_callback;
        default:
            throw_illegal_argument(env, "invalid decoder callback mode");
            return nullptr;
    }
}

static FromUCallback from_callback_for_mode(JNIEnv* env, jint mode) {
    switch (mode) {
        case NATIVE_CONVERTER_REPORT:
            return g_icu.from_stop;
        case NATIVE_CONVERTER_IGNORE:
            return g_icu.from_skip;
        case NATIVE_CONVERTER_REPLACE:
            return encoder_replace_callback;
        default:
            throw_illegal_argument(env, "invalid encoder callback mode");
            return nullptr;
    }
}

static void* converter_handle(JNIEnv* env, jlong address) {
    void* converter =
        reinterpret_cast<void*>(static_cast<uintptr_t>(address));
    if (converter == nullptr) {
        throw_illegal_argument(env, "invalid NativeConverter handle");
    }
    return converter;
}

static jlong converter_open(JNIEnv* env, jclass, jstring java_name) {
    A3_TRACE(ENTRY_CONVERTER_OPEN, "NativeConverter.openConverter",
             converter_open);
    if (java_name == nullptr) {
        throw_null_pointer(env, "converterName == null");
        return 0;
    }
    const char* name = env->GetStringUTFChars(java_name, nullptr);
    if (name == nullptr) {
        return 0;
    }
    // Match Android 11's NativeConverter contract: the Java UTF-16 charset is
    // big-endian with a BOM, while ICU's bare "UTF-16" converter is
    // platform-endian. charsetForName remains with the ART provider and hands
    // this method the unversioned canonical name, so normalize it here.
    const char* icu_name =
        strcmp(name, "UTF-16") == 0 ? "UTF-16,version=2" : name;
    UErrorCode status = U_ZERO_ERROR;
    void* converter = g_icu.ucnv_open(icu_name, &status);
    env->ReleaseStringUTFChars(java_name, name);
    if (u_failure(status) || converter == nullptr) {
        if (converter != nullptr) {
            g_icu.ucnv_close(converter);
        }
        if (!u_failure(status)) {
            status = U_ILLEGAL_ARGUMENT_ERROR;
        }
        throw_icu(env, "ucnv_open", status);
        return 0;
    }
    trace_lifecycle(LIFECYCLE_CONVERTER_OPEN, "converter", "open");
    return static_cast<jlong>(reinterpret_cast<uintptr_t>(converter));
}

static void converter_close(JNIEnv*, jclass, jlong address) {
    A3_TRACE(ENTRY_CONVERTER_CLOSE, "NativeConverter.closeConverter",
             converter_close);
    void* converter =
        reinterpret_cast<void*>(static_cast<uintptr_t>(address));
    if (converter != nullptr) {
        g_icu.ucnv_close(converter);
        trace_lifecycle(LIFECYCLE_CONVERTER_CLOSE, "converter", "close");
    }
}

static void converter_finalizer(void* converter) {
    if (converter != nullptr && g_icu.ready && g_icu.ucnv_close != nullptr) {
        g_icu.ucnv_close(converter);
        trace_lifecycle(LIFECYCLE_CONVERTER_CLOSE, "converter", "finalize");
    }
}

static jlong converter_get_native_finalizer(JNIEnv*, jclass) {
    A3_TRACE(ENTRY_CONVERTER_FINALIZER,
             "NativeConverter.getNativeFinalizer",
             converter_get_native_finalizer);
    return static_cast<jlong>(
        reinterpret_cast<uintptr_t>(&converter_finalizer));
}

static bool should_codec_throw(jboolean flush, UErrorCode error) {
    if (flush == JNI_TRUE) {
        return error != U_BUFFER_OVERFLOW_ERROR &&
               error != U_TRUNCATED_CHAR_FOUND;
    }
    return error != U_BUFFER_OVERFLOW_ERROR &&
           error != U_INVALID_CHAR_FOUND &&
           error != U_ILLEGAL_CHAR_FOUND;
}

static bool validate_codec_arrays(JNIEnv* env, jarray source, jint source_end,
                                  jarray target, jint target_end,
                                  jintArray data, jint* source_offset,
                                  jint* target_offset) {
    if (source == nullptr || target == nullptr || data == nullptr) {
        throw_null_pointer(env, "codec buffer/data array == null");
        return false;
    }
    if (env->GetArrayLength(data) < 3) {
        throw_illegal_argument(env, "codec data array length < 3");
        return false;
    }
    jint initial[3] = {0, 0, 0};
    env->GetIntArrayRegion(data, 0, 3, initial);
    if (env->ExceptionCheck()) {
        return false;
    }
    jsize source_length = env->GetArrayLength(source);
    jsize target_length = env->GetArrayLength(target);
    if (source_end < 0 || source_end > source_length ||
        target_end < 0 || target_end > target_length ||
        initial[0] < 0 || initial[0] > source_end ||
        initial[1] < 0 || initial[1] > target_end) {
        throw_illegal_argument(env, "invalid codec buffer bounds");
        return false;
    }
    *source_offset = initial[0];
    *target_offset = initial[1];
    return true;
}

static void ensure_codec_access_exception(JNIEnv* env,
                                          const char* array_name) {
    if (!env->ExceptionCheck()) {
        char message[128];
        snprintf(message, sizeof(message), "cannot access codec %s array",
                 array_name);
        throw_illegal_argument(env, message);
    }
}

static jint converter_encode(JNIEnv* env, jclass, jlong address,
                             jcharArray source, jint source_end,
                             jbyteArray target, jint target_end,
                             jintArray data, jboolean flush) {
    A3_TRACE(ENTRY_CONVERTER_ENCODE, "NativeConverter.encode",
             converter_encode);
    void* converter = converter_handle(env, address);
    if (converter == nullptr) {
        return U_ILLEGAL_ARGUMENT_ERROR;
    }
    jint source_offset = 0;
    jint target_offset = 0;
    if (!validate_codec_arrays(env, source, source_end, target, target_end,
                               data, &source_offset, &target_offset)) {
        return U_ILLEGAL_ARGUMENT_ERROR;
    }

    jchar* source_base = env->GetCharArrayElements(source, nullptr);
    if (source_base == nullptr) {
        ensure_codec_access_exception(env, "source");
        return U_ILLEGAL_ARGUMENT_ERROR;
    }
    jbyte* target_base = env->GetByteArrayElements(target, nullptr);
    if (target_base == nullptr) {
        env->ReleaseCharArrayElements(source, source_base, JNI_ABORT);
        ensure_codec_access_exception(env, "target");
        return U_ILLEGAL_ARGUMENT_ERROR;
    }
    jint* values = env->GetIntArrayElements(data, nullptr);
    if (values == nullptr) {
        env->ReleaseByteArrayElements(target, target_base, 0);
        env->ReleaseCharArrayElements(source, source_base, JNI_ABORT);
        ensure_codec_access_exception(env, "data");
        return U_ILLEGAL_ARGUMENT_ERROR;
    }

    const UChar* source_cursor =
        reinterpret_cast<const UChar*>(source_base) + source_offset;
    const UChar* source_limit =
        reinterpret_cast<const UChar*>(source_base) + source_end;
    char* target_cursor =
        reinterpret_cast<char*>(target_base) + target_offset;
    const char* target_limit =
        reinterpret_cast<const char*>(target_base) + target_end;
    UErrorCode status = U_ZERO_ERROR;
    g_icu.ucnv_from_unicode(
        converter, &target_cursor, target_limit, &source_cursor, source_limit,
        nullptr, flush == JNI_TRUE ? 1 : 0, &status);

    // Android 11's CharsetEncoderICU consumes data[0] as a delta but passes
    // data[1] to ByteBuffer.position(), so output must be an absolute array
    // index (including a non-zero arrayOffset).
    values[0] = static_cast<jint>(
        source_cursor - reinterpret_cast<const UChar*>(source_base) -
        source_offset);
    values[1] = static_cast<jint>(
        target_cursor - reinterpret_cast<char*>(target_base));

    if (status == U_ILLEGAL_CHAR_FOUND ||
        status == U_INVALID_CHAR_FOUND ||
        status == U_TRUNCATED_CHAR_FOUND) {
        UChar invalid[32];
        int8_t invalid_count = 32;
        UErrorCode minor = U_ZERO_ERROR;
        g_icu.ucnv_get_invalid_uchars(converter, invalid, &invalid_count,
                                      &minor);
        if (!u_failure(minor)) {
            values[2] = invalid_count;
        }
    }

    env->ReleaseIntArrayElements(data, values, 0);
    env->ReleaseByteArrayElements(target, target_base, 0);
    env->ReleaseCharArrayElements(source, source_base, JNI_ABORT);
    if (u_failure(status) && should_codec_throw(flush, status)) {
        throw_icu(env, "ucnv_fromUnicode", status);
    }
    return status;
}

static jint converter_decode(JNIEnv* env, jclass, jlong address,
                             jbyteArray source, jint source_end,
                             jcharArray target, jint target_end,
                             jintArray data, jboolean flush) {
    A3_TRACE(ENTRY_CONVERTER_DECODE, "NativeConverter.decode",
             converter_decode);
    void* converter = converter_handle(env, address);
    if (converter == nullptr) {
        return U_ILLEGAL_ARGUMENT_ERROR;
    }
    jint source_offset = 0;
    jint target_offset = 0;
    if (!validate_codec_arrays(env, source, source_end, target, target_end,
                               data, &source_offset, &target_offset)) {
        return U_ILLEGAL_ARGUMENT_ERROR;
    }

    jbyte* source_base = env->GetByteArrayElements(source, nullptr);
    if (source_base == nullptr) {
        ensure_codec_access_exception(env, "source");
        return U_ILLEGAL_ARGUMENT_ERROR;
    }
    jchar* target_base = env->GetCharArrayElements(target, nullptr);
    if (target_base == nullptr) {
        env->ReleaseByteArrayElements(source, source_base, JNI_ABORT);
        ensure_codec_access_exception(env, "target");
        return U_ILLEGAL_ARGUMENT_ERROR;
    }
    jint* values = env->GetIntArrayElements(data, nullptr);
    if (values == nullptr) {
        env->ReleaseCharArrayElements(target, target_base, 0);
        env->ReleaseByteArrayElements(source, source_base, JNI_ABORT);
        ensure_codec_access_exception(env, "data");
        return U_ILLEGAL_ARGUMENT_ERROR;
    }

    const char* source_cursor =
        reinterpret_cast<const char*>(source_base) + source_offset;
    const char* source_limit =
        reinterpret_cast<const char*>(source_base) + source_end;
    UChar* target_cursor =
        reinterpret_cast<UChar*>(target_base) + target_offset;
    const UChar* target_limit =
        reinterpret_cast<const UChar*>(target_base) + target_end;
    UErrorCode status = U_ZERO_ERROR;
    g_icu.ucnv_to_unicode(
        converter, &target_cursor, target_limit, &source_cursor, source_limit,
        nullptr, flush == JNI_TRUE ? 1 : 0, &status);

    // Android 11's CharsetDecoderICU consumes both positions as deltas.
    values[0] = static_cast<jint>(
        source_cursor - reinterpret_cast<const char*>(source_base) -
        source_offset);
    values[1] = static_cast<jint>(
        target_cursor - reinterpret_cast<UChar*>(target_base) -
        target_offset);

    if (status == U_ILLEGAL_CHAR_FOUND ||
        status == U_INVALID_CHAR_FOUND ||
        status == U_TRUNCATED_CHAR_FOUND) {
        char invalid[32];
        int8_t invalid_count = 32;
        UErrorCode minor = U_ZERO_ERROR;
        g_icu.ucnv_get_invalid_chars(converter, invalid, &invalid_count,
                                     &minor);
        if (!u_failure(minor)) {
            values[2] = invalid_count;
        }
    }

    env->ReleaseIntArrayElements(data, values, 0);
    env->ReleaseCharArrayElements(target, target_base, 0);
    env->ReleaseByteArrayElements(source, source_base, JNI_ABORT);
    if (u_failure(status) && should_codec_throw(flush, status)) {
        throw_icu(env, "ucnv_toUnicode", status);
    }
    return status;
}

static jint converter_get_max_bytes(JNIEnv* env, jclass, jlong address) {
    A3_TRACE(ENTRY_CONVERTER_MAX_BYTES,
             "NativeConverter.getMaxBytesPerChar",
             converter_get_max_bytes);
    void* converter = converter_handle(env, address);
    return converter != nullptr
               ? static_cast<jint>(g_icu.ucnv_get_max_char_size(converter))
               : -1;
}

static jfloat converter_get_average_bytes(JNIEnv* env, jclass,
                                          jlong address) {
    A3_TRACE(ENTRY_CONVERTER_AVERAGE_BYTES,
             "NativeConverter.getAveBytesPerChar",
             converter_get_average_bytes);
    void* converter = converter_handle(env, address);
    if (converter == nullptr) {
        return -1.0f;
    }
    int max_size = g_icu.ucnv_get_max_char_size(converter);
    int min_size = g_icu.ucnv_get_min_char_size(converter);
    return static_cast<jfloat>((max_size + min_size) / 2.0);
}

static jfloat converter_get_average_chars(JNIEnv* env, jclass,
                                          jlong address) {
    A3_TRACE(ENTRY_CONVERTER_AVERAGE_CHARS,
             "NativeConverter.getAveCharsPerByte",
             converter_get_average_chars);
    void* converter = converter_handle(env, address);
    if (converter == nullptr) {
        return -1.0f;
    }
    int max_size = g_icu.ucnv_get_max_char_size(converter);
    if (max_size <= 0) {
        throw_illegal_argument(env, "invalid converter maximum char size");
        return -1.0f;
    }
    return 1.0f / static_cast<jfloat>(max_size);
}

static void converter_reset_to_unicode(JNIEnv* env, jclass, jlong address) {
    A3_TRACE(ENTRY_CONVERTER_RESET_TO_UNICODE,
             "NativeConverter.resetByteToChar",
             converter_reset_to_unicode);
    void* converter = converter_handle(env, address);
    if (converter != nullptr) {
        g_icu.ucnv_reset_to_unicode(converter);
    }
}

static void converter_reset_from_unicode(JNIEnv* env, jclass, jlong address) {
    A3_TRACE(ENTRY_CONVERTER_RESET_FROM_UNICODE,
             "NativeConverter.resetCharToByte",
             converter_reset_from_unicode);
    void* converter = converter_handle(env, address);
    if (converter != nullptr) {
        g_icu.ucnv_reset_from_unicode(converter);
    }
}

static jbyteArray converter_get_substitution_bytes(JNIEnv* env, jclass,
                                                   jlong address) {
    A3_TRACE(ENTRY_CONVERTER_SUBSTITUTION,
             "NativeConverter.getSubstitutionBytes",
             converter_get_substitution_bytes);
    void* converter = converter_handle(env, address);
    if (converter == nullptr) {
        return nullptr;
    }
    char replacement[MAX_REPLACEMENT_LENGTH];
    int8_t length = MAX_REPLACEMENT_LENGTH;
    UErrorCode status = U_ZERO_ERROR;
    g_icu.ucnv_get_subst_chars(converter, replacement, &length, &status);
    if (u_failure(status) || length < 0) {
        return env->NewByteArray(0);
    }
    jbyteArray result = env->NewByteArray(length);
    if (result == nullptr) {
        return nullptr;
    }
    env->SetByteArrayRegion(
        result, 0, length, reinterpret_cast<const jbyte*>(replacement));
    return result;
}

static void converter_set_decode_callback(JNIEnv* env, jclass, jlong address,
                                          jint malformed_mode,
                                          jint unmappable_mode,
                                          jstring java_replacement) {
    A3_TRACE(ENTRY_CONVERTER_DECODE_CALLBACK,
             "NativeConverter.setCallbackDecode",
             converter_set_decode_callback);
    void* converter = converter_handle(env, address);
    if (converter == nullptr) {
        return;
    }
    ToUCallback malformed = to_callback_for_mode(env, malformed_mode);
    ToUCallback unmappable = to_callback_for_mode(env, unmappable_mode);
    if (env->ExceptionCheck() || malformed == nullptr || unmappable == nullptr) {
        return;
    }
    if (java_replacement == nullptr) {
        throw_illegal_argument(env, "decoder replacement == null");
        return;
    }
    jsize replacement_length = env->GetStringLength(java_replacement);
    if (replacement_length < 0 ||
        replacement_length > MAX_REPLACEMENT_LENGTH) {
        throw_illegal_argument(env, "decoder replacement is too long");
        return;
    }
    const jchar* replacement =
        env->GetStringChars(java_replacement, nullptr);
    if (replacement == nullptr) {
        return;
    }

    ToUCallback old_callback = nullptr;
    const void* old_context = nullptr;
    g_icu.ucnv_get_to_callback(converter, &old_callback, &old_context);
    bool allocated = old_callback != charset_decoder_callback ||
                     old_context == nullptr;
    DecoderCallbackContext* context =
        allocated ? static_cast<DecoderCallbackContext*>(
                        calloc(1, sizeof(DecoderCallbackContext)))
                  : const_cast<DecoderCallbackContext*>(
                        static_cast<const DecoderCallbackContext*>(
                            old_context));
    if (context == nullptr) {
        env->ReleaseStringChars(java_replacement, replacement);
        throw_out_of_memory(env, "decoder callback allocation failed");
        return;
    }
    context->on_malformed_input = malformed;
    context->on_unmappable_input = unmappable;
    context->replacement_count = static_cast<size_t>(replacement_length);
    if (replacement_length > 0) {
        memcpy(context->replacement_chars, replacement,
               static_cast<size_t>(replacement_length) * sizeof(UChar));
    }
    env->ReleaseStringChars(java_replacement, replacement);

    UErrorCode status = U_ZERO_ERROR;
    g_icu.ucnv_set_to_callback(converter, charset_decoder_callback, context,
                               nullptr, nullptr, &status);
    if (u_failure(status)) {
        if (allocated) {
            free(context);
        }
        throw_icu(env, "ucnv_setToUCallBack", status);
    }
}

static void converter_set_encode_callback(JNIEnv* env, jclass, jlong address,
                                          jint malformed_mode,
                                          jint unmappable_mode,
                                          jbyteArray java_replacement) {
    A3_TRACE(ENTRY_CONVERTER_ENCODE_CALLBACK,
             "NativeConverter.setCallbackEncode",
             converter_set_encode_callback);
    void* converter = converter_handle(env, address);
    if (converter == nullptr) {
        return;
    }
    FromUCallback malformed = from_callback_for_mode(env, malformed_mode);
    FromUCallback unmappable = from_callback_for_mode(env, unmappable_mode);
    if (env->ExceptionCheck() || malformed == nullptr || unmappable == nullptr) {
        return;
    }
    if (java_replacement == nullptr) {
        throw_illegal_argument(env, "encoder replacement == null");
        return;
    }
    jsize replacement_length = env->GetArrayLength(java_replacement);
    if (replacement_length < 0 ||
        replacement_length > MAX_REPLACEMENT_LENGTH) {
        throw_illegal_argument(env, "encoder replacement is too long");
        return;
    }
    jbyte* replacement =
        env->GetByteArrayElements(java_replacement, nullptr);
    if (replacement == nullptr) {
        return;
    }

    FromUCallback old_callback = nullptr;
    const void* old_context = nullptr;
    g_icu.ucnv_get_from_callback(converter, &old_callback, &old_context);
    bool allocated = old_callback != charset_encoder_callback ||
                     old_context == nullptr;
    EncoderCallbackContext* context =
        allocated ? static_cast<EncoderCallbackContext*>(
                        calloc(1, sizeof(EncoderCallbackContext)))
                  : const_cast<EncoderCallbackContext*>(
                        static_cast<const EncoderCallbackContext*>(
                            old_context));
    if (context == nullptr) {
        env->ReleaseByteArrayElements(java_replacement, replacement,
                                      JNI_ABORT);
        throw_out_of_memory(env, "encoder callback allocation failed");
        return;
    }
    context->on_malformed_input = malformed;
    context->on_unmappable_input = unmappable;
    context->replacement_count = static_cast<size_t>(replacement_length);
    if (replacement_length > 0) {
        memcpy(context->replacement_bytes, replacement,
               static_cast<size_t>(replacement_length));
    }
    env->ReleaseByteArrayElements(java_replacement, replacement, JNI_ABORT);

    UErrorCode status = U_ZERO_ERROR;
    g_icu.ucnv_set_from_callback(converter, charset_encoder_callback, context,
                                 nullptr, nullptr, &status);
    if (u_failure(status)) {
        if (allocated) {
            free(context);
        }
        throw_icu(env, "ucnv_setFromUCallBack", status);
    }
}

#define A3_NATIVE(name, signature, function)                                  \
    {const_cast<char*>(name), const_cast<char*>(signature),                   \
     reinterpret_cast<void*>(function)}

static JNINativeMethod kPatternMethods[] = {
    A3_NATIVE("compileImpl", "(Ljava/lang/String;I)J", pattern_compile),
    A3_NATIVE("openMatcherImpl", "(J)J", pattern_open_matcher),
    A3_NATIVE("getMatchedGroupIndexImpl", "(JLjava/lang/String;)I",
              pattern_group_number),
    A3_NATIVE("getNativeFinalizer", "()J", pattern_get_native_finalizer),
};

static JNINativeMethod kMatcherMethods[] = {
    A3_NATIVE("setInputImpl", "(JLjava/lang/String;II)V", matcher_set_input),
    A3_NATIVE("matchesImpl", "(J[I)Z", matcher_matches),
    A3_NATIVE("lookingAtImpl", "(J[I)Z", matcher_looking_at),
    A3_NATIVE("findImpl", "(JI[I)Z", matcher_find),
    A3_NATIVE("findNextImpl", "(J[I)Z", matcher_find_next),
    A3_NATIVE("groupCountImpl", "(J)I", matcher_group_count),
    A3_NATIVE("hitEndImpl", "(J)Z", matcher_hit_end),
    A3_NATIVE("requireEndImpl", "(J)Z", matcher_require_end),
    A3_NATIVE("useAnchoringBoundsImpl", "(JZ)V",
              matcher_use_anchoring_bounds),
    A3_NATIVE("useTransparentBoundsImpl", "(JZ)V",
              matcher_use_transparent_bounds),
    A3_NATIVE("getNativeFinalizer", "()J", matcher_get_native_finalizer),
};

static JNINativeMethod kConverterMethods[] = {
    A3_NATIVE("openConverter", "(Ljava/lang/String;)J", converter_open),
    A3_NATIVE("closeConverter", "(J)V", converter_close),
    A3_NATIVE("decode", "(J[BI[CI[IZ)I", converter_decode),
    A3_NATIVE("encode", "(J[CI[BI[IZ)I", converter_encode),
    A3_NATIVE("getMaxBytesPerChar", "(J)I", converter_get_max_bytes),
    A3_NATIVE("getAveBytesPerChar", "(J)F", converter_get_average_bytes),
    A3_NATIVE("getAveCharsPerByte", "(J)F", converter_get_average_chars),
    A3_NATIVE("resetByteToChar", "(J)V", converter_reset_to_unicode),
    A3_NATIVE("resetCharToByte", "(J)V", converter_reset_from_unicode),
    A3_NATIVE("getSubstitutionBytes", "(J)[B",
              converter_get_substitution_bytes),
    A3_NATIVE("getNativeFinalizer", "()J", converter_get_native_finalizer),
    A3_NATIVE("setCallbackDecode", "(JIILjava/lang/String;)V",
              converter_set_decode_callback),
    A3_NATIVE("setCallbackEncode", "(JII[B)V",
              converter_set_encode_callback),
};

static_assert(sizeof(kPatternMethods) / sizeof(kPatternMethods[0]) == 4,
              "PatternNative override count drift");
static_assert(sizeof(kMatcherMethods) / sizeof(kMatcherMethods[0]) == 11,
              "MatcherNative override count drift");
static_assert(sizeof(kConverterMethods) / sizeof(kConverterMethods[0]) == 13,
              "NativeConverter override count drift");

#undef A3_NATIVE
#undef A3_TRACE

static int register_methods(JNIEnv* env, const char* class_name,
                            JNINativeMethod* methods, jint count) {
    jclass cls = env->FindClass(class_name);
    if (cls == nullptr) {
        fprintf(stderr, "[A3-ICU] ERROR FindClass %s\n", class_name);
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        return -1;
    }
    jint rc = env->RegisterNatives(cls, methods, count);
    env->DeleteLocalRef(cls);
    if (rc != JNI_OK || env->ExceptionCheck()) {
        fprintf(stderr,
                "[A3-ICU] ERROR RegisterNatives %s rc=%d count=%d\n",
                class_name, rc, count);
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        return -1;
    }
    return 0;
}

}  // namespace

// Native acceptance probes may dlsym this symbol from the admitted
// liboh_android_runtime.so. The fixed order is pattern open/close, matcher
// open/close, converter open/close. This lets GC/RSS stress prove balanced
// ownership without flooding production logs.
extern "C" int westlake_icu_snapshot_lifecycle(uint64_t* counts,
                                                size_t count) {
    if (counts == nullptr || count < LIFECYCLE_COUNT) {
        return -1;
    }
    for (size_t index = 0; index < LIFECYCLE_COUNT; ++index) {
        counts[index] =
            __atomic_load_n(&g_lifecycle[index], __ATOMIC_RELAXED);
    }
    fprintf(stderr,
            "[A3-ICU] COUNTERS pid=%d pattern=%llu/%llu "
            "matcher=%llu/%llu converter=%llu/%llu\n",
            static_cast<int>(getpid()),
            static_cast<unsigned long long>(
                counts[LIFECYCLE_PATTERN_OPEN]),
            static_cast<unsigned long long>(
                counts[LIFECYCLE_PATTERN_CLOSE]),
            static_cast<unsigned long long>(
                counts[LIFECYCLE_MATCHER_OPEN]),
            static_cast<unsigned long long>(
                counts[LIFECYCLE_MATCHER_CLOSE]),
            static_cast<unsigned long long>(
                counts[LIFECYCLE_CONVERTER_OPEN]),
            static_cast<unsigned long long>(
                counts[LIFECYCLE_CONVERTER_CLOSE]));
    return 0;
}

int westlake_icu_early_init() {
    return load_icu_cohort();
}

int westlake_register_charset_natives(JNIEnv* env) {
    if (env == nullptr || !g_icu.ready) {
        fprintf(stderr,
                "[A3-ICU] ERROR charset registration before ICU ready\n");
        return -1;
    }
    if (env->PushLocalFrame(32) < 0) {
        fprintf(stderr, "[A3-ICU] ERROR charset PushLocalFrame\n");
        return -1;
    }
    int rc = register_methods(
        env, "com/android/icu/charset/NativeConverter", kConverterMethods,
        static_cast<jint>(sizeof(kConverterMethods) /
                          sizeof(kConverterMethods[0])));
    env->PopLocalFrame(nullptr);
    if (rc == 0) {
        fprintf(stderr,
                "[A3-ICU] registered NativeConverter 13/16 "
                "(provider methods remain ART-owned)\n");
    }
    return rc;
}

int westlake_register_regex_natives(JNIEnv* env) {
    if (env == nullptr || !g_icu.ready) {
        fprintf(stderr, "[A3-ICU] ERROR regex registration before ICU ready\n");
        return -1;
    }
    if (env->PushLocalFrame(32) < 0) {
        fprintf(stderr, "[A3-ICU] ERROR regex PushLocalFrame\n");
        return -1;
    }
    int rc = register_methods(
        env, "com/android/icu/util/regex/PatternNative", kPatternMethods,
        static_cast<jint>(sizeof(kPatternMethods) /
                          sizeof(kPatternMethods[0])));
    if (rc == 0) {
        rc = register_methods(
            env, "com/android/icu/util/regex/MatcherNative", kMatcherMethods,
            static_cast<jint>(sizeof(kMatcherMethods) /
                              sizeof(kMatcherMethods[0])));
    }
    env->PopLocalFrame(nullptr);
    if (rc == 0) {
        fprintf(stderr, "[A3-ICU] registered regex Pattern+Matcher 15/15\n");
    }
    return rc;
}
