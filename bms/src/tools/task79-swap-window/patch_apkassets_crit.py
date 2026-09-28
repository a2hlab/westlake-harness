#!/usr/bin/env python3
# [WALL-7 2026-07-31] ApkAssets.nativeIsUpToDate 是本跑里唯一一枚 @CriticalNative，
# 它收到的参数是错的，于是锁死主线程。
#
# 现场（板 5ce2dcee，child 4522 / 6889，本地 hdc + OHOS dumpcatcher 实证）：
#   主线程 state=S wchan=futex_wait_queue_me，OH AMS 超时发 ScheduleNotifyAppFault
#   → ScheduleCleanAbility 收尸。dumpcatcher 栈顶：
#     #00 __timedwait_cp                       ld-musl-aarch64.so.1
#     #01 __pthread_mutex_timedlock_inner      ld-musl-aarch64.so.1
#     #02 std::__h::mutex::lock()+8            libc++.so
#     #03 android::NativeIsUpToDate(long)+16   liboh_android_runtime.so
#     #04.. 全是 art::interpreter::InterpreterJni / ExecuteSwitchImpl（纯解释执行）
#   全进程 10 个线程，**只有主线程有 mutex::lock**，不存在跨线程死锁。
#
# 定罪（反汇编 + /proc 实证，非推理）：
#   objdump 本次部署件（BuildID 6ab128c0…，与栈里一致）：
#     631c4 <_ZN7androidL16NativeIsUpToDateEl>:
#       631d0: mov x19, x0            ← 唯一入参就是那个 ptr
#       631d4: bl  mutex::lock        ← 直接把 *(x0) 当 std::mutex 锁
#       631d8: ldr x0, [x19, #0x28]   ← ApkAssets* 在 +0x28
#   符号名 _ZN7androidL16NativeIsUpToDateEl = android::NativeIsUpToDate(long)，
#   单参 ⟹ CRITICAL_JNI_PARAMS；注册签名 (J)Z；子进程日志里标了 crit=1。
#   活体取证（child 6889）：
#     /proc/<pid>/syscall → futex uaddr = 0x7fd877159c
#     /proc/<pid>/maps    → 7fd875b000-7fd877b000 rw-p [stack]
#   **它锁的地址在主线程自己的栈上**。真正的 guarded-ApkAssets 在堆里
#   （本进程 heap = 55a5610000-55a57a0000）。⟹ 传进来的根本不是那个指针。
#   同跑 13 枚 crit=0 的 native 全部正常，crit=1 的只此一枚、只此一挂。
#
# 结论：这套 imageless ART 的解释器 JNI 路径不认 @CriticalNative 的传参约定。
#
# 补充：x0 具体是个什么（推理，非实证）
#   x0 = 0x7fd8771598 落在主线程栈里，而 ART 的解释器 shadow frame / vreg 数组
#   就是在本机栈上 alloca 的。所以最可能是：解释器把「入参数组指针 args」
#   当成那个 jlong 传了进来，而不是 args[0]|args[1]<<32 的值。
#   JNIEnv* 与真正的 ApkAssets* 都在堆上，都对不上这个地址，可排除。
#   —— 机制归机制，下面的修法对以上任何一种都免疫。
#
# 修法：不去修 ART，也不去猜参数——**换一枚不看参数的实现**。
#   RegisterNatives 覆盖 android/content/res/ApkAssets.nativeIsUpToDate (J)Z，
#   实现恒返 JNI_TRUE。
#   （AArch64 AAPCS 下，被调方不读任何入参 ⟹ 调用方按 f()、f(jlong)、
#     还是 f(JNIEnv*,jclass,jlong) 传都无所谓，三种约定全兼容。）
#
#   为什么恒返 true 是对的（不是敷衍）：
#     AOSP  ApkAssets.isUpToDate() 的唯一用途是 ResourcesManager 复用缓存前
#     确认底下的 APK 文件没被换过。本场景 APK 静态、进程生命周期内不会被替换，
#     "up to date" 就是事实。返回 true = 复用缓存，语义正确。
#     （返回 false 才有害：会触发重新 load，白烧一遍 mmap。）
#   这枚实现忽略全部入参 ⟹ **传参约定错不错都不影响它**，从根上绕开该缺陷。
#
# 局限（明写，不当已解决）：
#   ART 解释器对 @CriticalNative 的传参约定本身还是错的。今天全跑只撞到这一枚，
#   往后 app 用到别的 @CriticalNative（比如 Trace / SystemClock 一族）会再犯。
#   终局是修 ART 的 InterpreterJni 关键原生路径，不在本窗构建炉范围内。
#
# 与二进制补丁的关系：
#   本窗构建炉（alexyLinux 60022）当时不可达，先用 binpatch_isuptodate.py 把
#   已构建产物里的 NativeIsUpToDate 直接改成 `mov w0,#1; ret` 上板验证。
#   本脚本是同一改动的源码侧等价物，炉子回来后落进源码树；两者语义一致，
#   落了源码版之后二进制版自然被下一代产物覆盖。
#
# 实现说明：不借 westlake_icu_overrides.cpp 里那个匿名命名空间的
#   register_methods()——它的第三参是非 const JNINativeMethod*、返回值约定
#   我没在本地产物上验到（nm 只给得出形参，给不出返回类型）。
#   也不用 AndroidRuntime::registerNativeMethods()：它底下是 libnativehelper 的
#   jniRegisterNativeMethods，失败会 abort，而这段代码跑在 daemon 里，
#   一 abort 就是整个 appspawn-x 陪葬。直接用 JNI 原语，失败只记账不炸。
import io
import sys

ICU = "/opt/build-trees/adapter/framework/android-runtime/src/westlake_icu_overrides.cpp"
ART = "/opt/build-trees/adapter/framework/android-runtime/src/AndroidRuntime.cpp"

ICU_TAIL = r'''

// ===================== [WALL-7 2026-07-31] @CriticalNative 绕行 =====================
// 见 src/tools/task79-swap-window/patch_apkassets_crit.py 顶部定罪说明。
namespace {

// 忽略全部入参：这枚方法在本 ART 上以错误的传参约定被调用，任何一个参数都不可信。
jboolean a3_apkassets_is_up_to_date(JNIEnv*, jclass, jlong) {
    return JNI_TRUE;
}

}  // namespace

int westlake_register_apkassets_crit(JNIEnv* env) {
    jclass cls = env->FindClass("android/content/res/ApkAssets");
    if (cls == nullptr) {
        env->ExceptionClear();
        fprintf(stderr, "[WALL7-CRIT] FindClass(ApkAssets) failed\n");
        return -1;
    }
    JNINativeMethod m = {const_cast<char*>("nativeIsUpToDate"),
                         const_cast<char*>("(J)Z"),
                         reinterpret_cast<void*>(a3_apkassets_is_up_to_date)};
    const jint rc = env->RegisterNatives(cls, &m, 1);
    if (rc != JNI_OK && env->ExceptionCheck()) {
        env->ExceptionDescribe();
        env->ExceptionClear();
    }
    env->DeleteLocalRef(cls);
    fprintf(stderr, "[WALL7-CRIT] ApkAssets.nativeIsUpToDate override rc=%d\n",
            static_cast<int>(rc));
    return rc == JNI_OK ? 0 : -1;
}
'''

ART_DECL_ANCHOR = 'extern int westlake_install_anl_runtime_gate();  // [WALL-5B 2026-07-31]'
ART_DECL_ADD = '''
extern int westlake_register_apkassets_crit(JNIEnv* env);  // [WALL-7 2026-07-31]'''

ART_CALL_ANCHOR = '    (void)::westlake_install_anl_runtime_gate();\n'
ART_CALL_ADD = '''
    // [WALL-7 2026-07-31] 盖掉 ApkAssets.nativeIsUpToDate —— 它是 @CriticalNative，
    // 在本 ART 的解释器 JNI 路径上收到的是栈上垃圾指针，一锁就死。
    // 换成忽略入参恒返 true 的实现（语义见补丁说明）。
    (void)::westlake_register_apkassets_crit(env);
'''


def patch(path: str, edits, tail: str = "") -> str:
    with io.open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    if "[WALL-7 2026-07-31]" in src:
        raise SystemExit("already patched: " + path)
    for anchor, replacement in edits:
        if src.count(anchor) != 1:
            raise SystemExit("anchor count != 1 in %s: %r" % (path, anchor[:60]))
        src = src.replace(anchor, replacement, 1)
    return src + tail


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "icu":
        sys.stdout.write(patch(ICU, [], ICU_TAIL))
    elif which == "art":
        sys.stdout.write(patch(ART, [
            (ART_DECL_ANCHOR, ART_DECL_ANCHOR + ART_DECL_ADD),
            (ART_CALL_ANCHOR, ART_CALL_ANCHOR + ART_CALL_ADD),
        ]))
    else:
        raise SystemExit("usage: patch_apkassets_crit.py icu|art")
    return 0


if __name__ == "__main__":
    sys.exit(main())
