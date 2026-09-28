#!/usr/bin/env python3
"""
[A3-LOCALE] 给 liboh_android_runtime 补 com.android.icu.util.LocaleNative.setDefaultNative。

板 5ce2dcee child 6101 实证死链（adapter_child_6101.stderr:1093-1101）：

    ActivityThread.handleBindApplication(ActivityThread.java:6799)
      -> android.os.LocaleList.setDefault(LocaleList.java:548 -> 569)
      -> java.util.Locale.setDefault(Locale.java:1212)
      -> libcore.icu.ICU.setDefaultLocale(ICU.java:719)
      -> com.android.icu.util.LocaleNative.setDefault(LocaleNative.java:48)
      -> LocaleNative.setDefaultNative(String)     <<< UnsatisfiedLinkError
    => ensureBindApplication FAILED (InvocationTargetException)

A3 当初只覆盖 charset(NativeConverter 13/16) + regex(Pattern+Matcher 15/15)，
LocaleNative 不在册（本窗 grep 复核：westlake_icu_overrides.cpp 零命中）。

本补丁在同一 TU 内沿用 A3 已实证的 ICU72 dlopen cohort：
板上 /system/android/lib64/libicuuc.so 导出 uloc_setDefault_72 与
uloc_forLanguageTag_72（本窗拉件 strings 复核，各 2 命中）。

三条纪律：
  1. 新绑定走**可选**径，不用 BIND_REQUIRED —— uloc_* 万一缺失也不得拖垮
     已在板上实证的 charset/regex cohort（那是 startReg 的致命判据）。
  2. native 实现**绝不向 Java 抛异常** —— 抛了等于 ULE 没修。
     forLanguageTag 失败就降级成 '-'->'_' 直传，再失败就记账 no-op。
  3. 注册失败**非致命** —— 只记账，不中止 startReg（不牵连既有 39 枚桥注册）。

幂等：见 GUARD。
"""
import re
import sys

ICU = "westlake_icu_overrides.cpp"
ART = "AndroidRuntime.cpp"
GUARD = "A3-LOCALE"

# ---------------------------------------------------------------- 1. 结构体字段
ICU_STRUCT_ANCHOR = """    UBool (*uregex_require_end)(const void*, UErrorCode*);
};
"""
ICU_STRUCT_NEW = """    UBool (*uregex_require_end)(const void*, UErrorCode*);

    // [A3-LOCALE 2026-07-31] 可选族。绑定失败不得影响上面任何一枚。
    void (*uloc_set_default)(const char*, UErrorCode*);
    int32_t (*uloc_for_language_tag)(const char*, char*, int32_t, int32_t*,
                                     UErrorCode*);
};
"""

# ---------------------------------------------------------------- 2. 可选绑定
ICU_BIND_ANCHOR = """    BIND_REQUIRED(g_icu.i18n_handle, uregex_require_end, "uregex_requireEnd",
                  suffix);
    return true;
}
"""
ICU_BIND_NEW = """    BIND_REQUIRED(g_icu.i18n_handle, uregex_require_end, "uregex_requireEnd",
                  suffix);

    // [A3-LOCALE] 可选：缺了也让 cohort 成立，只是 setDefaultNative 退成 no-op。
    g_icu.uloc_set_default =
        reinterpret_cast<decltype(g_icu.uloc_set_default)>(
            versioned_symbol(g_icu.uc_handle, "uloc_setDefault", suffix));
    g_icu.uloc_for_language_tag =
        reinterpret_cast<decltype(g_icu.uloc_for_language_tag)>(
            versioned_symbol(g_icu.uc_handle, "uloc_forLanguageTag", suffix));

    return true;
}
"""

# ---------------------------------------------------------------- 3. 实现+注册
ICU_TAIL = r"""

// ===================== [A3-LOCALE 2026-07-31] =========================
// com.android.icu.util.LocaleNative.setDefaultNative(String)
//
// register_methods / g_icu 在上方匿名 namespace 内定义；匿名 namespace 成员
// 在本 TU 剩余部分依然可见，故此处直接复用，不重复实现。
//
// 语义对齐 AOSP libcore com_android_icu_util_LocaleNative.cpp：
// BCP-47 language tag -> ICU locale id -> uloc_setDefault。
// 差异：AOSP 在解析失败时抛 IllegalArgumentException，本实现**不抛** ——
// 见文件头纪律 2。

static void a3_locale_set_default(JNIEnv* env, jclass, jstring java_tag) {
    if (env == nullptr || java_tag == nullptr) {
        return;
    }
    if (g_icu.uloc_set_default == nullptr) {
        static bool warned = false;
        if (!warned) {
            warned = true;
            fprintf(stderr,
                    "[A3-LOCALE] uloc_setDefault unbound -> setDefaultNative "
                    "is a no-op (ICU keeps its own default locale)\n");
        }
        return;
    }

    const char* tag = env->GetStringUTFChars(java_tag, nullptr);
    if (tag == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        return;
    }

    char locale_id[256];
    locale_id[0] = '\0';
    UErrorCode status = U_ZERO_ERROR;
    if (g_icu.uloc_for_language_tag != nullptr) {
        int32_t parsed = 0;
        g_icu.uloc_for_language_tag(tag, locale_id,
                                    static_cast<int32_t>(sizeof(locale_id) - 1),
                                    &parsed, &status);
        if (status > U_ZERO_ERROR) {   // U_FAILURE：warning 是负数，不算失败
            locale_id[0] = '\0';
        } else {
            locale_id[sizeof(locale_id) - 1] = '\0';
        }
    }
    if (locale_id[0] == '\0') {
        size_t n = strlen(tag);
        if (n >= sizeof(locale_id)) {
            n = sizeof(locale_id) - 1;
        }
        memcpy(locale_id, tag, n);
        locale_id[n] = '\0';
        for (size_t i = 0; i < n; ++i) {
            if (locale_id[i] == '-') {
                locale_id[i] = '_';
            }
        }
    }

    status = U_ZERO_ERROR;
    g_icu.uloc_set_default(locale_id, &status);

    static bool logged = false;
    if (!logged) {
        logged = true;
        fprintf(stderr, "[A3-LOCALE] setDefaultNative ACTIVE tag=%s id=%s "
                        "rc=%d\n",
                tag, locale_id, static_cast<int>(status));
    } else if (status > U_ZERO_ERROR) {
        fprintf(stderr, "[A3-LOCALE] uloc_setDefault(%s) rc=%d (ignored)\n",
                locale_id, static_cast<int>(status));
    }

    env->ReleaseStringUTFChars(java_tag, tag);
    // 出口前不留任何 pending exception —— 纪律 2。
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
    }
}

static JNINativeMethod kLocaleMethods[] = {
    {const_cast<char*>("setDefaultNative"),
     const_cast<char*>("(Ljava/lang/String;)V"),
     reinterpret_cast<void*>(a3_locale_set_default)},
};

int westlake_register_locale_natives(JNIEnv* env) {
    if (env == nullptr) {
        return -1;
    }
    if (env->PushLocalFrame(16) < 0) {
        fprintf(stderr, "[A3-LOCALE] ERROR PushLocalFrame\n");
        return -1;
    }
    int rc = register_methods(env, "com/android/icu/util/LocaleNative",
                              kLocaleMethods,
                              static_cast<jint>(sizeof(kLocaleMethods) /
                                                sizeof(kLocaleMethods[0])));
    env->PopLocalFrame(nullptr);
    fprintf(stderr,
            "[A3-LOCALE] LocaleNative %s  uloc_setDefault=%s "
            "uloc_forLanguageTag=%s icu_ready=%d\n",
            rc == 0 ? "registered 1/1" : "REGISTRATION FAILED",
            g_icu.uloc_set_default != nullptr ? "bound" : "MISSING",
            g_icu.uloc_for_language_tag != nullptr ? "bound" : "MISSING",
            g_icu.ready ? 1 : 0);
    return rc;
}
"""

# ---------------------------------------------------------------- 4. 声明
ART_DECL_ANCHOR = "extern int westlake_register_regex_natives(JNIEnv* env);\n"
ART_DECL_NEW = ("extern int westlake_register_regex_natives(JNIEnv* env);\n"
                "extern int westlake_register_locale_natives(JNIEnv* env);"
                "  // [A3-LOCALE 2026-07-31]\n")

# ---------------------------------------------------------------- 5. 调用点
ART_CALL_ANCHOR = """            "NativeConverter=13/16 regex=15/15\\n");
"""
ART_CALL_NEW = """            "NativeConverter=13/16 regex=15/15\\n");

    // [A3-LOCALE 2026-07-31] handleBindApplication:6799 -> LocaleList.setDefault
    // -> Locale.setDefault -> ICU.setDefaultLocale -> LocaleNative.setDefaultNative
    // 板 5ce2dcee child 6101 实证：此处 ULE 直接打死 bindApplication。
    // 非致命：注册失败只记账，不中止 startReg（不牵连既有桥注册 39 枚）。
    if (::westlake_register_locale_natives(env) != 0) {
        fprintf(stderr,
                "[liboh_android_runtime] A3 LocaleNative registration failed "
                "(non-fatal; bindApplication will ULE)\\n");
    }
"""


def patch(path, edits, tail=None):
    src = open(path, encoding="utf8").read()
    if GUARD in src:
        print(f"  SKIP {path}: 已含 {GUARD} 标记（幂等）")
        return False
    for label, old, new in edits:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"FAIL {path}: 锚点 [{label}] 命中 {n} 次（须恰好 1）")
        src = src.replace(old, new)
        print(f"  ok  {path}: [{label}]")
    if tail:
        src = src.rstrip("\n") + "\n" + tail
        print(f"  ok  {path}: [尾部实现+注册]")
    open(path, "w", encoding="utf8").write(src)
    return True


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    icu, art = f"{root}/{ICU}", f"{root}/{ART}"

    patch(icu, [("IcuApi 结构体字段", ICU_STRUCT_ANCHOR, ICU_STRUCT_NEW),
                ("bind_symbol_cohort 可选绑定", ICU_BIND_ANCHOR, ICU_BIND_NEW)],
          tail=ICU_TAIL)
    patch(art, [("extern 声明", ART_DECL_ANCHOR, ART_DECL_NEW),
                ("startReg 调用点", ART_CALL_ANCHOR, ART_CALL_NEW)])

    for p in (icu, art):
        s = open(p, encoding="utf8").read()
        print(f"  复核 {p}: {len(s.splitlines())} 行, {GUARD} x{s.count(GUARD)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
