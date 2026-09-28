#!/usr/bin/env python3
"""
[adapter-bridge-reg 2026-07-31] 幂等补丁：给 liboh_android_runtime.so 的 startReg
加一段「显式 RegisterNatives OH adapter 族」的块。

为什么需要：liboh_adapter_bridge.so 是 runtime 的 DT_NEEDED 直接依赖，进程内实测
映射在场（child /proc/PID/maps 4 条），且以标准 C JNI 名导出 50 枚 Java_adapter_*；
但桥住在与 ART lazy 解析搜索面不同的 musl namespace，**在场 ≠ 可达**
（docs/noice-reproduce/gate-baseline-r1.md:281-287 已定案）。已实证可用注册径只有
RegisterNatives + provider VJI 路由。

拦路症状（本补丁针对）：PackageManagerAdapter.nativeGetApplicationInfo ULE →
ensureBindApplication 回落到裸 ApplicationInfo（sourceDir/publicSourceDir 为 null）
→ android.app.LoadedApk.makePaths 对 null 调 String.equals → NPE 出 main，
首帧之前死。证据 var/evidence/task79-noice-lightup/libandroid-symlink-window-5ce2dcee/。

设计纪律：
  - 容错（log+continue），**绝不 abort startReg**。这些是 OH 集成便利径、Java 侧
    自带 fallback，不属 kRegJNI[] fail-hard 规约要防的「NULL g*_cache → 远 NULL 解引用」族。
  - 逐方法 RegisterNatives（不批量）：一个签名写错不会连累同类其余方法。
  - 签名取自**板上部署的** oh-adapter-framework.jar（jadx 反编译），不取仓内源码
    ——两者已漂移（仓内 PackageManagerAdapter 有 12 个 native，部署版只有 8 个）。
  - 符号经 dlsym 取；桥已是 DT_NEEDED，dlopen 按名返回既有句柄，不产生第二实例。
    dlopen 失败时 br=nullptr，dlsym(nullptr,…) 即 RTLD_DEFAULT，天然兜底。

用法: patch_adapter_bridge_reg.py <AndroidRuntime.cpp 路径>
"""
import sys, re

MARK = "[adapter-bridge-reg"

BLOCK = r'''
    // ============================================================
    // [adapter-bridge-reg 2026-07-31] 显式 RegisterNatives：OH adapter JNI 族
    //
    // liboh_adapter_bridge.so 是本 .so 的 DT_NEEDED 直接依赖，以标准 C JNI 名
    // 导出 50 枚 Java_adapter_*；进程内映射在场实测（child maps 4 条）。但桥所在
    // musl namespace 不在 ART lazy 解析的搜索面内 ⟹ 每个 adapter native 都
    // UnsatisfiedLinkError，尽管符号就在同一进程里（「在场 ≠ 可达」，
    // gate-baseline-r1.md §注册径 namespace 隔离）。已实证可用注册径 =
    // RegisterNatives（本块）+ provider VJI 路由。
    //
    // 拦路症状：PackageManagerAdapter.nativeGetApplicationInfo ULE →
    // ensureBindApplication 回落裸 ApplicationInfo（sourceDir 为 null）→
    // LoadedApk.makePaths 对 null 调 String.equals → NPE 出 main，首帧前死。
    //
    // 容错设计：log+continue，绝不 abort startReg。逐方法注册，坏签名不连累同类。
    // 签名取自板上部署的 oh-adapter-framework.jar（jadx），非仓内源码（已漂移）。
    // ============================================================
    {
        struct BrFn  { const char* name; const char* sig; const char* sym; };
        struct BrCls { const char* cls; const BrFn* fns; size_t n; };

        // --- adapter.packagemanager.PackageManagerAdapter ---
        // 部署版声明 8 枚 native；桥导出其中 6 枚。缺的两枚
        // （nativeParseApkManifestJson / nativeGetOhSystemProperty）全板零实现，
        // 属真缺件（gate-baseline-r1.md:285 对照组判词），不在本补丁范围。
        static const BrFn kPm[] = {
            {"nativeGetApplicationInfo", "(Ljava/lang/String;I)Ljava/lang/String;",
             "Java_adapter_packagemanager_PackageManagerAdapter_nativeGetApplicationInfo"},
            {"nativeGetBundleInfo",      "(Ljava/lang/String;I)Ljava/lang/String;",
             "Java_adapter_packagemanager_PackageManagerAdapter_nativeGetBundleInfo"},
            {"nativeGetAllBundleInfos",  "(I)Ljava/lang/String;",
             "Java_adapter_packagemanager_PackageManagerAdapter_nativeGetAllBundleInfos"},
            {"nativeQueryAbilityInfos",  "(Ljava/lang/String;I)Ljava/lang/String;",
             "Java_adapter_packagemanager_PackageManagerAdapter_nativeQueryAbilityInfos"},
            {"nativeGetUidByBundleName", "(Ljava/lang/String;)I",
             "Java_adapter_packagemanager_PackageManagerAdapter_nativeGetUidByBundleName"},
            {"nativeCheckPermission",    "(Ljava/lang/String;Ljava/lang/String;)I",
             "Java_adapter_packagemanager_PackageManagerAdapter_nativeCheckPermission"},
        };

        // --- adapter.window.DisplayManagerAdapter ---
        // 未注册时 Java 侧走「hardcoded fallback」分支，屏幕尺寸/密度全是编死值；
        // 真出画面必须拿真值，否则 layout 与实际显示面不符。
        static const BrFn kDisp[] = {
            {"nativeGetDefaultDisplayWidth",       "()I", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayWidth"},
            {"nativeGetDefaultDisplayHeight",      "()I", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayHeight"},
            {"nativeGetDefaultDisplayDpi",         "()I", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayDpi"},
            {"nativeGetDefaultDisplayDensity",     "()F", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayDensity"},
            {"nativeGetDefaultDisplayXDpi",        "()F", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayXDpi"},
            {"nativeGetDefaultDisplayYDpi",        "()F", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayYDpi"},
            {"nativeGetDefaultDisplayRotation",    "()I", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayRotation"},
            {"nativeGetDefaultDisplayRefreshRate", "()I", "Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayRefreshRate"},
            {"nativeGetDisplayId",                 "()J", "Java_adapter_window_DisplayManagerAdapter_nativeGetDisplayId"},
            {"nativeGetDisplayState",              "()I", "Java_adapter_window_DisplayManagerAdapter_nativeGetDisplayState"},
            {"nativeGetAvailableArea",            "()[I", "Java_adapter_window_DisplayManagerAdapter_nativeGetAvailableArea"},
            {"nativeGetCutoutBoundingRects",      "()[I", "Java_adapter_window_DisplayManagerAdapter_nativeGetCutoutBoundingRects"},
            {"nativeGetRoundedCorners",           "()[I", "Java_adapter_window_DisplayManagerAdapter_nativeGetRoundedCorners"},
            {"nativeGetSupportedColorSpaces",     "()[I", "Java_adapter_window_DisplayManagerAdapter_nativeGetSupportedColorSpaces"},
            {"nativeGetSupportedHdrFormats",      "()[I", "Java_adapter_window_DisplayManagerAdapter_nativeGetSupportedHdrFormats"},
            {"nativeGetSupportedRefreshRates",    "()[I", "Java_adapter_window_DisplayManagerAdapter_nativeGetSupportedRefreshRates"},
        };

        // --- adapter.window.InputManagerAdapter ---
        // nativeInit 未注册 ⟹ 走 NO_FEATURE fallback，触摸/按键整条链不通。
        static const BrFn kInput[] = {
            {"nativeInit",                 "()J",        "Java_adapter_window_InputManagerAdapter_nativeInit"},
            {"nativeGetInputDeviceIds",    "(J)[I",      "Java_adapter_window_InputManagerAdapter_nativeGetInputDeviceIds"},
            {"nativeGetInputDevice",       "(JI)Landroid/view/InputDevice;",
                                                         "Java_adapter_window_InputManagerAdapter_nativeGetInputDevice"},
            {"nativeIsInputDeviceEnabled", "(JI)Z",      "Java_adapter_window_InputManagerAdapter_nativeIsInputDeviceEnabled"},
            {"nativeEnableInputDevice",    "(JIZ)V",     "Java_adapter_window_InputManagerAdapter_nativeEnableInputDevice"},
            {"nativeFindVirtualKeyboardId","(J)I",       "Java_adapter_window_InputManagerAdapter_nativeFindVirtualKeyboardId"},
            {"nativeHasKeys",              "(JI[I[Z)Z", "Java_adapter_window_InputManagerAdapter_nativeHasKeys"},
            {"nativeInjectKeyEvent",       "(JIIIIJJII)Z",
                                                         "Java_adapter_window_InputManagerAdapter_nativeInjectKeyEvent"},
            {"nativeInjectMotionEvent",    "(JIIFFJJIIII)Z",
                                                         "Java_adapter_window_InputManagerAdapter_nativeInjectMotionEvent"},
            {"nativeSetPointerIconType",   "(JI)V",      "Java_adapter_window_InputManagerAdapter_nativeSetPointerIconType"},
            {"nativeSetPointerSpeed",      "(JI)V",      "Java_adapter_window_InputManagerAdapter_nativeSetPointerSpeed"},
            {"nativeSetCustomPointerIcon", "(JLandroid/view/PointerIcon;)V",
                                                         "Java_adapter_window_InputManagerAdapter_nativeSetCustomPointerIcon"},
            {"nativeRegisterDeviceListener","(JLandroid/hardware/input/IInputDevicesChangedListener;)V",
                                                         "Java_adapter_window_InputManagerAdapter_nativeRegisterDeviceListener"},
        };

        // --- adapter.activity.ActivityClientControllerAdapter ---
        // nativeAbilityTransitionDone 是 Android 侧告知 OH「窗口转场完成」的回路；
        // 不通则 OH 侧可能永不置窗可见。
        static const BrFn kActCtl[] = {
            {"nativeAbilityTransitionDone",     "(JI)I", "Java_adapter_activity_ActivityClientControllerAdapter_nativeAbilityTransitionDone"},
            {"nativeBackPressedByTokenAddr",    "(J)I",  "Java_adapter_activity_ActivityClientControllerAdapter_nativeBackPressedByTokenAddr"},
            {"nativeMinimizeAbilityByTokenAddr","(J)I",  "Java_adapter_activity_ActivityClientControllerAdapter_nativeMinimizeAbilityByTokenAddr"},
            {"nativeTerminateAbilityByTokenAddr","(JI)I","Java_adapter_activity_ActivityClientControllerAdapter_nativeTerminateAbilityByTokenAddr"},
        };

        // --- adapter.activity.AppSchedulerBridge（桥只导出 2 枚）---
        static const BrFn kAppSch[] = {
            {"nativeTerminateAbility",              "(J)I", "Java_adapter_activity_AppSchedulerBridge_nativeTerminateAbility"},
            {"nativeNotifyApplicationForegrounded", "()I",  "Java_adapter_activity_AppSchedulerBridge_nativeNotifyApplicationForegrounded"},
        };

        static const BrCls kBrClasses[] = {
            { "adapter/packagemanager/PackageManagerAdapter",      kPm,     sizeof(kPm)/sizeof(kPm[0]) },
            { "adapter/window/DisplayManagerAdapter",              kDisp,   sizeof(kDisp)/sizeof(kDisp[0]) },
            { "adapter/window/InputManagerAdapter",                kInput,  sizeof(kInput)/sizeof(kInput[0]) },
            { "adapter/activity/ActivityClientControllerAdapter",  kActCtl, sizeof(kActCtl)/sizeof(kActCtl[0]) },
            { "adapter/activity/AppSchedulerBridge",               kAppSch, sizeof(kAppSch)/sizeof(kAppSch[0]) },
        };

        // 桥已是 DT_NEEDED，按名 dlopen 返回既有句柄（musl 按 dev+ino 去重），
        // 不产生第二实例。失败则 br=nullptr，dlsym(nullptr,…)==RTLD_DEFAULT 兜底。
        void* br = dlopen("liboh_adapter_bridge.so", RTLD_NOW);
        if (br == nullptr) {
            const char* e = dlerror();
            fprintf(stderr, "[adapter-bridge-reg] dlopen liboh_adapter_bridge.so FAILED: %s"
                            " — 退回 RTLD_DEFAULT\n", e ? e : "(null)");
        }

        int cls_ok = 0, cls_miss = 0, m_ok = 0, m_bad = 0, sym_miss = 0;
        for (const auto& c : kBrClasses) {
            if (env->PushLocalFrame(32) < 0) {
                fprintf(stderr, "[adapter-bridge-reg] PushLocalFrame failed at %s\n", c.cls);
                continue;
            }
            jclass k = env->FindClass(c.cls);
            if (k == nullptr) {
                if (env->ExceptionCheck()) { env->ExceptionClear(); }
                fprintf(stderr, "[adapter-bridge-reg] FindClass %s MISS（startReg 时刻不在 boot classpath？）\n",
                        c.cls);
                cls_miss++;
                env->PopLocalFrame(nullptr);
                continue;
            }
            int this_ok = 0;
            for (size_t i = 0; i < c.n; ++i) {
                void* fn = dlsym(br, c.fns[i].sym);
                if (fn == nullptr) {
                    fprintf(stderr, "[adapter-bridge-reg]   dlsym MISS %s\n", c.fns[i].sym);
                    sym_miss++;
                    continue;
                }
                JNINativeMethod m;
                m.name      = const_cast<char*>(c.fns[i].name);
                m.signature = const_cast<char*>(c.fns[i].sig);
                m.fnPtr     = fn;
                // 逐方法注册：坏签名只废掉自己，不连累同类其余方法。
                jint rc = env->RegisterNatives(k, &m, 1);
                if (env->ExceptionCheck()) { env->ExceptionClear(); rc = (rc == JNI_OK) ? -1 : rc; }
                if (rc == JNI_OK) {
                    this_ok++; m_ok++;
                } else {
                    fprintf(stderr, "[adapter-bridge-reg]   RegisterNatives BAD %s.%s%s rc=%d\n",
                            c.cls, c.fns[i].name, c.fns[i].sig, rc);
                    m_bad++;
                }
            }
            fprintf(stderr, "[adapter-bridge-reg]   %s: %d/%zu ok\n", c.cls, this_ok, c.n);
            if (this_ok > 0) cls_ok++;
            env->PopLocalFrame(nullptr);
        }
        fprintf(stderr,
                "[adapter-bridge-reg] SUMMARY: classes %d ok / %d miss, methods %d ok / %d bad, dlsym miss %d\n",
                cls_ok, cls_miss, m_ok, m_bad, sym_miss);
    }
'''

ANCHOR = """    for (size_t i = 0; i < kRegJNICount; ++i) {"""


def main():
    path = sys.argv[1]
    src = open(path, encoding="utf-8").read()

    if MARK in src:
        print(f"SKIP: {path} 已含 {MARK} 块（幂等）")
        return 0

    idx = src.find(ANCHOR)
    if idx < 0:
        print(f"FAIL: 找不到锚点 kRegJNI 循环: {path}", file=sys.stderr)
        return 1

    # 锚点之后第一处独立的 "    env->PopLocalFrame(nullptr);\n" = kRegJNI 循环收尾
    tail = src[idx:]
    m = re.search(r"\n    env->PopLocalFrame\(nullptr\);\n", tail)
    if not m:
        print("FAIL: 找不到 kRegJNI 循环收尾的 PopLocalFrame", file=sys.stderr)
        return 1
    ins = idx + m.end()

    out = src[:ins] + BLOCK + src[ins:]
    open(path, "w", encoding="utf-8").write(out)
    print(f"OK: 已插入 {MARK} 块 @ 偏移 {ins}（{path}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
