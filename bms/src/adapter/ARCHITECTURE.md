# ARCHITECTURE.md — adapter 整体架构总览

> 目的：让新人 5 分钟内建立"整体链路 + 各目录职责"的心智图，回答"我这个问题该改哪里"。
> 建立日期 2026-07-10。术语见 `GLOSSARY.md`；版本身份见 `BASE_VERSIONS.md`；来源见 `PROVENANCE.md`。

---

## 1. 一图看懂链路

```
  未修改 Android/Unity APK (CardWords, arm64-v8a, bionic ABI)
        │  被 OH 系统拉起（appspawn-x 混合孵化）
        ▼
  ┌─────────────────────────────────────────────┐
  │  adapter framework/ （Java + JNI 适配层）      │
  │   Android framework API  ──桥──▶  OH inner_api │
  │   liboh_adapter_bridge.so (framework/jni)      │
  └─────────────────────────────────────────────┘
        │              │                │
   bionic↔musl     IPC 桥接        源码补丁
   翻译层          (AMS/WMS/       aosp_patches/ (AOSP 14)
   (appspawn-x/    Surface/BMS…)   ohos_patches/ (OpenHarmony 6.1)
    bionic_compat)
        ▼
  OpenHarmony 6.1 (musl) 系统服务 / RenderService / 真机 arm64
```

三种改造手段并存：
1. **framework/**：adapter 自有 Java + JNI 桥接代码（可自由编辑，非补丁）。
2. **aosp_patches/ + ohos_patches/**：对**外置** AOSP/OH 源码树的 `.patch`（镜像上游目录结构，安装期 apply）。
3. **bionic↔musl 翻译 + stub/overlay/shim**：让 bionic ABI 的 app 在 musl 系统上正确运行、并让本机能独立编译。

## 2. 顶层目录职责

| 目录/文件 | 职责 | 可编辑性 |
|---|---|---|
| `framework/` | adapter 自有 Java+JNI 桥接源码（13 子模块 + CMakeLists.txt，见 `framework/README.md`） | 自有代码 |
| `aosp_patches/` | 对外置 AOSP 14 源码的补丁（镜像 AOSP 目录树） | 补丁 |
| `ohos_patches/` | 对外置 OpenHarmony 6.1 源码的补丁（BMS/installd 等） | 补丁（部分 codex 锁定） |
| `build/` | 编译脚本；`build/inner/` 是被上层 `build_*.sh` 调用的内部 helper | 脚本 |
| `third_party/oh_stubs/` | 27 个链接期符号 stub（`STUBS_MANIFEST.md`） | Claude 维护 |
| `build/oh_headers_631_overlay/` | 4 个 6.1.0.31 接口头覆盖 | Claude 维护 |
| `appspawn/` `config/` | appspawn-x 路由/沙箱注入脚本与配置 | 脚本/配置 |
| `deploy/` | 部署到设备的脚本与 SOP（真机侧，零设备纪律下只读参考） | 脚本 |
| `neverdie/` | "永不死机"设备加固/golden 恢复脚本 | 脚本 |
| `app/` | HelloWorld 测试脚手架 APK（**非**生产标的，生产标的是 CardWords APK） | 测试 |
| `doc/` | ~50 个中文 HTML 设计文档（**历史参考**，某时点快照，不保证与当前实现同步；详见 `LEGACY_CONTENT.md`） | 文档（历史） |
| `out/` | 编译产物（gitignore，不进仓库） | 产物 |
| `prebuilts/` | OH/AOSP 工具链快捷方式 | 只读 |
| `coordination/` | COORDINATION 历史归档 | 归档 |
| **权威 .md**（顶层） | `BASE_VERSIONS / PROVENANCE / HANDOFF_L04_L14 / COORDINATION` | 见各自 owner |
| **历史/噪声** | `_routeb_bak_*` `_routeb_dev_bak` `build/_deprecated` `doc/bkup` 等 | 只读，勿复制，见 `LEGACY_CONTENT.md` |

## 3. framework/ 13 模块速览（详见 framework/README.md；`CMakeLists.txt` 是构建聚合文件，不算模块）

| 模块 | 桥接的 Android 能力 | 对接的 OH 能力 |
|---|---|---|
| `core/` | OHEnvironment 等核心运行环境 | — |
| `activity/` | AMS / ATMS（Activity 生命周期） | OH AbilityManager |
| `window/` | WMS / WindowSession | OH WindowManager |
| `surface/` | Surface / SurfaceView | OH RSSurfaceNode / RenderService |
| `broadcast/` | 广播 Broadcast | OH CommonEvent |
| `contentprovider/` | ContentProvider | OH DataShare |
| `package-manager/` | PackageManager / APK 安装 | OH BMS / installd |
| `appspawn-x/` | 进程孵化 + bionic_compat 翻译 | OH appspawn |
| `hwui-shim/` | Android HWUI / NDK 图形 | OH 图形栈（含 GrAHB shim） |
| `android-runtime/` | 渐进替代 libandroid_runtime | OH（`liboh_android_runtime.so`） |
| `jni/` | `liboh_adapter_bridge.so` JNI 入口（BUILD.gn 权威 sources） | — |
| `inet-shim/` | 网络/inet | OH |
| `mainline-stubs/` | Android mainline 模块占位 | — |

## 4. 构建视角（详见 BUILDING.md / VERIFICATION.md）
- 单目录 arm64 主产物 = `liboh_adapter_bridge.so`，编译入口 `build/inner/compile_oh_adapter_bridge_arm64.sh`。
  **arm64 单目录**这条主线用受保护的直接调用（`BUILD_INNER_INVOKED=1 [FORCE_OH_SDK=1] bash …`，见 BUILDING §2）；
  顶层 `build_adapter.sh --target=liboh_adapter_bridge.so` 当前 dispatch 的是 **armv7** 版脚本，别用它编 arm64。
- 依赖：外置 `OH_ROOT`/`AOSP_ROOT`/`OH_SDK` + `third_party/oh_stubs/`（链接期符号）+ `build/oh_headers_631_overlay/`（头覆盖）。
- 成功判据：**strict link 成功**（`-Wl,--no-undefined` 未回退 relaxed），链成 AArch64 ELF64。判据细节与"为何 `nm -u` 非空也可能正常"见 `VERIFICATION.md`。
