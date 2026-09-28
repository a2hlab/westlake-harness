# framework/DEPENDENCIES.md — 模块编译依赖 / 运行时调用方向 / 产物归属

> 目的：回答"我把代码放对了目录，但它进哪个产物、能不能依赖别的模块、谁在运行时调它"。
> 建立日期 2026-07-10。模块职责见 `README.md`；构建见 `../BUILDING.md`。

---

## 1. 产物归属（模块源码最终进哪个 .so / .jar）

adapter 自有产物（其中 armv7 走 `build_adapter.sh` 的 target，见 `../build/build_adapter.sh`）：

| 产物 | 主要来源模块 | 说明 |
|---|---|---|
| `liboh_adapter_bridge.so` | `jni/`（入口）+ 各桥 `*/jni/` 中被 `jni/BUILD.gn` 收录的 sources | **sources 权威 = `jni/BUILD.gn`**，勿 glob（`[BR-1]`）。**arm64 单目录不经顶层 `build_adapter.sh`**（那条 dispatch 走 armv7），改用受保护直接调用 `compile_oh_adapter_bridge_arm64.sh`，见 `../BUILDING.md` §2 |
| `liboh_android_runtime.so` | `android-runtime/` | 渐进替代 libandroid_runtime |
| `libapk_installer.so` | `package-manager/`（native 侧） | APK 安装 native |
| `oh-adapter-framework.jar` / `oh-adapter-runtime.jar` | 各模块 `*/java/` | Java 侧适配 |

> 关键：一个 `*/jni/*.cpp` 是否进 `liboh_adapter_bridge.so`，**取决于它是否被 `jni/BUILD.gn` 的 sources 收录**，不是"放进 framework/ 就自动进"。新增/删除 native 源必须同步改 `jni/BUILD.gn`，否则构建脚本 post-flight 会 fail on drift。

## 2. 编译依赖方向（允许 / 禁止）

```
                 core/  (公共底座: OHEnvironment 等)
                   ▲   ▲   ▲
     ┌─────────────┘   │   └──────────────┐
  activity/ window/ surface/ broadcast/ contentprovider/
  package-manager/ ...  (各功能桥, 可依赖 core/)
                   │
  appspawn-x/bionic_compat/  ← bionic↔musl 翻译落点(同步原语/信号集中此)
                   │
  hwui-shim/ / android-runtime/ / surface/  ← 图形三层, 分工别混
```

规则：
- **允许**：功能桥 → `core/`（单向）。
- **禁止**：`core/` 反向依赖具体桥；功能桥之间横向 include 共享全局状态（易扩散重复 shim）。
- **bionic↔musl** 改动集中在 `appspawn-x/bionic_compat/`，不要散到各桥的 jni。
- **图形三层分工**：`surface/`（Surface 节点桥）、`hwui-shim/`（HWUI/NDK shim）、`android-runtime/`（runtime 替代）——改图形先分清改哪层，别跨层塞。

## 3. 运行时调用方向（大致）
```
Android app (bionic)
  → JNI → liboh_adapter_bridge.so (jni/ + 各桥)
    → OH inner_api (AbilityManager / WindowManager / RenderService / BMS / CommonEvent / DataShare …)
  ↑ 进程孵化: OH appspawn → appspawn-x (bionic_compat 翻译) → app 进程
```

## 4. 改动检查清单
1. 定位模块（`README.md` 表）。
2. Java 改 `*/java/`，native 改 `*/jni/`。
3. native 进 bridge → 同步 `jni/BUILD.gn`。
4. 依赖方向合规（只向 `core/`，不横向、不反向）。
5. 涉及上游源码 → 改 `../aosp_patches/` 或 `../ohos_patches/`（注意 codex 锁，见 `../COORDINATION.md`）。
6. 按 `../BUILDING.md` 重编，按 `../VERIFICATION.md` 验收。
