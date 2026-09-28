# framework/ — adapter 自有 Java + JNI 桥接源码（模块地图）

> 目的：回答"我要改某个能力的桥接，去哪个目录 / 谁依赖谁"。
> 建立日期 2026-07-10。整体链路见上级 `../ARCHITECTURE.md`；编译依赖/运行时调用方向/产物归属见 `DEPENDENCIES.md`；术语见 `../GLOSSARY.md`。

`framework/` 是 adapter **自有**代码（区别于对上游源码打补丁的 `aosp_patches/` `ohos_patches/`）。
共 **13 个功能子模块** + 一个 `CMakeLists.txt`（构建聚合文件，不算模块）。每个子模块把某个 Android framework 能力桥接到对应 OH inner_api。典型子目录结构：`java/`（Java 侧适配）、`jni/`（native 桥）、少数含 `BUILD.gn`（sources 权威清单）。

## 模块清单与职责

| 模块 | 职责 | Android 侧 | OH 侧 | 目录结构 |
|---|---|---|---|---|
| `core/` | 核心运行环境（OHEnvironment 等），其它模块的公共底座 | — | — | include/ java/ jni/ |
| `activity/` | Activity 生命周期、Ability 管理 | AMS / ATMS | OH AbilityManager | java/ jni/ |
| `window/` | 窗口/会话生命周期 | WMS / WindowSession | OH WindowManager | java/ jni/ |
| `surface/` | 图形 Surface 桥接（含 skia RTTI shim） | Surface / SurfaceView | OH RSSurfaceNode / RenderService | jni/ |
| `broadcast/` | 广播事件 | Broadcast / Intent | OH CommonEvent | java/ jni/ |
| `contentprovider/` | 内容提供/数据共享 | ContentProvider | OH DataShare | java/ jni/ |
| `package-manager/` | 包管理与 APK 安装 | PackageManager | OH BMS / installd | BUILD.gn java/ jni/ |
| `appspawn-x/` | 混合进程孵化 + **bionic↔musl 翻译层**（`bionic_compat/`） | Zygote/进程孵化 | OH appspawn | BUILD.gn bionic_compat/ config/ java/ src/ test/ |
| `hwui-shim/` | 图形运行时 shim（HWUI / NDK → OH，含 GrAHB shim） | HWUI / Android NDK | OH 图形栈 | jni/ skia_compat_headers/ |
| `android-runtime/` | 渐进替代 `libandroid_runtime`，产出 `liboh_android_runtime.so` | libandroid_runtime | OH | etc/ include/ src/ |
| `jni/` | **`liboh_adapter_bridge.so` 的 JNI 入口**；`BUILD.gn` 是 bridge sources 的**权威清单** | JNI 边界 | — | BUILD.gn |
| `inet-shim/` | 网络 / inet 适配 | inet | OH | build.sh jni/ |
| `mainline-stubs/` | Android mainline 模块占位（仅 Java stub） | mainline modules | — | java/ |
| `CMakeLists.txt` | framework 构建聚合（部分模块） | — | — | — |

## 依赖方向（约定，防跨层扩散）
- `core/` 是底座，其它模块可依赖 `core/`；`core/` 不反向依赖具体桥。
- `appspawn-x/bionic_compat/` 是 bionic↔musl 翻译的落点，**同步原语/信号**相关改动优先在此，不要散到各桥。
- `jni/` 的 sources 以 `jni/BUILD.gn` 为准，**新增 .cpp 必须同步改 BUILD.gn**（编译脚本 `[BR-1]` 会 fail on drift；不要 glob）。
- 图形相关三处分工：`surface/`（Surface 节点桥）、`hwui-shim/`（HWUI/NDK shim）、`android-runtime/`（runtime 替代）——改图形前先分清改哪层。

## 改一个 IPC 桥的一般步骤
1. 在上表定位模块目录。
2. Java 侧改 `<模块>/java/`，native 侧改 `<模块>/jni/`。
3. 若该桥进 `liboh_adapter_bridge.so`，同步维护 `jni/BUILD.gn` sources。
4. 若涉及 OH/AOSP 上游源码，改 `../aosp_patches/` 或 `../ohos_patches/` 下对应镜像路径的 `.patch`（注意 codex 可能锁定部分 BMS/installd 补丁，见 `../COORDINATION.md`）。
5. 按 `../BUILDING.md` 重编，确认 **strict link** 通过。
