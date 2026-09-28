# GLOSSARY.md — adapter 术语表（团队黑话一处讲清）

> 目的：消除"只有原作者懂"的暗语。每条词条尽量给：**一句话定义 / 本工程中的具体含义 / 常见误解 / 相关目录或文档**。
> 建立日期 2026-07-10。新词条随工程演进在此补充，不要散落到各 README。

---

## 一、平台与运行时边界

### bionic ↔ musl 翻译
- **定义**：Android 用 bionic 作为 libc，OpenHarmony 用 musl。二者 pthread/信号/系统调用 ABI 不同。
- **本工程**：adapter 在 OS 边界把 Android app 的 bionic 期望翻译成 OH 的 musl 现实（如 pthread 同步原语内联布局、`futex` offset、`sigaction` sigset 大小）。核心原则：**优先在安装期/AOT 处理，运行时只做最小翻译**（保运行高效）。
- **常见误解**："只要符号能链接上就兼容了" ——错。符号解析通过 ≠ 结构体布局/vtable-slot 运行时正确。
- **相关**：`framework/appspawn-x/bionic_compat/`、`aosp_patches/art/sigchainlib/`、`PROVENANCE.md`。

### adapter bridge（`liboh_adapter_bridge.so`）
- **定义**：adapter 的 JNI 入口 .so，把 Android framework 的 JNI 调用桥到 OH inner_api。
- **本工程**：sources 权威清单是 `framework/jni/BUILD.gn`（**不要 glob**）；单目录 arm64 编译入口见 `BUILDING.md`。
- **常见误解**：以为随便加 .cpp 进 framework/ 就会被编进 bridge —— 实际必须与 BUILD.gn 对齐（见构建脚本 `[BR-1]`）。
- **相关**：`framework/jni/`、`build/inner/compile_oh_adapter_bridge_arm64.sh`。

### stub（符号 stub，`third_party/oh_stubs/`）
- **定义**：链接期占位库，提供与真实 OH 库**完全一致的导出符号集**，让 bridge 能在本机独立 link，而不必拥有整棵 OH 产物树。
- **本工程**：27 个 stub，逐库 sha256 + Build ID + parity 记录在 `STUBS_MANIFEST.md`。
- **常见误解**：stub 会进入运行路径 —— **不会**。stub 只解决**链接期**符号解析；运行时用的是设备上的真库。stub ≠ shim（shim 有真实行为、会跑）。
- **相关**：`third_party/oh_stubs/STUBS_MANIFEST.md`、`GLOSSARY.md#shim`。

### shim
- **定义**：有真实行为、会在运行时执行的适配薄层（区别于只占位的 stub）。
- **本工程**：如 `framework/hwui-shim/`（Android NDK→OH 桥接）、`framework/inet-shim/`、skia RTTI shim。
- **相关**：`framework/README.md`。

### header overlay（`build/oh_headers_631_overlay/`）
- **定义**：把少量 6.1.0.31（真机代次）接口头以 `-I` 优先命中，覆盖本机唯一可编译的、更老的 api24 代次 OH 头。
- **本工程**：仅 4 个接口头（`ScheduleMemoryLevel` 等两个方法签名对齐真机）。**刻意不 vendor** 其它有代际差异的头，避免引入未审计漂移。
- **常见误解**：overlay = 一整棵头树 —— 不是，只是 4 个文件的只读快照。
- **相关**：`build/oh_headers_631_overlay/README.md`、`BASE_VERSIONS.md` §三·风险①。

---

## 二、约束与合规

### 单目录约束 / "无外链"
- **定义**：编译单元只允许用①本目录 + ②外置 OH/AOSP 源码树与工具链（合规例外）；禁止其它兄弟项目代码进编译。
- **判定**：一个 .o/.so 的每个编译输入若不是"本目录 or 外置 OH/AOSP or 工具链"，即为**外链**，不合规。
- **本工程现状**：仍有已知缺口（arm64 AOSP 库无法从本仓库自产、6.1.0.31 头镜像软链已删），诚实记录在 `BASE_VERSIONS.md` §三 / `PROVENANCE.md`。
- **相关**：`PROVENANCE.md`、`BASE_VERSIONS.md`、`COORDINATION.md` §1。

### OH / AOSP 外置例外
- **定义**：单目录约束的**唯一合法外部**是外置的 OH/AOSP 源码树、SDK、工具链（通过 `OH_ROOT`/`AOSP_ROOT`/`ADAPTER_ROOT` 三个环境变量访问，可覆盖）。
- **相关**：`build/inner/compile_oh_adapter_bridge_arm64.sh` 头部注释、`BASE_VERSIONS.md`。

---

## 三、项目阶段语言

### L03 / L04 / L06 …（"楼层"编号）
- **定义**：把 APK-on-OH 上屏拆成自底向上、顺序钉死、每层有验收门的攻关阶梯。L03=单一安装路，L04=实验进程出生，L06=首墙 ABI/native 提取，L04–L14 交接见 `HANDOFF_L04_L14.md`。
- **常见误解**："到了 L04"没有可观察条件就各说各话 —— 楼层必须有明确 pass/block 判据（见 COORDINATION §3 裁决）。
- **相关**：`HANDOFF_L04_L14.md`、`COORDINATION.md` §3、`../RESEARCH_KANBAN.md`（在上级 `02.unity.cardwords/`，看板 agent 维护，勿改）。

### cut8 / cut9（代次）
- **定义**：adapter 源码 override 的"代次"标记，对应按哪一代 OH 接口形状编写（如 `[S24 cut9]` 按 6.1.0.31 接口形状写）。
- **常见误解**：cut 号 = OH 版本号 —— 不是，cut 是本仓库源码演进代次，与基座版本对齐关系见 `BASE_VERSIONS.md`。

### route B / baseline
- **定义**：route B 是一条历史技术路线（相关备份在 `_routeb_bak_*` / `_routeb_dev_bak/`，属**历史**）；baseline 指当前已回滚到的稳定生产态。
- **相关**：`LEGACY_CONTENT.md`。

### device_verified / truly-cold
- **定义**：`device_verified`=已在真机验证（codex 域）；`truly-cold`=真正冷启动（非热换、非手工 listener）验证，是最强验收级别。
- **常见误解**：符号 `nm -C` 核对通过就算验证 —— 不是，最终需 truly-cold 真机。

---

## 四、协同术语

### COORDINATION 轮转 / archive
- COORDINATION.md 超过 30000 字节 / 400 行就轮转到新版本（V1→V2→V3→…），全文只读归档在 `coordination/archive/`。**关键长期结论不要只留在轮转日志里**（会变得不可发现），应升级到 README/ARCHITECTURE/BASE_VERSIONS 等稳定文档。

### 设备锁 / 文件锁
- Claude 与 Codex 并发工作时，各自"锁定"一批文件/设备，另一方只读不改。当前锁清单在 `COORDINATION.md` §2。
