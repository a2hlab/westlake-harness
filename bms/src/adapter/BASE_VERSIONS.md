# BASE_VERSIONS.md — adapter 依赖的 OH / AOSP 基座版本唯一权威清单

> 本文件是 `/opt/21.Game/02.unity.cardwords/adapter` 依赖的外置 OH / AOSP 源码基座
> **精确版本身份的唯一权威来源**。`COORDINATION.md` 会按 30000 字节 / 400 行阈值轮转，
> 其中的版本行**不作权威**；本文件不轮转，版本变更时**在此更新**。
>
> 生成方式：只读扫描 adapter 全目录，只认能落到「具体文件:行号 / sha256 / Build ID /
> git tag / mtime」的证据。抽不到的一律标「未记录 / 待确认」，不编造版本号。
> 生成日期：2026-07-10。证据强度分三级：**实测**（本仓库文件字节 / 脚本变量直证）、
> **记录**（PROVENANCE / MANIFEST 等文档陈述）、**待确认**（无法在本目录内独立证实）。

---

## 0. 权威目标版本（最显眼处，一切偏差以此为基准）

> **adapter 的目标基座 = OpenHarmony 6.1.0.31（设备运行时口径）+ AOSP 14。**

### 用户架构冻结（2026-07-11）

- 决策号：`L01-02-VERSION-FREEZE-20260711`。
- **02 当前目标版本固定为 `OpenHarmony 6.1.0.31 + AOSP 14`**；未经用户新的明确
  架构决策，不得漂移、自动升级或用 api24 / 6.1.0.105 等构建输入身份改写目标版本号。
- “目标版本固定”只消除版本号选择歧义，不冒充 single-generation 已闭环。头 oracle、
  SDK、stub source、AOSP prebuilt/JAR、设备 runtime 的实际身份仍按下文分别记录，并须
  在 public baseline 发布前收敛到同一可复现代次。
- 决策原话与证据上限见
  `research/architecture-six-way/evidence/L01-version-freeze-20260711.md`。

- **目标 OH = OpenHarmony 6.1.0.31 `wukong100` arm64**，设备构建时间戳
  `wukong100_20260602_1011`（Jun-02）。出处：`third_party/oh_stubs/STUBS_MANIFEST.md:65-68`
  （记录，标注 device_verified by codex / shared memory Q3）。
- **目标 AOSP = 14（大版本）**；本仓库能落到的最精确 tag 引用是 `android-14.0.0_r1`
  （见 §二）。API level 34。

**★头号结论（详见 §三·风险①）**：目标版本已经明确固定，但 adapter 当前的
**实际构建基座尚未闭合到 6.1.0.31**。
它实际是**对 api24 代次的 OH 头 + Jun-13 wukong100 arm64 stub 符号集**构建的，
`PROVENANCE.md` 自己也承认「从 api24 解析、真机是 6.1.0.31、运行时结构体布局可能
不一致」。这是**最大的、尚未闭合的可复现 / 正确性缺口**。

---

## 一、OH（OpenHarmony）——四个身份分别钉死

adapter 触及的 OH 有**四个互不相同的版本身份**，绝不能混为一谈。四者**不是同一次构建**。

### ① 头 / 源码编译 oracle（编 bridge / adapter 时头文件从哪解析）

| 项 | 值 | 出处 | 强度 |
|---|---|---|---|
| OH 源码树代次 | **api24 代次**，`sdk_version = 26.0.0.18` | `build/oh_headers_631_overlay/HEADERS_MANIFEST.md:57`；`PROVENANCE.md:119,134-136` | 记录 |
| 参照树路径 | `/opt/10.Project/16-WestLake/16.12-HanBing/oh`（外置，本机唯一带完整 `prebuilts/clang/ohos` + 已 build `out/`） | `HEADERS_MANIFEST.md:57`；`PROVENANCE.md:118-120` | 记录 |
| armv7 目标产物目录 | `$OH_ROOT/out/rk3568`（DAYU200 / RK3568 板级；已 ninja 构建，`out/rk3568/gen` 4726 gen 头，mtime 2026-04-17） | `build/config.sh:19-20`；`compile_oh_adapter_bridge.sh:137`；`HEADERS_MANIFEST.md:57` | 实测（脚本变量）|
| arm64 目标产物目录 | `$OH_ROOT/out/wukong100` | `compile_oh_adapter_bridge_arm64.sh:167,244-248` 等 | 实测（脚本变量）|
| 为何是它 | 本机唯一一棵可编译的完整 OH 源码树就是这棵 api24 树；6.1.0.31 代次本机无完整可编译 SDK / 源码 | `PROVENANCE.md:136-139` | 记录 |

**6.1.0.31 偏差的补偿机制（部分、且在本仓库内失效）**：arm64 bridge 脚本
`compile_oh_adapter_bridge_arm64.sh:484-504` 设计了一个「device-version (6.1.0.31)
header SHADOW」：把一份 13k 头的 `oh_mirror` 前置 `-I` 以覆盖 api24 头。
**但该镜像路径 `$ADAPTER_ROOT/local_oh_headers/oh_mirror` 在本仓库中不存在**
（vendor 时那个软链接已被删除，`PROVENANCE.md:36-38`；本轮 `ls` 实测确认无此目录），
脚本因此走 `:504` 的 `WARN: 6.1.0.31 header mirror not found — bridge may carry
api24 parcel skew` 分支。真正落在本仓库内、替代 13k 镜像的只有
`build/oh_headers_631_overlay/` 下**4 个** 6.1.0.31 接口头（见 §三·风险①）。

### ② stub 符号源（`third_party/oh_stubs/` 27 个链接期符号 stub 的来源构建）

| 项 | 值 | 出处 | 强度 |
|---|---|---|---|
| 符号源树 | `/opt/10.Project/16-WestLake/16.13-Yue/local-arm64-build-YUE/oh61-wukong100/out/wukong100/packages/phone/system/lib64` | `STUBS_MANIFEST.md:57` | 记录 |
| product / arch | OpenHarmony 6.1 **`wukong100` arm64 (aarch64)** | `STUBS_MANIFEST.md:58` | 记录 |
| 构建日期 | **~2026-06-13/14**（per-lib mtime） | `STUBS_MANIFEST.md:59` | 记录 |
| 逐库 sha256 / Build ID | 27 库全部有，见 `STUBS_MANIFEST.md:84-112` 表（例：`librender_service_base.z.so` sha256 `a585c962…d082` / BuildID `761fbb51…`；`libwm.z.so` `4d79d815…096e` / `39fd3bb6…`） | `STUBS_MANIFEST.md:84-112` | 实测（本仓库表）|
| 符号解析等价性 | 27 stub 对 bridge 457-UND 名集给出与真库**完全一致**的解析结果（0 missing / 0 extra 逐库 parity） | `STUBS_MANIFEST.md:49-51,133-151` | 记录 |

### ③ 构建工具链 SDK（cross clang / musl sysroot）

| 项 | 值 | 出处 | 强度 |
|---|---|---|---|
| OH SDK 版本 | **6.1.0.105 / api23** | `STUBS_MANIFEST.md:60`；`compile_oh_adapter_bridge_arm64.sh:226,234` | 记录 |
| clang | `clang 15.0.4`（`llvm-project b3ff6d5a`） | `STUBS_MANIFEST.md:60` | 记录 |
| SDK 路径 | `/opt/17-TestLab/17.03-D600/apps/d600-sdk-full/native` | `STUBS_MANIFEST.md:60` | 记录 |

### ④ 目标设备运行时（生产口径 = §0 权威目标）

| 项 | 值 | 出处 | 强度 |
|---|---|---|---|
| 设备 OH 版本 | **6.1.0.31 `wukong100` arm64** | `STUBS_MANIFEST.md:65` | 记录（codex device_verified）|
| 设备构建时间戳 | `wukong100_20260602_1011`（Jun-02） | `STUBS_MANIFEST.md:65` | 记录 |

### ★ 四身份对齐分析（是否同一次构建？）

**否，四者是四次不同构建**：

| 身份 | product/代次 | 构建实例 |
|---|---|---|
| ① 头 oracle | api24（sdk 26.0.0.18）rk3568 / wukong100 | HanBing OH 树，out mtime 2026-04-17 |
| ② stub 符号源 | 6.1 wukong100 arm64 | Yue 树，~Jun-13/14 |
| ③ SDK 工具链 | 6.1.0.105 / api23 | D600 SDK |
| ④ 设备运行时 | **6.1.0.31** wukong100 arm64 | 设备，Jun-02 |

**已知 ABI / 布局不一致风险**（未闭合）：

- **①(api24 头) ↔ ④(6.1.0.31 设备)**：`PROVENANCE.md` 自承的核心偏差。已在 2 个
  IPC 接口方法上实锤参数个数不同（`ScheduleMemoryLevel` 2→1、
  `NotifyAppForceLandscapeConfigEnableUpdated` 1→0，`PROVENANCE.md:179-187`），
  另有 ~13 个 `appmgr/` + `zidl/` 头在两代之间也不同但**未被 override 保护、编译期
  发现不了**（`PROVENANCE.md:248-261`）。详见 §三·风险①。
- **②(Jun-13) ↔ ④(Jun-02)**：同为「6.1 wukong100 arm64」product 但**不同构建实例**。
  对「导出符号集」（stub 唯一需要的东西）预期一致，但**是否为设备所跑的精确
  6.1.0.31 patch，本目录内无法独立证实**。`STUBS_MANIFEST.md:63-76` 明确标注
  **PENDING: codex 设备只读 per-lib dynsym / build-id diff 确认**。
- 综合判定：**未闭合，待 codex 设备只读 dynsym / build-id diff 确认**（零设备纪律，
  5eab/5bb5b 属 codex，本文件不碰设备）。

---

## 二、AOSP

| 项 | 值 | 出处 | 强度 |
|---|---|---|---|
| 源码大版本 | **AOSP 14** | `aosp_patches/README_AOSP_PATCHES.txt:7`；`app/BUILD_INSTRUCTIONS.md:136` | 记录 |
| **精确 tag（唯一落地证据）** | **`android-14.0.0_r1`** —— 仅覆盖 minikin / harfbuzz_ng / freetype 三个子项目的拉取 | `build/inner/fetch_minikin_deps.sh:16`（`BRANCH=android-14.0.0_r1`，`git clone --depth 1 --branch`） | 实测（脚本变量）|
| API level | **34**（compileSdk 34 / targetSdk 34 / minSdk 21；Android 14 = API 34） | `app/BUILD_INSTRUCTIONS.md:53,57-58,136` | 实测（仅测试脚手架 app，见下注）|
| 消费的产物：`out/aosp_lib` / `out/aosp_lib64`（~22 个预编译 AOSP native `.so`：`libart.so` / `libnativehelper.so` / `libandroidfw` / `libbase` 等） | 来源版本 tag / build-id **未记录** —— 作为「外部预构建输入」只读消费，本仓库无法从源自产（arm64 交叉编译脚本活在兄弟项目，未 vendor） | `PROVENANCE.md:307-321,570-581,606-618` | 待确认 |
| 消费的产物：AOSP Soong turbine header jar（`framework-minus-apex.jar` / `core-oj.jar` / `core-libart.jar`）+ `d8` | 来源 tag / build-id **未记录**；由 `~/aosp-local` 现场 Soong 构建产出，无版本锚 | `PROVENANCE.md:396-426`；`compile_fresh_jars_manifested.sh:169-171` | 待确认 |
| `third_party/aosp_raw/` 8 个零 diff 上游文件（GLES20/30/31 + asset_manager + EGL/KHR 头） | 无 tag，但有逐字节 md5（例 `android_opengl_GLES20.cpp` = `aeab0f3e…`） | `third_party/aosp_raw/README.md:32-41` | 实测（md5）|

**注**：`app/AndroidManifest.xml` 是 `com.example.helloworld` 测试脚手架（无
`android:*SdkVersion` 属性），**不能**作为真机 APK 的 API level 佐证；上表 API 34
来自同目录 `BUILD_INSTRUCTIONS.md` 的 Gradle 配置。真正的生产标的是
**Unity 2022.3.62f2 的 CardWords APK**（`com.CardWordsStudio.CardWords`，
sha256 `435f0eb…10626`，dual-ABI arm64-v8a + armeabi-v7a，`COORDINATION.md:22-26`），
其自身 targetSdk/minSdk 未在本目录记录。

**AOSP 结论**：**仅精确到大版本 14**；唯一 tag 级证据 `android-14.0.0_r1` 只覆盖
minikin 三件套，**不代表整套 aosp_lib / framework jar 的精确 tag**。整体
**精确 tag / commit / build-id 待补**。

---

## 三、可复现缺口清单（诚实）

### 已精确钉死（可逐字节复现）

- **② stub 符号源**：27 库逐库 sha256 + Build ID + product + arch + mtime + 生成命令，
  全在 `STUBS_MANIFEST.md`。（相对 Jun-13 wukong100 树可复现。）
- **③ SDK 工具链**：6.1.0.105 / api23 / clang 15.0.4 / llvm b3ff6d5a / 精确路径。
- **`third_party/aosp_raw/` 8 文件**：逐字节 md5。
- **`build/oh_headers_631_overlay/` 4 头**：内容 + 来源（6.1.0.31 oh_mirror 快照）钉死。

### 只有大版本 / 参照路径，无精确 patch tag

- **① 头 oracle**：知道是「api24 / sdk 26.0.0.18 / HanBing 树 / out mtime 2026-04-17」，
  但这是**参照树身份**，非 git commit / repo manifest 级锚定。
- **② ↔ ④ 的 patch 级一致性**：stub 源（Jun-13）与设备（6.1.0.31 / Jun-02）是否同一
  patch，**待 codex 设备只读 dynsym/build-id diff**。
- **AOSP 整体**：大版本 14；只有 minikin 三件套有 `android-14.0.0_r1`。

### 完全未记录 / 待确认

- **★风险①（头号，正确性 + 可复现双待闭合）：目标 6.1.0.31 vs 实际构建基座 api24 的偏差**
  - **偏差本质**：adapter 源码的最新改动（`[S24 cut9]`）是**按 6.1.0.31 接口形状**写的
    override，但本仓库唯一可用的编译 oracle 是 **api24 头**。
  - **偏差有多大 / 涉及哪些头**：
    - **已定位并修补** 2 个方法（`app_scheduler_interface.h` 的 `ScheduleMemoryLevel`、
      `session_stage_interface.h` 的 `NotifyAppForceLandscapeConfigEnableUpdated`）——
      靠 `build/oh_headers_631_overlay/` 4 头覆盖，编译期触发 `override` 错误故已闭合。
    - **未修补、静默风险**：`appmgr/` 下 ~11 个头（`ams_mgr_interface.h`、
      `app_jsheap_mem_info.h`、`app_mem_info.h`、`app_mgr_client.h`、`fault_data.h`、
      `running_process_info.h` 等）+ `zidl/` 下 `session_stage_proxy.h`、
      `session_stage_ipc_interface_code.h` 在 api24 与 6.1.0.31 之间**也不同**，
      **未 vendor 进 overlay**、adapter 无 `override` 触发编译检查 →
      **编译不报错，但运行时结构体布局 / IPC parcel 可能与真机 6.1.0.31 不一致**
      （`PROVENANCE.md:248-261`）。
    - **补偿机制在本仓库失效**：13k 头的 6.1.0.31 `oh_mirror` SHADOW 机制
      （`compile_oh_adapter_bridge_arm64.sh:484-504`）依赖的
      `local_oh_headers/oh_mirror` **在本仓库不存在**（软链接已删），单目录构建时
      脚本落 `WARN … api24 parcel skew` 分支，仅剩 4 头 overlay 兜底。
  - **已知风险等级**：这是「没有 `override` 关键字保护、编译期发现不了」的静默 ABI
    偏差，**未逐个排查**（`PROVENANCE.md:261`）；静态 `nm -C` 符号核对通过 ≠ 运行时
    vtable-slot / 布局正确，**最终需 truly-cold 真机验证**（`PROVENANCE.md:243-247`）。
  - **要让构建基座真正对齐 6.1.0.31 还需**：
    1. 拿到一棵**可编译的 6.1.0.31 代次 OH 源码树 / SDK**（本机目前无，
       `PROVENANCE.md:136-139` 已搜证），或
    2. 把完整的 6.1.0.31 `oh_mirror`（13k 头）正式 vendor 进本仓库并接进
       `INCS`（替代已删软链接），而非只留 4 头 overlay；且
    3. 对 §三所列 ~13 个 `appmgr/`+`zidl/` 差异头逐个做 api24↔6.1.0.31 diff，把
       adapter 实际 marshal 到的结构体全部对齐 6.1.0.31；最后
    4. codex 在 6.1.0.31 设备上做 truly-cold 运行时验证（vtable-slot / parcel 布局）。
- **`out/aosp_lib64`（arm64）无法从本仓库源码自产**：22+ 个 AOSP native `.so` 的 arm64
  交叉编译脚本原活在兄弟项目 `/opt/1F.Application/02.Noice/adapter/build/inner_arm64_5583/`，
  已 vendor 进 `build/inner/` 但**跑不通**——更深的第三缺口：本机 `OH_ROOT`（HanBing 树）
  **从未为任何 arm64 product 跑过 ninja 构建**，`out/wukong100/obj/third_party/musl/usr/include`
  为空，无 musl aarch64 sysroot（`PROVENANCE.md:655-820`）。「0 外链自包含」判定
  **未达成**。
- **AOSP 整套精确 tag / commit / build-id**：待补。
- **CardWords 生产 APK 自身 targetSdk / minSdk**：本目录未记录。

### 要达成「完全可复现」还需补的精确锚

1. OH ① 头 oracle 的 git commit / repo manifest（或改用可编译的 6.1.0.31 树）。
2. OH ②↔④ 的设备侧 per-lib dynsym / build-id diff（codex，零设备解锁后）。
3. AOSP 整套（aosp_lib + framework jar）的精确 tag / commit / build-id。
4. 一棵为 arm64 product 真正 ninja 构建过的 OH 树（补 musl sysroot 第三缺口）。

---

## 四、维护约定

- 本文件是 adapter 依赖的 OH / AOSP 基座版本的**唯一权威来源**。
- `COORDINATION.md` 按字节 / 行数阈值轮转，其版本行**不作权威**；两者冲突以本文件为准。
- 基座版本（OH 目标 / stub 源 / SDK / AOSP tag）发生变更时，**在此文件更新**并注明出处
  文件:行号与证据强度，不要只改 `COORDINATION.md`。
