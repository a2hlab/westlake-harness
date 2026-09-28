# KNOWN_ISSUES.md — 能力范围 + 单目录自包含缺口登记

> 目的：区分"设计目标 / 已构建 / 已真机验证 / 尚未闭合"，并集中登记单目录"无外链"的已知缺口，避免把特定结果泛化成普遍承诺。
> 建立日期 2026-07-10。权威细节在 `BASE_VERSIONS.md` §三 与 `PROVENANCE.md`；本文件是它们的**导航索引**，冲突以那两份为准。

---

## 1. 能力范围四分（别把目标当已证）

| 范围 | 状态 | 说明 |
|---|---|---|
| **设计目标** | 目标 | 让**任意**未修改 Android/Unity APK 在 OH 6.1 arm64 上屏可交互；修复做在通用适配层 |
| **当前标的** | 进行中 | 具体推进 `CardWords`（Unity 2022.3.62f2, arm64-v8a）；不代表任意 APK 已支持 |
| **已构建（host）** | 部分 | `liboh_adapter_bridge.so` arm64 可 strict link（见 `VERIFICATION.md`） |
| **已真机验证** | 未闭合 | 楼层进度见 `HANDOFF_L04_L14.md` / `COORDINATION.md` §3；`truly-cold` 尚未达成 |

> 结论：README 的"把未修改 APK 直接跑起来"是**设计目标 + 当前主攻方向**，不是"对任意 APK 的完成承诺"。单个 app（CardWords）的进展不自动泛化到 02-20 其它标题（尤其 v7a-only 标题需独立 32-bit spawner/runtime，见 COORDINATION §5.7）。

## 2. "单目录无外链"已知未闭合缺口（诚实清单）

| # | 缺口 | 影响 | 是否阻塞 bridge 编译 | 权威出处 |
|---|---|---|---|---|
| 缺口A | 目标 6.1.0.31 vs 实际构建基座 api24 头偏差；6.1.0.31 头镜像软链已删，仅剩 4 头 overlay 兜底 | ~13 个 appmgr/zidl 头代际差异**无 override 保护、编译期发现不了**，运行时布局/parcel 可能与真机不一致 | 否（编过，但静默正确性风险） | `BASE_VERSIONS.md` §三·风险①；`build/oh_headers_631_overlay/README.md` |
| 缺口B | `out/aosp_lib64`（22+ 个 AOSP native `.so`）无法从本仓库源码自产 | 作为**预构建输入**被消费；本机 OH_ROOT 从未为 arm64 跑过 ninja，无 musl aarch64 sysroot | 否（bridge 消费其产物，不重编它） | `BASE_VERSIONS.md` §三；`PROVENANCE.md:655-820` |
| 缺口C | AOSP 整套精确 tag/commit/build-id 未记录（仅大版本 14；minikin 三件套有 `android-14.0.0_r1`） | 精确可复现未达成 | 否 | `BASE_VERSIONS.md` §二 |
| 缺口D | ②stub 源(Jun-13) ↔ ④设备(6.1.0.31/Jun-02) patch 级一致性待设备 dynsym/build-id diff | 符号集预期一致但未独立证实 | 否 | `STUBS_MANIFEST.md:63-76`（PENDING codex）|

## 3. 闭合条件（要达成"完全可复现 + 无外链"还需）
1. 拿到可编译的 6.1.0.31 代次 OH 树/SDK，或把完整 13k 头 `oh_mirror` 正式 vendor 进仓库接入 `INCS`（替代已删软链）。
2. 对 ~13 个 appmgr/zidl 差异头逐个 api24↔6.1.0.31 diff，对齐 marshal 结构体。
3. 为 arm64 product 真正 ninja 构建过的 OH 树，补 musl sysroot（缺口B）。
4. AOSP 整套精确 tag/commit/build-id（缺口C）。
5. codex 设备侧 dynsym/build-id diff（缺口D）+ 最终 `truly-cold` 验证。

## 4. 维护约定
- 新发现的缺口在此登记（编号 + 影响 + 是否阻塞编译 + 权威出处 + 闭合条件），并在 `BASE_VERSIONS.md`/`PROVENANCE.md` 落权威细节。
- 本文件只做索引，**不复制**权威数据（哈希/行号以那两份为准），避免双写漂移。
