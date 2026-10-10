spec: task
name: "Local arm64 build chain for liboh_adapter_bridge"
inherits: project
---

## 意图

把 `liboh_adapter_bridge.so`(arm64)的构建链在本机补齐:找回当时的构建输入,在本机容器里逐字节复现已部署的件,让 BoatAttack 需要的渲染补丁(SET_BUFFERS_GEOMETRY、pixel_format_mapper、UNITY-LANDSCAPE)能从源码编进 adapter,而不是依赖来历说不清的预编件。符合 AGENTS「上板产物连同源码快照、补丁、工具链哈希、构建脚本与原始构建日志一起留存」。

## 已定决策

- 复现目标两件:U13 部署件 `84695d62`(boat-repro Aug-09 预编件,原字节在 hw248 `/home/alvin/westlake-oh6.1-lab-state-20260930/vm-copies/bridge-84695d62/`,DIGEST 470)与 BoatAttack PASS 候选 `8ab85446`(boat-repro Aug-11,hw248 构建 run `boatattack-runtime-source-20260813T141442Z`)。
- 已知缺口(cc-t3 e17192802b `benchmark/2026-10-10-boat-pr03-render-port/rebuild/`):本仓 `compile_oh_adapter_bridge.sh` 只出 armv7,arm64 adapter 本机编不了;runtime 可在 `a2hlab-build:24.04` 容器用冻结 OHOS clang-15 编。
- 找构建输入的顺序(用户 2026-09-30 定):本机 Mac(`~/orca/workspaces/` 各树、vm-copies、00.Workspace 系列)→ OrbStack `orb -m a2hlab` → hw248;三处都没有才在 hw248 下载对应上游版本,不凭记忆补。
- 先复现再改:未逐字节复现 `84695d62` 或 `8ab85446` 之前,不出带补丁的新件;复现不了就列出差异(TU、符号、编译选项、链接顺序、build-id)并停报。
- 工具链用已证的冻结 clang(cx-build 证 `libapp_native_loader` eebd62f2 逐字节复现);容器与工具链 SHA 入回执。
- 大文件(源码快照 tar、中间对象)放 hw248 `/home/alvin/`,仓库记路径与 SHA;构建执行日志原样 tee 到持久位置。
- 并入「产物可重编门」(用户 2026-10-10 定):同一套机制推广到每个上板件(先 adapter 84695d62/8ab85446 与 runtime 18763dd4——runtime 的源码在本机 `westlake-harness-bms-deploy/benchmark/2026-09-30-n3b-webview/src/` 补齐 webview_publication.cpp 后由 cc-t3 复现),出一张表 `knowledge/gates/rebuildable-artifacts.json`:每件=SHA、源码快照、工具链、构建命令、最近一次复现结果;编不回来的标「锁死件」并写出处与缺口。门可定期重跑。

## 边界

### 允许修改
- benchmark/2026-10-10-adapter-buildchain/**
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

### 禁止
- 任何上板写操作;改冻结项;改 U13 部署件。

## 验收标准

场景: Build inputs are located and pinned
  测试: demo_baseline_adapter_buildchain
  假设 The two target adapters are pinned by SHA
  当 The build inputs are searched local then OrbStack then hw248
  那么 Each input (source snapshot, patch series, build script, toolchain, sysroot, link flags) has a location and SHA and the search log names every place looked

场景: Search falls back in the fixed order
  测试: demo_baseline_adapter_buildchain
  假设 An input is absent from the local Mac trees
  当 The search continues
  那么 The search log shows OrbStack checked before hw248 and an upstream download on hw248 only after all three missed

场景: Missing input stops before any build
  测试: demo_baseline_adapter_buildchain
  假设 A required input is found nowhere and has no upstream source
  当 The build step starts
  那么 It exits nonzero naming the missing input and no adapter binary is produced

场景: Deployed adapter is reproduced byte for byte
  测试: demo_baseline_adapter_buildchain
  假设 The pinned inputs and the frozen toolchain in the local container
  当 The arm64 adapter is built twice from a clean tree
  那么 Both builds equal 84695d62 or 8ab85446 byte for byte and the raw build logs are kept

场景: Rebuildability table marks locked artifacts
  测试: demo_baseline_adapter_buildchain
  假设 The deployed parts listed in the U13 runtime fingerprint
  当 The rebuild gate runs over them
  那么 Each part is marked reproduced or locked and every locked part names its provenance and the missing input

场景: Irreproducible build stops with a difference report
  测试: demo_baseline_adapter_buildchain
  假设 A rebuild does not match its target SHA
  当 The comparison runs
  那么 It exits nonzero and lists differing translation units symbols build-id and flags and no patched adapter is produced

## 排除范围

- 上板验证新 adapter;重编 runtime(另有 cc-t3 的复现门);改 BoatAttack 叠加路线。
