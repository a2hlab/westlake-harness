# wukong100 全量构建历史与快速校订

更新时间：2026-07-16。范围：AlexPC 上
`/opt/build-trees/oh610_lts_source` 的 OH 6.1 LTS、`wukong100/arm64`
`images` 构建。本文只记录可复核事实；host build PASS 不等于 PAC、刷机、
D600 冷启动或 Unity 首帧 PASS。

> **2026-07-19 新机执行警告**：本文出现的 `/opt/build-trees`、
> `/tmp/m04-bin` 和 `/home/alexyang` 是历史证据路径，不能在发布后的新机照抄。
> 新机只从 `/opt/21.Game/02.*` 内 regular directory 构建，并先运行
> `${PROJECT_ROOT}/_handoff/bin/preflight-wukong100-r45 "$OH_ROOT"`。

## 1. 2026-07-13 成功基线（“周末成功”真相）

成功尝试使用官方入口，而不是裸 Ninja：

```sh
cd /opt/build-trees/oh610_lts_source
./build.sh --product-name wukong100 --ccache -j2 \
  --gn-args linux_use_bundled_binutils_override=false \
  --prebuilts-sdk-gn-args linux_use_bundled_binutils_override=false
```

该入口实际发出：

```sh
/opt/build-trees/oh610_lts_source/prebuilts/build-tools/linux-x86/bin/ninja \
  -w dupbuild=warn -C /opt/build-trees/oh610_lts_source/out/wukong100 images
```

事实：watchdog 从 `-j4` 遇 OOM 后降到 `-j2`；第 8 次增量尝试成功，日志到达
`[20286/20286] .../images.stamp`、`wukong100 build success`，耗时
`1:12:07`。不要复制历史 watchdog 内容；以下身份已足够复核：

| 证据 | SHA256 |
|---|---|
| `/home/alexyang/auto_build_wukong100.sh` | `d88f38765167985827faf46c16e2ad9dc1f5ea0f70aa3c6d64fea4e6e25bd316` |
| `/home/alexyang/build_wukong100.log` | `90d6f3d4f3ef676b210dd0d6e762a79b34ea81f91d54a2bc50a3d779306ed9ed` |
| `/home/alexyang/autobuild_status.txt` | `3d924fa32fb0806ab77be0c8845087b5f4926edb6a8b71e73f430e13877b6b31` |
| `/opt/build-trees/oh610_lts_source/out/wukong100/build.1783903636.7541108.log` | `244ca03242ca5e062e3fd45b341fbba1ad2d01e5960d39a83e2fe6877f8c69d1` |

## 2. R6/R7/R9/R11 根因与正确修复

| 代次 | 首墙 | 已证根因 | 正确补丁边界 |
|---|---|---|---|
| R6 | `find component oh_adapter failed`（LOAD） | 产品配置请求 `oh_adapter`，但 LTS 基座和 generation-private OH 树均无该 subsystem/source registration；adapter 是 OH `images` 后注入的密封输入，不应再建第二棵 adapter source。 | 只在新鲜私有副本中、按输入 SHA/JSON 对象 fail-closed 删除陈旧 product request；不改 terminal R6。当前固定 R45 流程不再以“新代地址”制造该墙。 |
| R7 | `gfx_utils/geometry2d.h` missing | `foundation/arkui/ui_lite/ext/updater/BUILD.gn` 的官方依赖 `graphic_utils_lite:utils_lite` 被本地注释；provider/header 实际存在。 | 恢复官方 HEAD 那一行/整文件，不复制 header、不造 shim。当前文件已等于 HEAD。 |
| R9 | ACE webpack `FileNotFoundError` | dirty `build/ohos/app/app_internal.gni` 注释官方 `ace_loader_ark_hap`/`ets_loader_ark_hap` producers，并改为不存在的源码根路径；官方 API-23 prebuilt bytes 实际存在。 | 恢复 pinned HEAD，保持 `ohos_indep_compiler_enable=true`；禁止 npm/network/node_modules 手工复制。当前文件已等于 HEAD。 |
| R11 | es2panda `Can't find prefix for 'std/core'` 等 | dirty `build/config/components/ets_frontend/ets2abc_config.gni` 禁用了完整官方 ETS stdlib/API/ArkTS producer family；不是 stdlib 源码缺失。 | 恢复完整 pinned HEAD 文件；不能只补两行。当前文件已等于 HEAD。 |

正式 receipts：

- `/opt/21.Game/02.unity.cardwords/adapter/research/atoms/L03/A15/evidence/M04/20260715T1555-r6-terminal-oh-adapter/ROUND.md`
- `/opt/21.Game/02.unity.cardwords/adapter/research/atoms/L03/A15/evidence/M04/20260715T1629-r7-gfx-dependency-diagnosis-r8-launch/ROUND.md`
- `/opt/21.Game/02.unity.cardwords/adapter/research/atoms/L03/A15/evidence/M04/20260715T1726-r9-ace-rootcause-r10-launch/ROUND.md`
- `/opt/21.Game/02.unity.cardwords/adapter/research/atoms/L03/A15/evidence/M04/20260715T1825-r11-terminal-ets-stdlib-prefix/ROUND.md`
- `/opt/21.Game/02.unity.cardwords/adapter/research/atoms/L03/A15/evidence/M04/20260715T1859-r12-staged-preflight-integration/ROUND.md`

## 3. R45 BMS 与 mission 修复

- BMS：本地 `installd_operator.cpp` 调用了未声明/未定义的
  `IsValidBundleName`。已在 BMS 边界内补齐经审阅的命名校验定义；精确
  `installd_operator.o` target rc=0。该文件仍是有意 adapter dirty，不能误还原。
  Receipt：`20260716T0703-r45-bms-undeclared-validator/ROUND.md` 与
  `20260716T0709-r45-bms-validator-fix-build-active/ROUND.md`。
- mission：dirty `mission_list_manager.cpp` 调用 `Mission` 中不存在的
  `PushAbility`、`SetMultiAbilityMode`、`IsMultiAbilityMode`、
  `GetAbilityStackSize`、`PopAbility`；根因是实现/API 三文件只同步了一部分。
  已让 `mission_list_manager.cpp`、`mission.h`、`mission.cpp` 成为一致的三件套，
  精确 `mission_list_manager.o` target rc=0。三件均仍是有意 adapter dirty。
  Receipt：`20260716T0720-r45-ability-mission-member-wall/ROUND.md` 与
  `20260716T1002-r45-adapter-pass-full-build-active/ROUND.md`。

## 4. AlexPC 临时日志账本

早期一批错误只留在 `/tmp` 日志和相邻 `.m04-r45-before*` 备份中；本表是其
耐久索引。SHA 是 2026-07-16 的只读核验值。

| 日志绝对路径 | SHA256 |
|---|---|
| `/tmp/m04-r45-ninja.log` | `60b4b1ccca29fa62114ad76d9bac2a3b86875e8cbbf2778ab0fefc0731f5db29` |
| `/tmp/m04-r45-ninja-rerun.log` | `57d26b7146e56b9e8aa24faed89aa86b0848261e1a406dce8ec89ec613838ef9` |
| `/tmp/m04-r45-ninja-final.log` | `6960a1442ab52c4b1047fa8a489c2355a9bfef24b7a58473aeb6493cf726be94` |
| `/tmp/m04-r45-ninja-libcgark-fix.log` | `b687f6b23ba764d6766e72359a62771d19ff5fe7b232d3486cc090a108ad664a` |
| `/tmp/m04-r45-ninja-generated-hiview-fix.log` | `90c36942680538d8bee44bff4c0544610125813159aafdc1d468de7eef2355cb` |
| `/tmp/m04-r45-ninja-battery-test-fix.log` | `ea1a9988ce58c1175c59b143508221cbbb8813d0ec4bb3fa522505d9cf5c8dcd` |
| `/tmp/m04-r45-ninja-wrapper-fix.log` | `19eefa19995651e254ed980902d6bd6e432421830569d373b1b4046c68b70766` |
| `/tmp/m04-r45-ninja-appspawn-fix.log` | `5a24847f5926c3225c8c805a3f49426521570470fcccecf7f99bd1b955391897` |
| `/tmp/m04-r45-ninja-cjappspawn-fix.log` | `67a86206576a590c6da31efe1e3889e4cfc0cde37de66050e0e75b5fd1c3445e` |
| `/tmp/m04-r45-ninja-nativespawn-fix.log` | `6fd3e6eb3ac8c06faadba2896a02d8ad720ce1f631817f6692361b145b2b7955` |
| `/tmp/m04-r45-lts-restored-xperf.log` | `91289b703e0a158707c16425cb9b5437fb7e28fa21dba5e9b0d0b98cca76a715` |
| `/tmp/m04-r45-lts-prebuilt-python.log` | `efcba2e75e5012125ad7a966df0d61e712d2d07920d18497da16461577725f6e` |
| `/tmp/m04-r45-lts-pythonpath.log` | `25ffcfe1df254f97563fefa3834a00174a7c48ed832c0b4a252beb78eeb3c20d` |
| `/tmp/m04-r45-final-full-v2.log` | `7f2fff35d64def4c4460027b3d6e5fd31e8b72e4ff9a7d327e6891dbe16a672c` |
| `/tmp/m04-r45-final-full-v3.log` | `b5c7054b4fc7a170fb18d9ea3e3985696f991900caa5da0757e36502c3b398bb` |

## 5. 当前分类

### Fixed（先校验，禁止再“修”）

- `build/ohos/app/app_internal.gni`：等于 HEAD，SHA
  `595c739b0741f9fbc1e32990cb1d95bee37bd2fd68daae17e65b726ff44edd1c`。
- `build/config/components/ets_frontend/ets2abc_config.gni`：等于 HEAD，SHA
  `28fc4cdcd620fda21c3cb6728d5cfc6a40f0162b93247f2ab86c2c5d4d763867`。
- `foundation/arkui/ui_lite/ext/updater/BUILD.gn`：等于 HEAD，SHA
  `2a59138648ef7e8771836ea532c7effde7c1fb7387f45bdd74f1bf1cfcc81e13`。
- Python/json5 环境：使用下一节固定的 `PATH` 和 `PYTHONPATH`。

### Still-dirty（已知本地差异，恢复前必须逐项审计）

- 有意 adapter 实现：BMS `installd_operator.cpp`；mission 三件套。
- 构建 loader：`build/hb/util/loader/load_ohos_build.py`，放宽若干
  subsystem/linkfile 检查；不是官方 LTS bytes。
- 本地裁剪：`applications/standard/hap/BUILD.gn`、
  `arkcompiler/ets_runtime/.../maple_be/BUILD.gn`、
  `base/powermgr/battery_manager/test/systemtest/BUILD.gn`、
  `base/request/request/frameworks/ets/ani/request/BUILD.gn`、
  `base/startup/appspawn/standard/BUILD.gn`。
- `appspawn/standard` 的三个 rc target 是重复/坏路径；正确 cfg producer 在
  `base/startup/appspawn/BUILD.gn`。不要把整文件恢复当成当然正确。

### Optional-only / bare-Ninja-only（不得阻塞正式 `images`）

- 缺失 media HAP：`Media_Library.hap`、`Media_Scanner.hap`、
  `Ringtone_Library_Ext.hap`。
- Maple：`libcgark`、`src/cg/ark/foo.cpp`、
  `cg_stackmap_computation.cpp`。
- battery systemtest、request ANI `src/wrapper.rs`。
- standard appspawn 重复 `appspawn/cjappspawn/nativespawn.rc`。
- Hiview xperf static/`hiviewparam_update` 陈旧路径，以及
  updateservice `updater_sa.rc` 陈旧路径。

这些墙来自早期“裸 Ninja/default-all”扫描；它们未出现在当时正式 `images`
闭包中。若未来真实 `images` 首错命中其中之一，再以当次 graph/command/log
升级为事实墙；此前不得继续靠 `if(false)` 扩大裁剪。

## 6. 历史入口与新机唯一执行入口

**禁止**执行 `ninja -C out/wukong100` 或其它无 target 的 bare Ninja。2026-07-13
成功基线走 §1 的 `build.sh`；2026-07-16 最终暖树续编也走 `build.sh`，显式
`--build-target images`。早期曾用过 `python3 build.py -p wukong100` 和
`/tmp/m04-bin/python`，它们只保留为 provenance，不是新机入口。

新机首次 clean rebuild 只执行
[`../../_handoff/history/alexpc-build-recovery-20260719/ERROR_ATLAS.md`](../../_handoff/history/alexpc-build-recovery-20260719/ERROR_ATLAS.md)
“正式构建入口”的命令：显式项目内 `OH_ROOT`、`build.sh`、`images`、durable
wrapper 和 `BUILD_NJOBS`。默认 `BUILD_NJOBS=2` 是保守 cold baseline；历史最终
`-j30 --ccache --fast-rebuild` 只证明一轮暖树续编成功，不能直接套到 clean build。

## 7. 60 秒快速 preflight

在 AlexPC 最终目录发布后执行；任何一项失败都先停止，不进入全编译：

```sh
PROJECT_ROOT=/opt/21.Game/02.unity.cardwords
OH_ROOT="$PROJECT_ROOT/.work/source-snapshots/oh-6.1.0.31"
"$PROJECT_ROOT/_handoff/bin/preflight-wukong100-r45" "$OH_ROOT"
```

预期末行含 `WUKONG100_PREFLIGHT=PASS`。脚本会验证三个 fixed SHA、项目内
regular-directory realpath、pinned Python/json5、官方 `build.sh`、单 build chain、
空间和内存。项目内 `_handoff/bin/python` 取代已丢失的 `/tmp/m04-bin/python`。
随后先跑受影响的精确 object/asset target，都通过后才启动单条官方 `images`
build。每次失败只封存第一 factual marker、exact command/rc/log SHA；不得从
default-all 噪音推导产品墙。

## 8. 首错快速校订索引

| 类别 | 可机械匹配的首错签名 | 快速校订（先做精确 target，再续同一 R45 `images`） | 权威证据 |
|---|---|---|---|
| OOM | kernel journal 含 `oom-kill:`，且 `/home/alexyang/autobuild_status.txt` 记录 `OOM detected (...)` | 不改源码、不清 `out/`；07-13 的 `-j2` 暖树增量成功、07-16 的 `-j30` 暖树续编也成功。新机 clean build 从 `-j2` 起，只有单 build chain、RAM/swap 门和 receipt 支持时才提高并发 | §1 的 status/build-log SHA；最终 `20260716T1701Z-bms-lts-fix-j30-resume/full.log`；`.../20260716T0840-r45-adapter-arm64-compile-pass/ROUND.md` |
| Python PATH | `/usr/bin/env: python: no such file or directory` | 使用 §6 固定的 prebuilt `PATH`/`PYTHONPATH`，先以 `python3 -c 'import json5'` 和原精确 target 复验；不得改源码或联网安装包 | `.../20260716T0657-r45-lts-compile-active/ROUND.md`；`.../20260716T1117-r45-full-gated-active/ROUND.md` |
| ACE webpack / ETS | `FileNotFoundError` 命中 `webpack/bin/webpack.js`；或 `Fatal error F0016: Can't find prefix for 'std/core'` | 先核验 §5 两个 pinned 文件 SHA；分别恢复完整官方 `app_internal.gni` 或 `ets2abc_config.gni`，不得复制 `node_modules`、只补两行或改用网络输入 | `.../20260715T1716-r9-terminal-ace-loader-webpack/ROUND.md`；`.../20260715T1726-r9-ace-rootcause-r10-launch/ROUND.md`；`.../20260715T1825-r11-terminal-ets-stdlib-prefix/ROUND.md`；`.../20260715T1859-r12-staged-preflight-integration/ROUND.md` |
| BMS validator | `installd_operator.cpp:3176:28: error: use of undeclared identifier 'IsValidBundleName'` | 保留 BMS 边界内唯一经审阅定义，重跑精确 `installd_operator.o`；目标 rc=0 后才续正式构建，不得误还原该有意 dirty 文件 | `.../20260716T0703-r45-bms-undeclared-validator/ROUND.md`；`.../20260716T0709-r45-bms-validator-fix-build-active/ROUND.md` |
| ccache auto-regeneration 漂移 | `args.gn` 只有 `ohos_build_enable_ccache = true`，但 target toolchain 的 CXX command 直接调用 `clang++`；post-GN direct Ninja 又先出现 `[0/1] Regenerating ninja files` | 根因是 `--ccache` 的布尔参数不等于生成图已绑定 wrapper，且 direct Ninja 可自动重生图；根治为显式 `cc_wrapper="/usr/bin/ccache"`、固定完整 `USE_CCACHE`/`CCACHE_*`/`PATH`/`PYTHONPATH`/`LIBRARY_PATH` 生命周期环境，并在 GN 后、五 target 后、正式全编译前各执行一次 args + target/clang_x64 toolchain graph gate | 固定入口 `build/build_wukong100_full.sh` SHA256 `3bcfe46308d1cb2317cb8f66300c50dd49eab140043a308a551866db60f5525c`；`/tmp/m04-r45-js-assets-post-gn.log`；`.../20260716T1117-r45-full-gated-active/ROUND.md` |
| bare/default-all Ninja | 命令是 `ninja -C out/wukong100` 且没有显式 `images`；首错落入 §5 的 optional-only 清单 | 该结果不能升级为产品墙；停止扩大 `if(false)` 裁剪，改走 §6 官方入口或显式 `images -w dupbuild=warn`，只接受其首个 factual marker | §4 临时日志 SHA 账本；`.../20260716T1117-r45-full-gated-active/ROUND.md` |

上表中 `...` 的共同绝对前缀为
`/opt/21.Game/02.unity.cardwords/adapter/research/atoms/L03/A15/evidence/M04/`。
任何签名未精确命中时都不得套用历史修复；先封存当次 exact command、rc、首个
`FAILED:` 和 log SHA，再新增事实项。

ccache 的三道 graph gate 只证明编译命令图绑定了 `/usr/bin/ccache`；在正式 wrapper
运行产生可核验的 `ccache -s` 前后计数前，cache hit、命中率和加速幅度均为
**Not-Proven**。
