#!/usr/bin/env python3
"""
[A3-ICUDATA] 在 runtime 原生侧把 android.icu.impl.ICUBinary.icuDataFiles 填上。

板 5ce2dcee child 14507 实证（adapter_child_14507.stderr:1101-1110 与 :290-297，
两处**同一根**）：

    [class_linker.cc:6318] Tolerating clinit failure for Landroid/icu/impl/UPropertyAliases;
    java.lang.NullPointerException: Attempt to get length of null array
      at java.lang.VMClassLoader.getResource(VMClassLoader.java:64)
      at java.lang.BootClassLoader.findResource(ClassLoader.java:2698)
      at java.lang.ClassLoader.getResourceAsStream(ClassLoader.java:1704)
      at android.icu.impl.ICUData.getStream(ICUData.java:142)
      at android.icu.impl.ICUBinary.getData(ICUBinary.java:511)

读法：ICUBinary.getData 先走**文件径**（icuDataFiles 列表），空 ⟹ 回退到
**boot classloader 取资源**径；而本 imageless ART 的 VMClassLoader.getResource
里那个数组是 null ⟹ NPE。clinit 失败被 ART "Tolerating"，于是
UPropertyAliases.INSTANCE 恒为 null，后面
UCharacter.getPropertyValueEnumNoThrow 直接 NPE 打死 handleBindApplication。
android.graphics.Typeface.<clinit> 死在同一条链上（child 日志 :290）。

⟹ 只要把文件径填上，两处一起活。

已有的等效修复写在 Java 侧
appspawn-x/java/com/android/internal/os/AppSchedulerBridge 邻居
AppSpawnXInit.ensureICUDataLoaded()（源码 :582-665），但**板上这条路径没跑**
（child 日志对其全部日志串零命中），而 framework jar 是本板红线不可替换。
故在 runtime 原生侧做等效实现——startReg 在 daemon 里执行一次，
子进程 fork COW 继承已填好的静态列表（与既有 39 枚桥注册同一机制）。

两级：
  1) 反射调 ICUBinary.addDataFilesFromPath("/system/android/etc/icu", list)
     —— daemon 是 root，listFiles() 很可能在这里就成，子进程直接继承。
  2) 不成则 mmap .dat 自造 ICUBinary$PackageDataFile 塞进列表
     （先 icudt72l.dat 后 icudt74l.dat；A3 原生 cohort 绑的是 ICU72）。
     映射只读私有，永不 munmap，fork 后子进程继承同一映射。

纪律：全程不抛 Java 异常、失败非致命（不牵连既有 charset/regex/locale/桥注册）。

幂等：见 GUARD。
"""
import sys

ICU = "westlake_icu_overrides.cpp"
ART = "AndroidRuntime.cpp"
GUARD = "A3-ICUDATA"

ICU_INCLUDE_ANCHOR = """#include <dlfcn.h>
"""
ICU_INCLUDE_NEW = """#include <dlfcn.h>
#include <errno.h>       // [A3-ICUDATA 2026-07-31]
#include <fcntl.h>       // [A3-ICUDATA]
#include <sys/mman.h>    // [A3-ICUDATA]
#include <sys/stat.h>    // [A3-ICUDATA]
"""

ICU_TAIL = r"""

// ===================== [A3-ICUDATA 2026-07-31] =========================
// 填 android.icu.impl.ICUBinary.icuDataFiles。见本仓
// src/tools/task79-swap-window/patch_icu_data.py 头部的实证与读法。

static const char kA3IcuDir[] = "/system/android/etc/icu";
static const char* const kA3IcuDats[] = {"icudt72l.dat", "icudt74l.dat"};

// 只读私有映射，成功后**不** munmap —— 该 ByteBuffer 要活到进程结束，
// 且 fork 后子进程继承同一映射。
static jobject a3_map_dat(JNIEnv* env, const char* name, long* out_size) {
    char path[512];
    int written = snprintf(path, sizeof(path), "%s/%s", kA3IcuDir, name);
    if (written < 0 || static_cast<size_t>(written) >= sizeof(path)) {
        return nullptr;
    }
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "[A3-ICUDATA] open %s failed errno=%d\n", path, errno);
        return nullptr;
    }
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size <= 0) {
        fprintf(stderr, "[A3-ICUDATA] fstat %s failed errno=%d\n", path, errno);
        close(fd);
        return nullptr;
    }
    void* addr = mmap(nullptr, static_cast<size_t>(st.st_size), PROT_READ,
                      MAP_PRIVATE, fd, 0);
    close(fd);
    if (addr == MAP_FAILED) {
        fprintf(stderr, "[A3-ICUDATA] mmap %s failed errno=%d\n", path, errno);
        return nullptr;
    }
    jobject bb = env->NewDirectByteBuffer(addr, static_cast<jlong>(st.st_size));
    if (bb == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        munmap(addr, static_cast<size_t>(st.st_size));
        fprintf(stderr, "[A3-ICUDATA] NewDirectByteBuffer %s failed\n", path);
        return nullptr;
    }
    *out_size = static_cast<long>(st.st_size);
    return bb;
}

int westlake_ensure_icu_data(JNIEnv* env) {
    if (env == nullptr) {
        return -1;
    }
    if (env->PushLocalFrame(64) < 0) {
        fprintf(stderr, "[A3-ICUDATA] ERROR PushLocalFrame\n");
        return -1;
    }

    int rc = -1;
    int stage = 0;
    jint count = -1;

    do {
        jclass icu = env->FindClass("android/icu/impl/ICUBinary");
        if (icu == nullptr) {
            env->ExceptionClear();
            fprintf(stderr, "[A3-ICUDATA] FindClass ICUBinary MISS\n");
            break;
        }
        jfieldID fid =
            env->GetStaticFieldID(icu, "icuDataFiles", "Ljava/util/List;");
        if (fid == nullptr) {
            env->ExceptionClear();
            fprintf(stderr, "[A3-ICUDATA] static field icuDataFiles MISS\n");
            break;
        }
        jobject list = env->GetStaticObjectField(icu, fid);
        if (list == nullptr) {
            fprintf(stderr, "[A3-ICUDATA] icuDataFiles is null\n");
            break;
        }
        jclass list_cls = env->FindClass("java/util/List");
        if (list_cls == nullptr) {
            env->ExceptionClear();
            break;
        }
        jmethodID m_size = env->GetMethodID(list_cls, "size", "()I");
        jmethodID m_add =
            env->GetMethodID(list_cls, "add", "(Ljava/lang/Object;)Z");
        if (m_size == nullptr || m_add == nullptr) {
            env->ExceptionClear();
            break;
        }

        count = env->CallIntMethod(list, m_size);
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
            break;
        }
        if (count > 0) {
            rc = 0;
            break;   // 已有条目：boot 期正常径已成，不动它
        }

        // ---- 一级：反射走 ICUBinary 自己的目录扫描 ----
        stage = 1;
        jmethodID m_path = env->GetStaticMethodID(
            icu, "addDataFilesFromPath", "(Ljava/lang/String;Ljava/util/List;)V");
        if (m_path != nullptr) {
            jstring dir = env->NewStringUTF(kA3IcuDir);
            if (dir != nullptr) {
                env->CallStaticVoidMethod(icu, m_path, dir, list);
            }
            if (env->ExceptionCheck()) {
                env->ExceptionClear();
            }
        } else {
            env->ExceptionClear();
        }
        count = env->CallIntMethod(list, m_size);
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
            count = 0;
        }
        if (count > 0) {
            rc = 0;
            break;
        }

        // ---- 二级：mmap .dat 自造 PackageDataFile ----
        stage = 2;
        jclass pdf = env->FindClass("android/icu/impl/ICUBinary$PackageDataFile");
        if (pdf == nullptr) {
            env->ExceptionClear();
            fprintf(stderr, "[A3-ICUDATA] PackageDataFile class MISS\n");
            break;
        }
        jmethodID pdf_ctor = env->GetMethodID(
            pdf, "<init>", "(Ljava/lang/String;Ljava/nio/ByteBuffer;)V");
        if (pdf_ctor == nullptr) {
            env->ExceptionClear();
            fprintf(stderr, "[A3-ICUDATA] PackageDataFile ctor MISS\n");
            break;
        }
        jclass dpr =
            env->FindClass("android/icu/impl/ICUBinary$DatPackageReader");
        jmethodID m_validate = nullptr;
        if (dpr != nullptr) {
            m_validate = env->GetStaticMethodID(dpr, "validate",
                                                "(Ljava/nio/ByteBuffer;)Z");
            if (m_validate == nullptr) {
                env->ExceptionClear();
            }
        } else {
            env->ExceptionClear();
        }

        for (size_t i = 0; i < sizeof(kA3IcuDats) / sizeof(kA3IcuDats[0]); ++i) {
            const char* name = kA3IcuDats[i];
            long sz = 0;
            jobject bb = a3_map_dat(env, name, &sz);
            if (bb == nullptr) {
                continue;
            }
            if (m_validate != nullptr) {
                jboolean ok = env->CallStaticBooleanMethod(dpr, m_validate, bb);
                if (env->ExceptionCheck()) {
                    env->ExceptionClear();
                    ok = JNI_FALSE;
                }
                if (ok == JNI_FALSE) {
                    fprintf(stderr,
                            "[A3-ICUDATA] %s rejected by DatPackageReader"
                            ".validate\n", name);
                    continue;
                }
            }
            jstring jname = env->NewStringUTF(name);
            if (jname == nullptr) {
                env->ExceptionClear();
                continue;
            }
            jobject df = env->NewObject(pdf, pdf_ctor, jname, bb);
            if (df == nullptr || env->ExceptionCheck()) {
                env->ExceptionClear();
                continue;
            }
            env->CallBooleanMethod(list, m_add, df);
            if (env->ExceptionCheck()) {
                env->ExceptionClear();
                continue;
            }
            fprintf(stderr, "[A3-ICUDATA] mmap fallback added %s (%ld B)\n",
                    name, sz);
            rc = 0;
            break;
        }
        count = env->CallIntMethod(list, m_size);
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
            count = -1;
        }
    } while (false);

    env->PopLocalFrame(nullptr);
    if (env->ExceptionCheck()) {
        env->ExceptionClear();   // 纪律：出口零 pending exception
    }
    fprintf(stderr, "[A3-ICUDATA] SUMMARY rc=%d stage=%d icuDataFiles=%d\n",
            rc, stage, static_cast<int>(count));
    return rc;
}
"""

ART_DECL_ANCHOR = ("extern int westlake_register_locale_natives(JNIEnv* env);"
                   "  // [A3-LOCALE 2026-07-31]\n")
ART_DECL_NEW = ("extern int westlake_register_locale_natives(JNIEnv* env);"
                "  // [A3-LOCALE 2026-07-31]\n"
                "extern int westlake_ensure_icu_data(JNIEnv* env);"
                "  // [A3-ICUDATA 2026-07-31]\n")

ART_CALL_ANCHOR = """    if (::westlake_register_locale_natives(env) != 0) {
        fprintf(stderr,
                "[liboh_android_runtime] A3 LocaleNative registration failed "
                "(non-fatal; bindApplication will ULE)\\n");
    }
"""
ART_CALL_NEW = """    if (::westlake_register_locale_natives(env) != 0) {
        fprintf(stderr,
                "[liboh_android_runtime] A3 LocaleNative registration failed "
                "(non-fatal; bindApplication will ULE)\\n");
    }

    // [A3-ICUDATA 2026-07-31] ICUBinary.icuDataFiles 若为空，ICU 资源查找会
    // 回退到 boot classloader 取资源径，而本 imageless ART 的
    // VMClassLoader.getResource 在那里 NPE（child 14507 实证），连累
    // UPropertyAliases 与 Typeface 两处 clinit 被 ART "Tolerating"。
    // 此处在 daemon 内填一次，子进程 fork COW 继承。非致命。
    (void)::westlake_ensure_icu_data(env);
"""


def patch(path, edits, tail=None):
    src = open(path, encoding="utf8").read()
    if GUARD in src:
        print(f"  SKIP {path}: 已含 {GUARD}（幂等）")
        return False
    for label, old, new in edits:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"FAIL {path}: 锚点 [{label}] 命中 {n} 次（须恰好 1）")
        src = src.replace(old, new)
        print(f"  ok  {path}: [{label}]")
    if tail:
        src = src.rstrip("\n") + "\n" + tail
        print(f"  ok  {path}: [尾部实现]")
    open(path, "w", encoding="utf8").write(src)
    return True


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    icu, art = f"{root}/{ICU}", f"{root}/{ART}"
    patch(icu, [("头文件", ICU_INCLUDE_ANCHOR, ICU_INCLUDE_NEW)], tail=ICU_TAIL)
    patch(art, [("extern 声明", ART_DECL_ANCHOR, ART_DECL_NEW),
                ("startReg 调用点", ART_CALL_ANCHOR, ART_CALL_NEW)])
    for p in (icu, art):
        s = open(p, encoding="utf8").read()
        print(f"  复核 {p}: {len(s.splitlines())} 行, {GUARD} x{s.count(GUARD)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
