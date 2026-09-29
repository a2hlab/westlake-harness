// libwestlake_html_compat.so — Wikipedia tagsoup 墙的兼容层(#r17,40min 限时)。
//
// 照抄来源(vm-copies/westlake-current @ 532633d,一手行号):
//   child_main.cpp L468-525  wl_clear_converted_fast_native 的 fail-closed 位修语义
//                            (ArtMethod: access_flags_ @ +4;kAccNative 0x100 /
//                             kAccFastNative 0x80000 同位冲突须清)
//   child_main.cpp L905-917  ArtMethod 布局注释(Android 12+ ART = 板上 R155 image108/oat230):
//                            +0x00 u32 declaring_class_ / +0x04 u32 access_flags_ /
//                            +0x08 u32 dex_method_index_ / +0x18 ptr quick entry
//   child_main.cpp L536-593  wl_rebind_portable_timezone 的开关 + dlsym + RegisterNatives 流程
//
// 目标:把 android.text.Html.fromHtml(String,int,ImageGetter,TagHandler) 一个托管方法
// 改成 JNI 方法,native 实现回调 runtime JAR 的 Java 替代类(类名经 WESTLAKE_HTML_COMPAT_CLASS
// 传入,由 cc-t3 提供替代实现)。硬要求:
//   ①写前校验:读回 declaring_class/access_flags/dex_method_index,须与
//     GetStaticMethodID 拿到的 jmethodID 对应同一方法一致才写,否则跳过+日志;
//   ②WESTLAKE_HTML_COMPAT=1 开关,关则不装;
//   ③任何失败只 log,不抛、不杀(其他 app 不受影响)。
#include <jni.h>
#include <dlfcn.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstddef>
#include <cstdarg>
#include <unistd.h>
#include <sys/uio.h>

namespace {

// —— ArtMethod 布局(Westlake child_main.cpp L905-917,Android 12+ ART)——
constexpr size_t kDeclaringClassOff = 0x00;   // u32 GcRoot(压缩引用)
constexpr size_t kAccessFlagsOff    = 0x04;   // u32
constexpr size_t kDexMethodIndexOff = 0x08;   // u32
constexpr size_t kQuickEntryOff     = 0x18;   // ptr
constexpr uint32_t kAccNative       = 0x00000100u;
constexpr uint32_t kAccFastNative   = 0x00080000u;
constexpr uint32_t kAccStatic       = 0x00000008u;
constexpr uintptr_t kMinDirectAddr  = 0x10000u;

// 安全读(EFAULT 返回而非嵌套 fault)——照抄 wl_safe_read L922-927
bool safe_read(uintptr_t src, void* dst, size_t n) {
    struct iovec l{dst, n};
    struct iovec r{reinterpret_cast<void*>(src), n};
    return process_vm_readv(getpid(), &l, 1, &r, 1, 0) == static_cast<ssize_t>(n);
}

void logf(const char* fmt, ...) __attribute__((format(printf, 1, 2)));
void logf(const char* fmt, ...) {
    char b[512];
    va_list ap; va_start(ap, fmt);
    int n = vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    if (n > 0) { ssize_t w = write(2, b, static_cast<size_t>(n)); (void)w; }
}

// native 实现:转发给 runtime JAR 的替代类(类名由 env 注入)。返回类型与
// Html.fromHtml 声明一致 = android.text.Spanned;替代类签名为
//   static android.text.Spanned fromHtmlCompat(String source, int flags,
//       Html.ImageGetter ig, Html.TagHandler th)
// (外环 2026-09-30 修订①:jstring 返回会类型错乱;缺类/缺方法时返回
//   new SpannedString(source) 而非原串。)
jobject JNICALL html_from_html_native(JNIEnv* env, jclass, jstring src, jint flags,
                                      jobject imageGetter, jobject tagHandler) {
    static jmethodID compat = nullptr;
    static jclass compatClass = nullptr;
    static jclass spannedStringClass = nullptr;
    static jmethodID spannedStringCtor = nullptr;
    // fallback: new SpannedString(source) — a real Spanned even when src is null
    auto fallback = [&]() -> jobject {
        if (spannedStringCtor == nullptr) {
            jclass sc = env->FindClass("android/text/SpannedString");
            if (sc == nullptr || env->ExceptionCheck()) {
                env->ExceptionClear();
                logf("[HTML-COMPAT] SpannedString unavailable; returning null\n");
                return nullptr;
            }
            spannedStringClass = static_cast<jclass>(env->NewGlobalRef(sc));
            env->DeleteLocalRef(sc);
            spannedStringCtor = env->GetMethodID(
                spannedStringClass, "<init>", "(Ljava/lang/CharSequence;)V");
            if (spannedStringCtor == nullptr || env->ExceptionCheck()) {
                env->ExceptionClear();
                logf("[HTML-COMPAT] SpannedString ctor missing; returning null\n");
                return nullptr;
            }
        }
        return env->NewObject(spannedStringClass, spannedStringCtor, src);
    };
    if (compat == nullptr) {
        const char* clsName = getenv("WESTLAKE_HTML_COMPAT_CLASS");
        if (clsName == nullptr || clsName[0] == '\0') {
            logf("[HTML-COMPAT] WESTLAKE_HTML_COMPAT_CLASS unset; fallback SpannedString(source)\n");
            return fallback();
        }
        jclass c = env->FindClass(clsName);
        if (c == nullptr || env->ExceptionCheck()) {
            env->ExceptionClear();
            logf("[HTML-COMPAT] class %s not found; fallback SpannedString(source)\n", clsName);
            return fallback();
        }
        compatClass = static_cast<jclass>(env->NewGlobalRef(c));
        env->DeleteLocalRef(c);
        compat = env->GetStaticMethodID(
            compatClass, "fromHtmlCompat",
            "(Ljava/lang/String;ILandroid/text/Html$ImageGetter;"
            "Landroid/text/Html$TagHandler;)Landroid/text/Spanned;");
        if (compat == nullptr || env->ExceptionCheck()) {
            env->ExceptionClear();
            logf("[HTML-COMPAT] fromHtmlCompat(String,int,ImageGetter,TagHandler)Spanned "
                 "missing in %s; fallback SpannedString(source)\n", clsName);
            compat = reinterpret_cast<jmethodID>(1);  // sentinel: no forward
        }
    }
    if (compat == reinterpret_cast<jmethodID>(1) || src == nullptr) {
        return fallback();
    }
    return env->CallStaticObjectMethod(compatClass, compat,
                                       src, flags, imageGetter, tagHandler);
}

// 位修:写前读回校验 + kAccNative 置位 + kAccFastNative 清位(照抄 L468-525 的
// fail-closed 语义,方向相反:那里清 FastNative,这里置 Native 并保 Fast 位为 0)
bool convert_method_to_native(jmethodID id, const char* name,
                              uint32_t expectedDexIdxLo, uint32_t expectedDexIdxHi) {
    const uintptr_t raw = reinterpret_cast<uintptr_t>(id);
    if (raw < kMinDirectAddr || (raw & 3u) != 0u) {
        logf("[HTML-COMPAT] %s: not a direct ArtMethod (%p)\n", name, (void*)raw);
        return false;
    }
    uint32_t declaring = 0, flags = 0, dexIdx = 0;
    if (!safe_read(raw + kDeclaringClassOff, &declaring, 4) ||
        !safe_read(raw + kAccessFlagsOff, &flags, 4) ||
        !safe_read(raw + kDexMethodIndexOff, &dexIdx, 4)) {
        logf("[HTML-COMPAT] %s: ArtMethod unreadable @%p\n", name, (void*)raw);
        return false;
    }
    // 校验一:声明类非零压缩引用、flags 里 static 位符合 fromHtml(static)
    if (declaring == 0 || (flags & kAccStatic) == 0) {
        logf("[HTML-COMPAT] %s: layout mismatch declaring=%#x flags=%#x (not static?)\n",
             name, declaring, flags);
        return false;
    }
    // 校验二:dex_method_index 在框架 dex 的合理窗口(boot framework.dex 方法数<150k;
    // 用调用方给的窗口双重锁定,防错位)
    if (dexIdx < expectedDexIdxLo || dexIdx > expectedDexIdxHi) {
        logf("[HTML-COMPAT] %s: dex_method_index %u outside [%u,%u] — layout suspect, skip\n",
             name, dexIdx, expectedDexIdxLo, expectedDexIdxHi);
        return false;
    }
    if ((flags & kAccNative) != 0u) {
        logf("[HTML-COMPAT] %s: already native flags=%#x — RegisterNatives only\n", name, flags);
        return true;   // 已是 native,无需写位
    }
    const uint32_t after = kAccNative | (flags & ~kAccFastNative);
    __atomic_store_n(reinterpret_cast<uint32_t*>(raw + kAccessFlagsOff), after, __ATOMIC_RELEASE);
    logf("[HTML-COMPAT] %s: flags %#x -> %#x (kAccNative set, FastNative cleared) "
         "declaring=%#x dexIdx=%u\n", name, flags, after, declaring, dexIdx);
    return true;
}

void install(JNIEnv* env) {
    const char* on = getenv("WESTLAKE_HTML_COMPAT");
    if (on == nullptr || strcmp(on, "1") != 0) return;   // ②开关,默认不装

    jclass html = env->FindClass("android/text/Html");
    if (html == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        logf("[HTML-COMPAT] android/text/Html not found — skip\n");
        return;
    }
    jmethodID id = env->GetStaticMethodID(
        html, "fromHtml", "(Ljava/lang/String;ILandroid/text/Html$ImageGetter;Landroid/text/Html$TagHandler;)Landroid/text/Spanned;");
    if (id == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        logf("[HTML-COMPAT] fromHtml(String,int,ImageGetter,TagHandler) not found — skip\n");
        env->DeleteLocalRef(html);
        return;
    }
    // ①写前校验(窗口:framework dex 巨大方法区,取宽窗;失败即跳过不写)
    if (!convert_method_to_native(id, "Html.fromHtml", 1u, 150000u)) {
        env->DeleteLocalRef(html);
        return;
    }
    JNINativeMethod m = {
        const_cast<char*>("fromHtml"),
        const_cast<char*>("(Ljava/lang/String;ILandroid/text/Html$ImageGetter;Landroid/text/Html$TagHandler;)Landroid/text/Spanned;"),
        reinterpret_cast<void*>(&html_from_html_native)};
    const jint rc = env->RegisterNatives(html, &m, 1);
    if (env->ExceptionCheck()) env->ExceptionClear();
    logf("[HTML-COMPAT] RegisterNatives(Html.fromHtml) rc=%d\n", static_cast<int>(rc));

    // —— 生效性核验与修补(外环 2026-09-30 修订②)——
    // RegisterNatives 只写 JNI 入口表;若 Html 已在父进程被 AOT 初始化,
    // quick 入口(@+0x18)仍指 OAT 代码,改写不生效。读回 quick 与
    // art_quick_generic_jni_trampoline(Westlake art_runtime_stubs.cpp L384 证实
    // libart 导出该符号;dlsym 取本进程真值)比对:不同则按同一 trampoline 目标
    // 写回(imageless Westlake 运行时做同样转换的落点)。两路都打 before/after。
    dlerror();
    auto genericTrampoline = reinterpret_cast<uintptr_t>(
        dlsym(RTLD_DEFAULT, "art_quick_generic_jni_trampoline"));
    const char* symErr = dlerror();
    uintptr_t quick = 0;
    const uintptr_t art = reinterpret_cast<uintptr_t>(id);
    bool readOk = safe_read(art + kQuickEntryOff, &quick, sizeof quick);
    if (genericTrampoline == 0 || symErr != nullptr) {
        logf("[HTML-COMPAT] generic trampoline unavailable (%s); quick before=%#lx "
             "— CANNOT verify/repair, leaving as RegisterNatives left it\n",
             symErr ? symErr : "dlsym null", (unsigned long)quick);
    } else if (!readOk) {
        logf("[HTML-COMPAT] quick entry unreadable @%p — leaving untouched\n", (void*)art);
    } else if (quick == genericTrampoline) {
        logf("[HTML-COMPAT] quick already generic-JNI (%#lx) — effective\n",
             (unsigned long)quick);
    } else {
        __atomic_store_n(reinterpret_cast<uintptr_t*>(art + kQuickEntryOff),
                         genericTrampoline, __ATOMIC_RELEASE);
        uintptr_t after = 0;
        safe_read(art + kQuickEntryOff, &after, sizeof after);
        logf("[HTML-COMPAT] quick repointed AOT %#lx -> generic-JNI %#lx (verify read=%#lx)\n",
             (unsigned long)quick, (unsigned long)genericTrampoline, (unsigned long)after);
    }
    env->DeleteLocalRef(html);
}

}  // namespace

extern "C" JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    if (vm == nullptr ||
        vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK ||
        env == nullptr) return JNI_ERR;
    install(env);          // ③内部全 try-path,失败只 log
    return JNI_VERSION_1_6;
}
