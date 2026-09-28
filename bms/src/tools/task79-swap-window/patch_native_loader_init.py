#!/usr/bin/env python3
# [WALL-5 2026-07-31] NativeLoader 注册表从来没人初始化过。
#
# 现场（板 5ce2dcee，child 2495，本地 hdc 实证）：
#   java.lang.UnsatisfiedLinkError: Unable to create namespace for the
#   classloader dalvik.system.PathClassLoader[westlake]:
#   NativeLoader is not initialized
#     at com.android.internal.os.ClassLoaderFactory.createClassLoader:153
#     ... LoadedApk.getClassLoader → ContextImpl.createActivityContext
#     ... ActivityThread.performLaunchActivity → handleLaunchActivity
#
# 定罪（源码级）：
#   adapter/framework/native-loader-oh/src/native_loader_registry.cpp:157
#     if (state_ != RegistryState::kRunning) → "NativeLoader is not initialized"
#   状态只由 Registry::Initialize()（同文件 :77）置 kRunning，
#   而 Initialize 的唯一生产入口 android::InitializeNativeLoader()
#     （native-loader-oh/src/native_loader.cpp:137）
#   全树 grep 无任何生产调用方 —— 只有 tests/ 和 bionic_compat 里的空 stub
#     （appspawn-x/bionic_compat/src/art_runtime_stubs.cpp:247/881
#      `void InitializeNativeLoader() {}`）。
#   AOSP 里这一枚由 art/runtime/jni/java_vm_ext.cc:1231 在建 VM 时调用；
#   本树的 imageless ART 没走那条路，于是整套 namespace 注册表是死的。
#
# 之前没暴露，是因为只有 app 自己的 PathClassLoader 才会走
# CreateClassLoaderNamespace；bindApplication 直到这一轮才推进到那里。
#
# 修法：在 daemon 的 startReg 尾部调一次 InitializeNativeLoader()。
#   - Initialize(nullptr) → BindVmLocked(nullptr) 直接 kOk（registry.cpp:64），
#     不绑 VM，VM 留给各进程首次 GetOrCreate 时自绑 → fork 后子进程自己绑自己的，
#     不会撞 "observed a different JavaVM"。
#   - 幂等：state_ 已是 kRunning 就只是空转。
#   - 时序与 AOSP 一致（AOSP 也是 zygote fork 前建 VM 时初始化）。
#   - 全树没有任何 ResetNativeLoader() 生产调用方，不存在 fork 后被重置的风险。
#   - libnativeloader.so 未被守护 pin（appspawn-x.real .rodata 无该串），
#     所以这次只换 runtime 一枚，pin 窗口照旧。
import io
import re
import sys

PATH = "/opt/build-trees/adapter/framework/android-runtime/src/AndroidRuntime.cpp"

DECL_ANCHOR = 'extern int westlake_ensure_icu_data(JNIEnv* env);  // [A3-ICUDATA 2026-07-31]'
DECL_ADD = '''
// [WALL-5 2026-07-31] libnativeloader.so 导出的 extern "C" 未修饰符号。
// 声明在文件作用域即可，调用点用 ::InitializeNativeLoader() 显式限定。
extern "C" void InitializeNativeLoader(void);'''

CALL_ANCHOR = '    // [A3-ICUDATA 2026-07-31] ICUBinary.icuDataFiles 若为空'
CALL_ADD = '''    // [WALL-5 2026-07-31] NativeLoader 注册表初始化。不初始化则 app 自己的
    // PathClassLoader 一律拿不到 namespace，performLaunchActivity 必 ULE。
    // 见 native_loader_registry.cpp:157 的 kRunning 判据。
    ::InitializeNativeLoader();
    fprintf(stderr, "[WALL5-NL] InitializeNativeLoader called\\n");

'''


def main() -> int:
    with io.open(PATH, "r", encoding="utf-8") as fh:
        src = fh.read()

    if "[WALL-5 2026-07-31]" in src:
        sys.stderr.write("already patched\n")
        return 3

    if src.count(DECL_ANCHOR) != 1:
        sys.stderr.write("decl anchor count != 1\n")
        return 1
    src = src.replace(DECL_ANCHOR, DECL_ANCHOR + DECL_ADD, 1)

    if src.count(CALL_ANCHOR) != 1:
        sys.stderr.write("call anchor count != 1\n")
        return 1
    src = src.replace(CALL_ANCHOR, CALL_ADD + CALL_ANCHOR, 1)

    sys.stdout.write(src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
