# adapter/ — 完整技术栈的源码级 vendor 快照（独立本地仓库，零共享代码）

2026-07-09 从 `/opt/10.Project/16-WestLake/16.12-HanBing/adapter` 完整 vendor 进来，目标是让
"整个 Unity 运行不依赖当前 adapter 目录以外的内容"。

**这个目录本身是一个独立的本地 git 仓库**（`git init` 于此，首个 commit `ffa3899`），
和源仓库 `/opt/10.Project` **没有 git 关联**（不是 clone/fork，是一次性 vendor +
独立重新起的历史）。目的：`/opt/10.Project/16-WestLake/16.12-HanBing/adapter`
是一份长期有其它并发 job（如仍在活跑的 565933fa）在改动的共享 working tree，
在这里独立建仓之后，本项目（`/opt/21.Game/02.unity.cardwords`）范围内的后续所有
构建/实验/改动都应该只对这个本地仓库操作，**不应再读写共享树**——唯一允许的例外
是"引入某个尚未 vendor 进来的历史版本"这类一次性只读拉取（例如下面 cut9 的引入），
拉一次之后就要留在本地，不要每次实验都重新去共享树读。构建脚本里的 `ADAPTER_ROOT`
默认值已核查并修正为自动指向脚本自身所在位置（`build/config.sh` 本来就对，
`build/inner/compile_fresh_jars_manifested.sh` 之前硬编码指回共享树，已修正）。

## 版本锚定

- `framework/window/jni/oh_window_manager_client.cpp` 锚定在源仓库 git commit
  `7d962e5`（"snapshot: preserve cut8 self-drawing RSSurfaceNode XCOM lever"）——
  这是在 5eab 设备上实测确认能消除 Mali GPU 崩溃（`0x10000000f`，`libGLES_mali`
  指针截断）的版本，即路线3对齐路线2团结引擎"自绘子 RSSurfaceNode +
  SetHardwareEnabled(true, XCOM)"机制的那一版。
- **未采纳但已本地留存**：源仓库在 cut8 之上还有更晚的 commit `9640799`（"cut9
  XCOM geometry attempts — FAIL, evidence"），按其自己记录在 5bb5b 上仍然失败，
  与当前一个约 266ms 静默进程死亡（已坐实为真 SIGSEGV，见 memory
  `route3-rssurface-stack-confirmed`）的悬案有关，5eab 上从未测试过。已作为
  `framework/window/jni/oh_window_manager_client.cut9-untested-on-5eab.cpp`
  单独留存在本仓库（不参与构建，仅供实验/参考），避免以后还要回共享树去读。
- 其余文件按源仓库当天的活体 working tree 原样拷贝。

## 排除项（及理由）

- **`out/`**（源仓库中 2.1GB，git 已忽略）——编译产物，可从源码重新生成，非代码。
- **`oh-build-2204.tar.gz`**（397MB）——鸿蒙构建工具链 docker 镜像包，属于"鸿蒙"
  本身而非 adapter 代码。
- **`local_oh_headers`**——一个指向 `16.13-Yue/local-arm64-build/.../local_oh_headers`
  的软链接，链接目标是真实的 OpenHarmony 头文件树；已删除该软链接。
- **`ohos_patches/` 下 18 个带 `Copyright (c) 20xx Huawei Device Co., Ltd.` 版权头
  的 `.cpp`/`.h`/`.c`/sepolicy 文件**（如 `bundle_data_mgr.cpp`、`mission.cpp`、
  `installd_operator.cpp`、`appspawn.h`、`file_contexts` 等）——这些是被 patch 的
  OpenHarmony **系统服务源码全量副本**（编译进 OS 本身，不是 adapter 的产物），
  按"不包括鸿蒙/安卓源代码"的要求已删除。`ohos_patches/` 里剩下的 `.patch` diff
  文件（adapter 自己的改动记录）和无版权头的 adapter 原创文件予以保留。
- **`framework/appspawn-x/test/out/`、`framework/inet-shim/out/`、
  `ohos_patches/build/`**——嵌套的 git-ignored 构建产物目录。
- **`CLAUDE.md` / `doc/CLAUDE.md`**——git-ignored 且内容已过期（描述的是
  DAYU200/rk3568 32位 + Windows本机 + ECS云构建的旧工作流，与当前
  5eab/5bb5b arm64 + Mac本机 + OrbStack本机构建的现状不符），移除避免误导。

## 保留但值得注意的一类文件

- **`framework/android-runtime/` 下 24 个带 AOSP（"The Android Open Source
  Project"）版权头、文件名多带 `_aosp` 后缀的文件**（如
  `android_database_SQLiteConnection.cpp`、`CursorWindow.cpp`、
  `android_util_AssetManager_aosp.cpp` 等）——这些**保留**，因为它们会被直接
  编译进 adapter 自己的产物 `liboh_android_runtime.so`，是"让未修改 Android
  APK 在 OH 上跑起来"这件事的核心交付物本身，不是被引用的外部平台源码。删掉会
  直接挖空核心功能，与"不依赖 adapter 目录以外内容"的目标矛盾。用户已确认此
  处理方式。
- **`aosp_patches/libs/hwui/` 下 3 个文件**（`hwui_register_stubs.cpp`、
  `hwui_oh_abi_patch.cpp`、`renderthread/ReliableSurface.cpp`）——检查确认均为
  adapter 原创重写（`ReliableSurface.cpp` 文件头明确注明"Adapter stub version"，
  不是 AOSP 源码的拷贝），无版权头，保留。
- **`_routeb_dev_bak/`、`_routeb_bak_20260628/`**——adapter 自己构建产物的历史
  备份（`.devbak` 后缀的 `.jar`/`.so`），非 OS 平台源码，保留。

## 范围

未包含项目层面的一次性个人 CLAUDE.md 元文档、构建产物缓存、以及任何完整的
HarmonyOS/AOSP 平台源码。其余——adapter 自己的框架代码、AOSP/OH 补丁（.patch
diff）、构建脚本、部署脚本、设计文档——按用户要求全量收录。

## 2026-07-09 追加：绝对路径审查 + 独立编译验证

审查范围：`build.sh` → `build/config.sh` → `build/inner/compile_oh_adapter_bridge.sh`
（编译 `liboh_adapter_bridge.so` 的实际脚本）及其依赖的其它 `build/inner/*.sh`、
`framework/jni/BUILD.gn`、`build/apply_ohos_patches.sh`、`build/restore_after_sync.sh`。
`build/_deprecated/`、`deploy/*.sh`、`config/*.json`（设备侧运行时路径）、GZ05/ECS
远程编译脚本（`build/run_gz05_container_build.sh`、`build/start_container_build_on_gz05.sh`、
`build/pull_ecs_artifacts.sh` —— 与本项目"本机 OrbStack 构建"路线无关的历史/替代
工作流入口）不在本轮改动范围内。

**改的**（全部把默认值从硬编码指向某台机器/某个人主目录，改成 `${VAR:-$HOME/...}`
或脚本自身位置自推导，语义不变、仍可用同名环境变量覆盖）：
- `build/inner/discover_skia_rtti_syms.sh`、`check_skia_rtti_coverage.sh`、
  `compile_appspawnx.sh`、`compile_apk_installer.sh`、`compile_oh_android_runtime.sh`、
  `cross_compile_arm32.sh`、`cross_compile_minikin_stack.sh`、`compile_libhwui.sh`、
  `compile_oh_adapter_bridge.sh`——`OH_ROOT`/`AOSP_ROOT`/`ADAPTER_ROOT` 默认值原先写死
  `/home/HanBingChen/{oh,aosp,adapter}`（GZ05 上某具体账号的主目录，本机根本不存在），
  部分（`discover_skia_rtti_syms.sh`）甚至完全没有 env 覆盖入口。
- `appspawn/apply_appspawnx_routing.py`、`apply_appspawnx_sepolicy_and_namespace.py`——
  `--oh-root` 默认值同样硬编码 `/home/HanBingChen/oh`，改成
  `os.environ.get("OH_ROOT", os.path.expanduser("~/oh"))`。
- `framework/hwui-shim/skia_compat_headers/nativehelper/JNIPlatformHelp.h`——原来是
  `#include "/home/HanBingChen/aosp/libnativehelper/include_platform/nativehelper/JNIPlatformHelp.h"`
  的绝对路径字面量 `#include`，任何其他机器上编译必炸。改成 `#include_next
  <nativehelper/JNIPlatformHelp.h>`（GCC/Clang 委托语义：跳过当前文件所在目录继续
  往后搜索 `-I` 列表），配套在 `compile_libhwui.sh` 里把
  `-I$AOSP_ROOT/libnativehelper/include_platform` 加到 `-I$SKIA_COMPAT` **之后**。
  已用最小复现单独验证 `#include_next` 确实穿透到了真实 AOSP 头（而非递归指回
  shim 自己），完整 flag 集下 `android/log.h` 由已有的
  `-I$AOSP_ROOT/system/logging/liblog/include` 提供，链路完整。
- `build/inner/compile_oh_adapter_bridge.sh` 的 `window/` 源文件收集顺带修了一个
  真 bug：`*.cpp` glob 会把本仓库特有的、按本文件"版本锚定"一节明确"不参与构建"
  的 `oh_window_manager_client.cut9-untested-on-5eab.cpp` 也扫进编译（BR-1 警示的
  glob drift 打在了自己身上——共享树里没这个文件所以没暴露）。加了
  `*-untested-on-*.cpp` 排除。
- **未改**（`OH_ROOT`/`AOSP_ROOT` 默认值本来就是 `$HOME/oh`、`$HOME/aosp`，符合
  用户既定的"外部 SDK 依赖，不强求消除"标准）：`build/config.sh`、
  `build/restore_after_sync.sh`、`build/apply_ohos_patches.sh`。GZ05/ECS
  远程编译脚本、`_deprecated/`、`config/*.json`（设备侧 `/system/...` 路径，语义
  不同，不是构建期硬编码）按范围声明不改。

**独立编译验证**（OrbStack VM `westlake-build`，本 Mac 通过 `/mnt/mac` 挂载对本目录
可读写，对共享树只读）：`bash build/inner/compile_oh_adapter_bridge.sh` 单独调用
（`BUILD_INNER_INVOKED=1 OH_ROOT=... AOSP_ROOT=... ADAPTER_ROOT=` 三个环境变量，
`ADAPTER_ROOT` 自推导），`OH_ROOT` 只读指向共享树 `16.12-HanBing/oh`（本机唯一一份
带完整 `prebuilts/clang/ohos` + 已 build 好的 `out/rk3568` 的 OH 源码树，"api24"
代次），`AOSP_ROOT` 指向 OrbStack VM 本地已有的 `~/aosp-local`（与共享树无关，
本地已有的完整 AOSP checkout），`$ADAPTER_ROOT/out/aosp_lib` 的预编译 AOSP native
库（`libnativehelper.so` 等）从共享树同名目录只读复制到本地 `out/`（`out/` 本就
被本文件排除在 vendor 范围外、gitignore、可从源重新生成，复制不算写共享树，且
compile_oh_adapter_bridge.sh 的设计本来就假定 OH/AOSP 侧都是"已构建好的输入"，
不在这一个目标脚本里重新编译）。

结果：路径解析层面**零失败**——230 条从 OH ninja 计划里 harvest 出来的 `-I`、
本地 `INCS_LOCAL/INCS_OH/INCS_AOSP` 全部命中，39 个源文件里 31 个（79%）完整编译
通过，0 个"文件找不到"类错误。剩余 8 个失败**全部**是同一对根因、且**不是路径
问题**：`framework/activity/jni/app_scheduler_adapter.h`、
`framework/window/jni/session_stage_adapter.h` 里的
`ScheduleMemoryLevel`/`NotifyAppForceLandscapeConfigEnableUpdated` override
签名，本仓库源码自带的注释（`[S24 cut9 2026-07-09]`）写明是**今天**为对齐"真机
6.1.0.31"故意改的参数个数，与本机唯一可用的 OH 源码树（api24 代次，接口仍是老
参数个数）**代次不匹配**——即当前 vendor 进来的这份 adapter 源码，其最新改动
本来就不是针对 api24 写的，本机没有 6.1.0.31 代次的完整可编译 OH SDK/源码树
可用于验证到 link 这一步（搜过 `/opt/1Z.Tools`、`/opt/17-TestLab` 下两份
`19.1F.HarmonyOS-v6.1.0.31`，都只是 repo 部分同步/固件包，没有 `foundation/` 也
没有已 build 的 `out/`）。这是**代次缺口**，不是本轮要修的"硬编码路径"问题；
留给下一个碰 S24/cut9 的 agent。

结论：单目录路径自包含性——**验证通过**（zero 路径类编译错误）。单目录完整编译
到 link 出 `.so`——**当前环境下不可达**，卡在上述代次缺口，与本轮路径修复无关。
用户提供的参照产物 `out/arm64-unity/liboh_adapter_bridge.so`（md5 `aa204660`）另有
隐情：它不是本仓库 vendor 进来的 `build/inner/compile_oh_adapter_bridge.sh`
（armv7/rk3568 目标）编出来的，产出它的脚本是 `out/arm64-unity/compile_bridge_local.sh`
——一份活在共享树 `out/` 目录下（按本文件"排除项"一节的规则从未 vendor 进本仓库）、
面向 aarch64/wukong100 的手改副本，且它自己就还有更多硬编码绝对路径（`OUT=`、
`CXX=`、`BUILTINS=` 直接写死指向共享树，`AOSPLIB=` 写死指向另一个不相关项目
`/opt/17-TestLab/17.07-Build/noice-oh61-fromscratch/...`）——也就是说这份参照产物
本身就不是从"单一自包含目录"编出来的，无法作为本轮"独立编译能力"的直接对照，
只能作为"这条构建链路本身能出 .so"的间接佐证（用户原话）。

## 2026-07-09 二次追加：上一节"代次缺口"已解决，39/39 编译到 link 通过

上一节结论"单目录完整编译到 link 出 `.so`——当前环境下不可达"**已被推翻**——不是
靠拿到一整棵 6.1.0.31 源码树，而是定位到真正需要的东西比想象中小得多。以下是
完整过程，供复核。

**①精确定位缺什么**：失败的只有 2 个方法的纯虚函数签名（`app_scheduler_adapter.h`
的 `ScheduleMemoryLevel`、`session_stage_adapter.h` 的
`NotifyAppForceLandscapeConfigEnableUpdated`），报错信息本身就精确到"参数个数
2 vs 1"/"1 vs 0"，且报错指向的正是 api24 树里对应两个基类接口头文件
（`app_scheduler_interface.h` 第 85 行、`session_stage_interface.h` 第 306 行）。

**②签名来源找到了，在本机、非共享树**：`/opt/1F.Application/02.Noice/adapter/
local_oh_headers/oh_mirror/`——另一个不相关项目（Noice）的、面向真机
6.1.0.31/wukong100 世代的**只读头文件镜像**（`foundation/...` 目录结构，无
`out/`、无完整编译工具链，纯粹是接口签名的"快照"）。同一份镜像在
`/opt/10.Project/16-WestLake/16.13-Yue/local-arm64-build{,-YUE}/oh61-wukong100/
adapter/local_oh_headers/oh_mirror` 和 `_cleanlibart_pathfind/adapter-cleanlibart/
local_oh_headers/oh_mirror` 下还有另外 3 份拷贝，互相印证不是孤证。core/window
两个 adapter 头文件里"[S24 cut9 2026-07-09]"注释写的"confirmed against
local_oh_headers/oh_mirror"就是指这份东西——即当天写这两处签名改动的人已经用
它核对过，只是没有把它接进本仓库的编译脚本。

**核对结果**（`/usr/bin/diff -u`，用 `/usr/bin/diff` 不是 PATH 里 DevEco 的
`diff`，后者选项不兼容）：
- `app_scheduler_interface.h`：api24 与 oh_mirror 之间**只有一行不同**——
  `ScheduleMemoryLevel(int32_t level, bool isShellCall = false)` →
  `ScheduleMemoryLevel(int32_t level)`。逐字符匹配本仓库当前代码已经改成的样子。
- `session_stage_interface.h`：diff 显示 api24 比 oh_mirror(6.1.0.31) 多出几个
  V7 新增的纯虚函数（`NotifySubWindowAfterParentWindowSizeChange`、
  `GetSceneNodeCount`、`UpdateAppHookWindowInfo`、`SetUIExtensionTransparent`
  等——即代码注释里说的"V7-only newly added pure virtuals"那一批，全部对得上），
  加上目标行 `NotifyAppForceLandscapeConfigEnableUpdated(bool needUpdateViewport
  = false)` → `NotifyAppForceLandscapeConfigEnableUpdated()`。没有其它出入。
- 用 `app_scheduler_host.h`（identical，两代字节相同）+
  `session_stage_stub.h`（只是同步删掉了 V7-only 那批方法对应的
  `HandleXxx` 私有声明，不影响这两个目标方法）配套佐证：generational skew
  确实**只集中在这两行**，不是大范围漂移。

**③只 vendor 这 4 个头文件进本仓库**（不是整棵 SDK，不读写共享树——
`oh_mirror` 来源不是本 PROVENANCE 之前定义的"共享树" `/opt/10.Project/16-
WestLake/16.12-HanBing`，是另一个项目目录，全程只读）：
- `build/oh_headers_631_overlay/foundation/ability/ability_runtime/
  interfaces/inner_api/app_manager/include/appmgr/{app_scheduler_host.h,
  app_scheduler_interface.h}`
- `build/oh_headers_631_overlay/foundation/window/window_manager/
  window_scene/session/container/include/zidl/{session_stage_stub.h,
  session_stage_interface.h}`

`build/inner/compile_oh_adapter_bridge.sh` 新增 `INCS_OVERLAY_631`，
`-I` 指向这两个 overlay 叶子目录（**踩过一次坑**：第一次把 `-I` 指到 overlay
树的根目录，参照本仓库源码里"完整相对路径"摆放，结果编译**仍然**解析到 api24
版本——原因是 `INCS_OH`/harvest 出的 ninja `-I` 本来就是**直接指到叶子目录**
如 `.../appmgr`、`.../window_scene`，配合 adapter 自己 `#include
"app_scheduler_host.h"`（裸文件名）/ `#include "session/container/include/
zidl/session_stage_stub.h"`（相对叶子目录的相对路径）这两种写法，`-I` 必须精确
落在同样的叶子层级，指到 overlay 树根不生效；修正后才真正生效，用 `clang++ -H`
逐层跟踪头文件解析路径确认），并放在 `INCS_LOCAL` 之后、`INCS_OH`/harvested
ninja 列表之前，保证被优先命中。

**④OrbStack VM `westlake-build` 独立编译验证**（`OH_ROOT` 仍是共享树只读，
`AOSP_ROOT=~/aosp-local`，与上一节相同环境，完全复现后清 `/tmp/bridge_build`
+ `--clean` 重跑两次确认非缓存假象）：

```
sources: 39 .cpp files
Compiled: 39/39 (fails: 0)
Linking .../liboh_adapter_bridge.so ...
  linked: 1.6M [strict]
```

`[strict]` = `-Wl,--no-undefined` 严格链接一次通过，没有走 BR-2 警示的
"relaxed 兜底"（那条路径会把未解析符号推迟到运行时才炸，本轮没有触发）。
`nm -C` 抽查确认编译产物里的符号确实是修复后的形状：

```
oh_adapter::AppSchedulerAdapter::ScheduleMemoryLevel(int)
oh_adapter::SessionStageAdapter::NotifyAppForceLandscapeConfigEnableUpdated()
```

（而不是残留的 2-参数/1-参数旧形状），证明不是"凑巧编过"而是真的按 6.1.0.31
接口形状 override 成功、参与了正确的 vtable 槽位。

**结论**：39/39（100%）源文件编译通过，**完整 link 出 `.so`**，本仓库路径
自包含 + 单目录独立编译目标**双双达成**。之前"代次缺口，留给下一个 agent"的
结论撤回：真正卡住的从来不是"需要一整棵 6.1.0.31 源码树"，而是"需要知道 2 个
方法的正确签名"，而这个签名早就以只读头文件镜像的形式存在于本机（虽然不在
`16.12-HanBing` 那棵共享树里），只是没人把它接进编译脚本。

**没有做、也不在本轮范围内的事**（如实记录，避免过度宣称）：
- 未做真机 6.1.0.31 部署验证——用户明确要求本轮"不碰任何真机设备"。上面④的
  `nm -C` 符号核对是静态证据，不是运行时证据；真正的 ABI/vtable-slot 正确性
  最终要靠 truly-cold 真机验证（`_deep_debug_westlake` 纪律）。不过这一层
  正确性和"能不能编译到 link"是两个独立问题——本轮解决的是后者。
- **已知残留风险，未处理，供后续 agent 参考**：目录级 diff（`/usr/bin/diff -r
  -q`）发现 `appmgr/` 目录下还有其它文件在 api24 与 6.1.0.31 之间也不同
  （`ams_mgr_interface.h`、`ams_mgr_proxy.h`、`ams_mgr_stub.h`、
  `app_jsheap_mem_info.h`、`app_mem_info.h`、`app_mgr_client.h`、
  `app_mgr_interface.h`、`fault_data.h`、`ierror_observer.h`、
  `running_process_info.h`），`zidl/` 目录下 `session_stage_proxy.h`、
  `session_stage_ipc_interface_code.h` 也不同。这些**没有**被本轮 vendor
  进 overlay（刻意保持从 api24 解析，避免引入未审计过的新漂移），因为
  adapter 代码里没有任何地方对它们做 `override` 声明去触发编译期检查——
  但这也意味着如果 adapter 未来某处以 api24 形状使用了这些类型
  （比如 `ScheduleJsHeapMemory(JsHeapDumpInfo&)` 用到的 `app_jsheap_mem_info.h`），
  编译不会报错，但运行时结构体布局可能与真机 6.1.0.31 不一致——这类"没有
  `override` 关键字保护、编译期发现不了"的静默 ABI 偏差，本轮**没有**逐个排查，
  仅确认了本轮真正触发编译错误的那 2 处。

## 2026-07-09 三次追加：扩大验证覆盖面——apk_installer / appspawn-x / liboh_android_runtime.so 三个 native 目标 + oh-adapter-framework.jar（Java）范围内首次尝试

`liboh_adapter_bridge.so` 只是 adapter 众多构建目标之一。本轮扩大"单目录可编译"
验证覆盖面到 CLAUDE.md「OH Build (BUILD.gn)」一节列出的其它目标，并对"哪些目标
属于本仓库范围"重新做了一次显式判断。

### 范围边界判断（哪些算 adapter 自己的交付物，哪些不算）

沿用第一轮已确立的判据：**会被编译进 adapter 自己产物的东西 = 保留/验证；
被 patch 的 OS/AOSP 平台源码本身（要 vendor 一整棵外部源码树才能编）= 排除**。
本轮把这条判据应用到 CLAUDE.md 列出的剩余目标：

**判为「属于本仓库范围」（adapter 自己的交付物，本轮逐个验证编译）**：
- `libapk_installer.so`（`framework/package-manager/`，脚本
  `build/inner/compile_apk_installer.sh`）
- `appspawn-x`（`framework/appspawn-x/`，脚本 `build/inner/compile_appspawnx.sh`）
- `liboh_android_runtime.so`（`framework/android-runtime/`，脚本
  `build/inner/compile_oh_android_runtime.sh`）——AOSP 原版 `libandroid_runtime.so`
  的**精简重实现**（2.28MB → ≈370KB 实测），源码就是第一轮"保留但值得注意"里
  那 24 个 vendor 进本仓库的 `_aosp` 后缀文件，是 adapter 自己的产物，不是被
  引用的外部平台库本身。
- `oh-adapter-framework.jar`（BCP Java library，脚本
  `build/inner/compile_oh_adapter_framework.sh`）——只含 `adapter.*` 包，
  adapter 自己的 Java 源码。
- `oh-adapter-runtime.jar`（非 BCP Java library，脚本
  `build/inner/compile_oh_adapter_runtime.sh`）——同上，adapter 自己的 Java 源码，
  与 `oh-adapter-framework.jar` 拆分自同一份工程（频繁改动的类挪到这边避免
  boot image 重烤）。本轮因其前置产物（BCP `CLASS_DIR`）未就绪，未实际验证，
  留给下一个 agent（见下）。

**判为「不属于本仓库范围」（OS/AOSP 平台自身构建，不处理，只记录理由）**：
- **OH 系统服务 patches**（`abilityms`、`libappms`、`scene_session_manager`、
  `scene_session`、`libbms`）——第一轮 vendor 时已经把 `ohos_patches/` 下 18 个
  带 Huawei 版权头的系统服务源码全量副本删掉了，本轮核实 `ohos_patches/` 现状
  （`find ... -type f`）：剩下 44 个 `.patch` diff 文件 + 少量 `.txt`/`.html`
  说明文档 + 2 个无版权头的 adapter 原创文件，**没有任何一个 `.cpp`/`.h` 全量
  服务源码残留**。决定性证据：`build/inner/` 目录下**没有任何一个脚本**以
  `abilityms`/`libappms`/`scene_session_manager`/`scene_session`/`libbms` 为编译
  目标——这些 patch 是要打进完整 OH 系统源码树、再用 OH 自己的
  `cd ~/oh && ./build.sh --product-name rk3568 ... --build-target <target>`
  （CLAUDE.md 原文命令）编出整个 OS 产品镜像的一部分，根本不是"某个脚本单独在
  这个仓库里就能调用"的东西。要让这类目标可编译，前提是把**整棵 OpenHarmony
  操作系统源码树**（`foundation/`、`base/` 等，数十 GB）vendor 进本仓库，直接
  违反第一轮已确立的"不包括鸿蒙/安卓源代码"原则。判定：不在范围内，不处理。
- **AOSP native 交叉编译产物本身**（`libart.so`、真正的 AOSP 原版
  `libandroid_runtime.so`、dex2oat 等，`out/aosp_lib/` 下这一类 ~22 个 `.so`，
  由 `cross_compile_arm32.sh`/`compile_libhwui.sh`/`compile_dex2oat_host.sh`/
  `cross_compile_minikin_stack.sh` 产出）——这些脚本编的是**未经 adapter 修改
  的 AOSP 平台自身源码**（`art/`、`system/core/`、`external/icu` 等，读自外部
  `$AOSP_ROOT`），不是 adapter 自己写的代码；它们和 `liboh_adapter_bridge.so`
  编译时依赖的 `$OH_ROOT/out/rk3568`（OH 平台自己已构建好的产物，第一轮就已
  确立"外部 SDK 依赖，只读使用，不强求 vendor 消除"）是**同一性质**——只是
  OH 侧那份别人已经预构建好摆在共享树里，AOSP 平台侧这份是本项目自己用专门的
  交叉编译工具链（OH clang + musl sysroot + bionic_compat 翻译层）现造的，但
  造出来之后的角色一样：都是 adapter 自己产物的**已构建好的外部输入**，不是
  adapter 自己的交付物。判定：这 4 个脚本本身仍是本仓库文件（第一轮硬编码路径
  清理已经覆盖过，见上文"改的"清单），但重新从头跑一遍交叉编译（拉起 ICU /
  HarfBuzz / libart 等 ~22 个库的完整构建）不在本轮验证范围——它们的产物
  `out/aosp_lib/*.so` 本轮开始前就已经存在（第一轮从共享树只读复制来的），
  本轮 appspawn-x 和 liboh_android_runtime.so 的链接都直接消费了这些**已构建
  好的输入**，与消费 `$OH_ROOT/out/rk3568` 是同一模式，不需要重新验证"从裸
  AOSP 源码能不能编出这些库"这件事本身。

### 逐目标编译结果

**`libapk_installer.so`**（`build/inner/compile_apk_installer.sh`）：
- 未发现残留硬编码路径问题（第一轮已清理，本轮实测确认）。
- OrbStack VM `westlake-build` 独立编译（`OH_ROOT` 只读指向共享树、
  `AOSP_ROOT=~/aosp-local`，与前两节相同环境），干净重跑两次确认非缓存假象：
  `Compiled: 10/10`（7 个 adapter 自己的 `.cpp` + minizip 的
  `unzip.c`/`zip.c`/`ioapi.c` 3 个 `.c`），链接出 `libapk_installer.so`（374K）。
- 脚本原有链接用的是宽松 `-Wl,--unresolved-symbols=ignore-all`（非严格）；本轮
  额外用同一批 `.o` 手工重新链接一遍、加 `-Wl,--no-undefined`，**同样一次通过**
  ——证明这条宽松兜底目前不是必需的，10 个源文件的符号引用全部在链接期就能
  完整解析，不是"编译能过、链接期偷偷放水"的假成功。
- `llvm-readelf -h/-d` + `llvm-nm -D` 核对：ELF32 ARM `DYN`（共享库）、
  NEEDED 全是合理的 OH 系统库（`libc.so`/`libhilog.so`/`libcrypto_openssl.z.so`
  等），导出符号 `oh_adapter_install_apk`/`oh_adapter_install_apk_with_manifest`
  存在。

**`appspawn-x`**（`build/inner/compile_appspawnx.sh`）：
- 未发现残留硬编码路径问题（第一轮已清理，本轮实测确认）。
- 同一 VM 环境独立编译，干净重跑两次确认非缓存假象：`Compiled: 4/4`
  （`main.cpp`/`appspawnx_runtime.cpp`/`spawn_server.cpp`/`child_main.cpp`），
  链接出 `appspawn-x`（109K，`ELF32 ARM DYN`——虽是可执行目标但生成的是位置
  无关的 DYN 类型 ELF，OH 平台正常形态）。
- 脚本原有链接用 `-Wl,--allow-shlib-undefined`（宽松）；同 apk_installer 一样
  手工验证：同一批 `.o` 加 `-Wl,--no-undefined` 重新链接**同样一次通过**——
  这条宽松兜底当前也不是必需的。
- NEEDED 核对：`libart.so`/`libnativehelper.so`/`libbionic_compat.so`（均来自
  `out/aosp_lib/`，第一轮从共享树只读复制来的已构建输入）+
  `libipc_core.z.so`/`libsamgr_proxy.z.so`/`libselinux.z.so` 等 OH 系统库，
  形状与脚本注释里 2026-04-11 记录的"链真 `libart.so`（非 stub）"设计一致。

**`liboh_android_runtime.so`**（`build/inner/compile_oh_android_runtime.sh`）——
**发现并修复了一个真实的路径/include 缺口**（不是硬编码绝对路径，是缺一条
`-I`）：
- 首次跑：编到第 10 个源文件 `android_graphics_compat_shim.cpp` 报错
  `fatal error: 'pixel_format_mapper.h' file not found`。定位：该头文件物理
  位于 `framework/surface/jni/pixel_format_mapper.h`，但脚本里"adapter 自己
  源码"这条编译规则（变量名 `COMMON`/`INC`，对应 `SRCS` 数组，第 179 行起）
  的 `INC` 变量只包含 `framework/android-runtime/{include,src}` 等目录，没有
  `framework/surface/jni`。**注意**：脚本里还有一套并行的 `COMMON_AOSP`/
  `INC_AOSP`（对应 `SRCS_AOSP` 数组的"AOSP 移植源码"编译规则）——第一次
  尝试误把 `-I` 加到了 `INC_AOSP`（两套变量容易混淆），交叉验证时用
  `bash -x` 打印实际编译命令行才发现该文件走的是 `COMMON`/`INC` 那条规则，
  改错了地方，随后订正。
- 修复：`build/inner/compile_oh_android_runtime.sh` 的 `INC` 变量新增
  `-I$ADAPTER_ROOT/framework/surface/jni`，并加注释说明原因（含日期 + 判断
  依据），避免以后又被当成"硬编码路径"来找错方向。
- 修复后干净重跑（`rm -rf out/android-runtime-build` 后重来一次）：
  `Compiled: 36/36`（24 个"adapter 自己"源码，C++17 + `-fno-rtti` + 强制
  include `libcxx_compat.h`；12 个"AOSP 移植"源码，C++20 + `-fno-exceptions`，
  含 `AndroidRuntime.cpp`/`android_util_AssetManager_aosp.cpp`/
  `android_view_MotionEvent_aosp.cpp` 等），链接出 `liboh_android_runtime.so`
  （378372 字节 ≈ 370KB，与脚本文档注释里"2.28MB → ≈170KB"的量级预期一致，
  实测比预期略大但同量级，未深究差异原因，不影响"能否编译到 link"这个判定）。
- `llvm-nm -D` 抽查确认导出 `android::AndroidRuntime::startReg(_JNIEnv*)`、
  `android::register_android_util_Log(_JNIEnv*)`、
  `android::register_android_content_AssetManager(_JNIEnv*)` 等真实符号。
- **严格链接测试的结果与前两个目标不同、如实记录**：用同一批 `.o` 加
  `-Wl,--no-undefined` 手工重新链接，**这次失败**——6 个符号未解析：
  `register_android_os_Debug`、`register_android_hardware_SensorManager`、
  `register_android_opengl_jni_EGL14`、`register_android_opengl_jni_GLES20`、
  `register_android_opengl_jni_GLES31`、`register_android_opengl_jni_GLES30`
  （均被 `AndroidRuntime.cpp` 的 `kRegJNI`/`kRegJNI_GL` 注册表引用，但对应的
  `register_*` 实现源码本仓库里目前没有）。也就是说，脚本原有的
  `-Wl,--allow-shlib-undefined`（宽松链接）在这个目标上**是真正必需的**、
  不是历史遗留的多余保险——这与本仓库文件头部注释里反复强调的"渐进式 JNI
  注册"（`[UNITY-SVC-STUB]`/`[G2.1x]` 系列日期化注释，逐个 native 方法按需
  补齐、明确记录哪些还未接）设计意图一致，是当前项目状态的真实反映，不是
  bug，本轮未改动、未强行补全这 6 个 `register_*` 函数。

**`oh-adapter-framework.jar`**（BCP Java library，
`build/inner/compile_oh_adapter_framework.sh`）：
- 前置产物缺口（不是本仓库脚本问题，是环境缺前置构建）：脚本需要
  `$AOSP_ROOT/out/soong/.intermediates/{frameworks/base/framework-minus-apex,
  libcore/core-oj,libcore/core-libart}/android_common/turbine-combined/*.jar`
  三个 turbine header jar + `$AOSP_ROOT/out/host/linux-x86/bin/d8`，这些都是
  AOSP Soong 完整构建的副产物。OrbStack VM `~/aosp-local`（本轮环境按用户要求
  与上一轮一致，只用这一份 AOSP checkout）里当时**都不存在**——`out/soong/`
  只有 setup 阶段的痕迹，从未真正跑过 `m` 编译任何目标。
- 解决过程：`~/aosp-local` 已有现成的自定义 lunch 组合
  `device/adapter/oh_adapter/{AndroidProducts.mk,oh_adapter.mk,BoardConfig.mk}`
  （product 名 `oh_adapter`），以及一份历史遗留的 `auto_build.sh`（路径已过期
  指向 `/root/aosp`，但其调用方式本身是有效参照）——其中记录了两个关键 env：
  `ALLOW_MISSING_DEPENDENCIES=true`、`BUILD_BROKEN_DISABLE_BAZEL=1`（后者是
  绕过一个环境相关的失败：`lunch`/`m` 触发的 mixed-build bazel cquery 因
  "Couldn't locate JDK to use for Bazel"而失败，是 VM 环境的 Bazel-JDK 发现
  问题，与 adapter 代码无关）。用这两个 env + `source build/envsetup.sh` +
  `lunch oh_adapter-userdebug` + `m framework-minus-apex core-oj core-libart
  d8 -j16`，在 `~/aosp-local`（`out/soong/build.ninja` 此前已有一份 1GB/725万行
  的现成 Soong 分析结果，省掉了最贵的 analysis 阶段，只需要跑 ninja 编译图）
  跑了约 20 分钟，`build completed successfully`，四个前置产物全部产出
  （`framework-minus-apex.jar` 29.5MB / `core-oj.jar` 3.4MB / `core-libart.jar`
  448KB / `d8` 2.7KB 可执行脚本）。**这一步编的是 AOSP 平台自身的 Java 库
  （`framework-minus-apex`/`core-oj`/`core-libart`），角色和 `out/aosp_lib/`
  里的 native `.so` 一样，都是 adapter 自己产物所需的"已构建好的外部输入"，
  本身不是 adapter 的交付物**——之所以这次要现场编，只是因为这个 VM 里之前
  没人替它预先构建好摆在那儿（不像 native 侧 `out/aosp_lib` 已经从共享树复制
  来了现成的），跑这一步是为了让"验证 adapter 自己的 `oh-adapter-framework.jar`
  能不能编"这件事具备可能性，不代表把"AOSP native 交叉编译"那类平台自身构建
  纳入了本轮范围（那类涉及 ~22 个库、体量大得多，且已有现成 `out/aosp_lib`
  可用，没有现场重编的必要，见上文范围判断）。
- 前置产物就绪后重跑 `compile_oh_adapter_framework.sh --clean`：pre-flight
  从 `framework/*/java` 同步 11 个变化文件到 `$AOSP_ROOT/device/adapter/
  oh_adapter_framework/java/`（跳过 112 个非 `adapter.*` 包、5 个按脚本自带
  规则搬到 runtime jar 的类），凑齐 32 个 `.java` 源码开始 `javac`，**编译到了
  真正的 javac 阶段**（证明前置产物路径/classpath 全部解析正确），但失败：

  ```
  adapter/core/OHServiceManager.java:168: error: package adapter.core.unitysvc
  does not exist
  ```

  精确定位：`OHServiceManager.java` 第 168/171/174/177/180 行引用
  `adapter.core.unitysvc.{PowerManagerStub,ThermalServiceStub,AudioServiceStub,
  VibratorManagerStub,ClipboardStub}` 共 5 个类，文件自带注释（第 159 行）写明
  这些是"auto-generated (adapter.core.unitysvc.*) subclass of the corresponding
  android AIDL .Stub"——即预期由某个代码生成步骤产出，但**这个包在本仓库、
  共享树 `16.12-HanBing/adapter`、以及本机全局搜索（`find /opt -path
  "*unitysvc*"`，含 `/opt/1F.Application`、`/opt/10.Project` 等已知有历史
  adapter 副本的位置）里都不存在**——不是漏 vendor（vendor 是从共享树逐字节
  复制来的，共享树自己也没有这个包），也没有任何生成脚本/AIDL 定义文件的踪迹；
  `build/build_aosp_fw.sh`、`build/build_adapter.sh`（两个会 dispatch 到
  `compile_oh_adapter_framework.sh` 的上层 wrapper）里也确认没有任何 unitysvc
  相关的代码生成步骤会在调用前先跑。**结论：这是 adapter 项目自身当前就存在
  的源码缺口（`[UNITY-SVC-STUB]` 标记显示是本 Unity 项目相关的未完工功能），
  不是本轮"硬编码路径"或"代次缺口"这两类问题，而是 5 个类的 Java 源码字面上
  还没有被写出来/生成出来过，在任何地方都找不到**。按用户"精确定位缺什么、
  不要一上来假设缺整棵 SDK"的要求已经做到位——缺的不是 SDK，是这 5 个具体
  类的源码本身，此事本轮不处理（编写全新的 AIDL Stub 子类实现属于功能开发，
  超出"验证既有构建目标能否编译"的范围，草率补一版可能引入未经设计审查的
  错误行为）。
- **结论**：`oh-adapter-framework.jar` 前置的 AOSP Soong 依赖缺口**已解决**
  （`~/aosp-local` 现在长期具备这四个 turbine jar + d8，后续 agent 不用重跑这
  ~20 分钟），构建流程本身路径无误、能推进到真正的 javac 编译，但受阻于上述
  真实源码缺口，**未能编出 `oh-adapter-framework.jar`**。

**`oh-adapter-runtime.jar`**（非 BCP Java library，
`build/inner/compile_oh_adapter_runtime.sh`）：**未实际验证**——该脚本需要
`$ADAPTER_ROOT/out/adapter/classes`（`compile_oh_adapter_framework.sh` 成功
产出的 BCP `.class` 中间目录）作为 `-classpath` 的一部分，由于上面
`oh-adapter-framework.jar` 卡在 `adapter.core.unitysvc` 缺口没能编完，这个
前置目录没有产出，本轮未运行 `compile_oh_adapter_runtime.sh`。留给下一个补上
`adapter.core.unitysvc` 缺口的 agent 顺带验证。

### 小结

| 目标 | 类型 | 范围判定 | 本轮结果 |
|---|---|---|---|
| `liboh_adapter_bridge.so` | native .so | adapter 自己产物 | 39/39 编译 + 严格链接通过（上一轮） |
| `libapk_installer.so` | native .so | adapter 自己产物 | 10/10 编译 + 严格链接通过（本轮） |
| `appspawn-x` | native ELF | adapter 自己产物 | 4/4 编译 + 严格链接通过（本轮） |
| `liboh_android_runtime.so` | native .so | adapter 自己产物 | 36/36 编译 + 链接通过（本轮，修了 1 处缺 `-I`；严格链接因 6 个故意未接的 `register_*` 而失败，符合已知设计） |
| `oh-adapter-framework.jar` | Java (BCP) | adapter 自己产物 | 前置 AOSP Soong 依赖缺口已解决；卡在真实源码缺口 `adapter.core.unitysvc`（5 类不存在于任何地方），未编出 jar |
| `oh-adapter-runtime.jar` | Java (非 BCP) | adapter 自己产物 | 未运行（前置产物未就绪） |
| OH 系统服务 patches（abilityms 等） | OS 内 patch | **不属于本仓库范围** | 未处理（需整棵 OH OS 源码树 + OH 自己的 product-image 构建，违反既定排除原则） |
| AOSP native 交叉编译（libart.so 等 ~22 个库本身） | 外部平台库 | **不属于本仓库范围** | 未处理（属于 adapter 产物的外部预构建输入，本轮消费的是已存在的 `out/aosp_lib`，未重新从源码验证） |

本轮改动的文件：`build/inner/compile_oh_android_runtime.sh`（新增 1 条
`-I$ADAPTER_ROOT/framework/surface/jni`，修复 `pixel_format_mapper.h` 找不到
的问题）。其余目标（`apk_installer`、`appspawn-x`）未发现需要改动的问题。

## 2026-07-10 追加：RenderThread 修复 rebuild 依赖的自包含性补全审计

**起因**：memory `route3-rssurface-stack-confirmed.md`（"RenderThread正交墙
修复已落地并生效"一节，2026-07-10）记录了一次绕过本仓库、直接在 GZ05
（`/data/adapter`）+ 额外从 `/data/aosp` 拉 3 个 raw AOSP 文件 + 从**另一个
不同的本地目录** `/opt/21.Game/21.Game/adapter/out/arm64-unity/` 拷贝
`egl_inc` 头文件目录完成的 rebuild。用户要求重新收紧"100%代码都在 adapter
目录下面"这条约束，逐项核实并补全。

### 审计结果

1. **门禁修复本身**（`framework/android-runtime/src/android_graphics_compat_shim.cpp`
   的 `OHUB_VARIANT` 枚举 + `OHUB_UNITY_LIBDIR` 双保险）——**已经在本仓库**，
   working tree 未提交改动，`md5 a7af9d7d593b0a22fee6f14893b42129`，与 memory
   记录的落地版本字节一致，未被后续任何 agent 覆盖或回退。
2. **5 个 adapter 自写文件**（`android_os_Debug.cpp` /
   `android_hardware_SensorManager.cpp` / `android_ndk_libandroid_shim.cpp` /
   `android_window_show_native.cpp` / `android_opengl_EGL14_adapter.cpp`）——
   **本来就都在** `framework/android-runtime/src/`，此前的 vendor 已经覆盖，
   不存在缺失。
3. **3 个 raw AOSP GLES 文件 + 1 个 raw AOSP asset_manager.cpp** —— **缺失**，
   已从本机 `/opt/1F.Application/02.Noice/aosp`（一个独立、已在 2026-07-09
   "39/39 编译" 那次审计里用作过 header 来源的本地 AOSP 镜像）复制补齐，
   `md5` 逐字节核对与 GZ05 `/data/aosp` 当天实际编译所用的版本**完全一致**
   （`android_opengl_GLES20.cpp`=`aeab0f3e...`、`GLES30.cpp`=`966fa3ad...`、
   `GLES31.cpp`=`76816b46...`、`asset_manager.cpp`=`ebef4b0b...`），不是"版本
   相近但可能有漂移"的旁证，是同一份字节。
4. **`egl_inc`（EGL/KHR Khronos 头文件，4 个文件，116KB）**—— **缺失**（此前
   只存在于 `/opt/21.Game/21.Game/adapter/out/arm64-unity/egl_inc`，一个跟本
   仓库毫无 git 关联的兄弟目录）。已复制并逐字节核对与 GZ05
   `/data/adapter/out/egl_inc`（当天实际编译使用的那份）**完全一致**
   （`egl.h`=`5428a669...`、`eglext.h`=`a79031e3...`、
   `eglplatform.h`=`ca01f4de...`、`khrplatform.h`=`fc46e6e5...`）。
5. **权威构建脚本 `compile_oh_android_runtime_arm64_stage2unity.sh`**——
   **本仓库此前完全没有**（`build/inner/` 下只有一个 armv7（32位）目标的
   `compile_oh_android_runtime.sh`，跟这次 rebuild 用的 aarch64（64位）
   脚本是两个不同架构、不同文件集合的脚本，不是同一份改小/改大的版本）。已
   直接从 GZ05（`/data/adapter/build/inner/compile_oh_android_runtime_arm64_stage2unity.sh`，
   当天实际产出部署产物 `md5 58d20467...` 的那份脚本本体，而非本 session 凭
   记忆重建）取回，核实其中硬编码外部路径后逐条修正（见下）。

### 新建的 vendor 目录：`third_party/aosp_raw/`

区别于 `aosp_patches/`（存的是"AOSP 原文件 + adapter 的 diff/patch"或
"adapter 原创重写但沿用 AOSP 目录结构"的文件），`third_party/aosp_raw/` 存的
是**零 diff、逐字节原样编译进 `liboh_android_runtime.so` 的未修改 AOSP/Khronos
源码**——套用本文件"保留但值得注意的一类文件"一节已经确立的原则（"会被直接
编译进 adapter 自己的产物…不是被引用的外部平台源码"），这 4+4 个文件的处理
方式与 `framework/android-runtime/` 下带 `_aosp` 后缀的文件是同一类推理，
只是它们连文件名都没有改、需要一个不会跟 `aosp_patches/` 的"patch"语义混淆
的新目录名。目录内部路径镜像其原始 AOSP 路径（`third_party/aosp_raw/
frameworks/base/core/jni/android_opengl_GLES{20,30,31}.cpp`、
`third_party/aosp_raw/frameworks/base/native/android/asset_manager.cpp`、
`third_party/aosp_raw/frameworks/native/opengl/include/{EGL,KHR}/*.h`），
方便对照上游。

### `compile_oh_android_runtime_arm64_stage2unity.sh` 的路径修正

取回的 GZ05 原始版本本身已经相当规范（`OH_ROOT` / `AOSP_ROOT` / `ADAPTER_ROOT`
均已是可覆盖的环境变量，没有裸写 `/data/adapter` 这类 GZ05 专属绝对路径），
只有 3 处需要修正：

1. `OH_ROOT` / `AOSP_ROOT` 默认值从 GZ05 专属的 `/data/oh` / `/data/aosp`
   改回本仓库统一约定的 `${OH_ROOT:-$HOME/oh}` / `${AOSP_ROOT:-$HOME/aosp}`；
   `ADAPTER_ROOT` 默认值从写死的 `$HOME/adapter` 改成脚本自身位置自动推导
   （`$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)`）。**更正**（codex
   round-1 复核指出的过度声称）：这个自动推导写法只是本仓库*较新一批*脚本
   （`compile_oh_android_runtime.sh`、`compile_oh_adapter_bridge.sh`、
   `cross_compile_arm32.sh` 等）的约定，不是全仓库统一状态——
   `compile_oh_adapter_runtime.sh`、`compile_oh_adapter_framework.sh`、
   `gen_boot_image.sh` 等仍默认 `$HOME/adapter`。本次新脚本对齐的是较新
   这批的写法，仓库整体的 `ADAPTER_ROOT` 默认值风格统一是一项独立的、
   本轮未处理的小清理，值得留给下一次顺手做。
2. `INC_AOSP` 里的 `-I$ADAPTER_ROOT/out/egl_inc` ——这个目录此前从未被本仓库
   任何脚本生成过，只是"曾经手工 scp 过一次"的隐性前提——改成指向新 vendor
   的 `-I$ADAPTER_ROOT/third_party/aosp_raw/frameworks/native/opengl/include`。
3. `SRCS_AOSP` 数组里 4 个 `"$A/frameworks/base/.../xxx.cpp"` 形式的条目改成
   `"$ADAPTER_ROOT/third_party/aosp_raw/.../xxx.cpp"`，不再读外部 `$AOSP_ROOT`
   树取这几个文件本体（`$AOSP_ROOT` 仍然作为头文件搜索路径的外部依赖保留，
   这与 `$OH_ROOT` 一样，属于"标准交叉编译工具链/上游源码树"范畴，按既定
   政策不需要 vendor 进代码仓库，只是不能再从它取"会被编译进我们自己产物的
   .cpp 文件本体"）。

`AOSP_LIB`（`out/aosp_lib64`，22+ 个预编译 AOSP native `.so`，
`liboh_android_runtime.so` 链接期依赖）改成 `${AOSP_LIB_DIR:-$ADAPTER_ROOT/out/aosp_lib64}`
可覆盖，但**没有**在本轮把它变成本仓库能从源码自产——见下"已知缺口"。

### 本地独立编译验证（OrbStack `westlake-build`，未碰任何真机设备）

`ADAPTER_ROOT` / `OH_ROOT` / `AOSP_ROOT` 均指向本仓库 + 外部工具链/源码树（通
过 OrbStack 的 `/mnt/mac/...` 只读挂载访问，语义上等价于"本机有一份 OH SDK
和一份 AOSP 源码树摆在某个路径"，跟直接在 Mac host 上跑没有本质区别，只是
`clang++` 是 linux-x86_64 ELF，必须在 Linux 环境执行）。`AOSP_LIB_DIR` 指向
本机一份已存在的 arm64 预编译产物镜像（`/opt/17-TestLab/17.07-Build/
noice-oh61-fromscratch/deps/native/aosp_lib64`，只读消费，不写回，性质等同于
"外部预构建输入"，见下"已知缺口"）；`liboh_adapter_bridge.so`（链接期 `-loh_adapter_bridge`
依赖）从 GZ05 取回实际部署那份放进本仓库 `out/adapter/`（`out/` 已在
`.gitignore`，不会被提交）。

结果：**43/43 源文件编译通过 + 链接成功**（`SRCS` 数组 27 个 adapter 自写文件
+ `SRCS_AOSP` 数组 16 个 AOSP-ported 文件，实际编译日志逐条核对，43 条
`... OK (N bytes)`；脚本头部注释沿用旧版"39+"的描述性说法已一并修正，见下）。
产物 `liboh_android_runtime.so`（721432 字节）。`strings` 确认新门禁字符串 `[UNITY-CW] neutering hwui
HardwareRenderer (OHUB_VARIANT=%s, OHUB_UNITY_LIBDIR%s)` 和
`OHUB_UNITY_LIBDIR` / `betweenworlds` 均在产物里，确认 RenderThread 修复确实
被编译进了这次的产物。

**符号级对比**（`llvm-nm -D --defined-only`，对照 GZ05 当天实际部署产物
`liboh_android_runtime.so.deployed`，`md5 58d20467ed6e3ad7bb3d6860b75183e2`，
即 memory 记录里 3 次 truly-cold 验证时设备上实际在跑的那份二进制）：
部署产物 258 个导出符号，本仓库这次重建产物 259 个，**258 个完全重合，多出
的 1 个是 `_ZN7android36android_util_Log_isVerboseLogEnabledEPKc`**——这与
memory 记录的"GZ05 重建时 `android_util_Log.cpp` 刻意保持 GZ05 原状（更老的
版本）以匹配 `724009e2` 已知行为基线"完全吻合：本仓库的 `android_util_Log.cpp`
是持续维护的当前版本，比 GZ05 当时特意锁定的旧版本多这一个小 helper 函数，
是已知的、方向上"更完整而非更缺失"的差异，不是新引入的缺口。

### 已知缺口（成本过高，本轮未处理，如实列出）

1. **`out/aosp_lib64` 无法从本仓库源码自产**——arm64（aarch64-linux-ohos）
   下 22+ 个 AOSP native `.so`（`libandroidfw` / `libbase` / `libart` 等）的
   交叉编译脚本，本仓库只有 armv7（32位）版本 `build/inner/cross_compile_arm32.sh`，
   没有对应的 arm64 版本。真正的 arm64 生产脚本
   （`cross_compile_arm64.sh` + `cross_compile_extras_arm64.sh` +
   `cross_compile_minikin_stack_arm64.sh`，共 1000+ 行）活在一个完全不同的
   兄弟项目 `/opt/1F.Application/02.Noice/adapter/build/inner_arm64_5583/`
   （Noice app 的 adapter 变体，本 session 之前从未接触过，属于不同子系统），
   从未被 vendor 进本仓库。本轮的编译验证是把这份预编译产物当作"外部依赖"
   （与 `$OH_ROOT` 同一范畴）只读消费，验证了**用现成的 aosp_lib64 能编出
   symbol-parity 的 liboh_android_runtime.so**，但**没有验证 aosp_lib64 本身
   能不能从本仓库+纯源码重新产出**——这是当前最大的、尚未闭合的自包含性
   缺口。
2. **`liboh_adapter_bridge.so` 的 arm64 版本同理缺失构建脚本**——本仓库
   `build/inner/compile_oh_adapter_bridge.sh` 是 armv7 目标（2026-07-09 那次
   审计验证的是这一份），链接 `liboh_android_runtime.so` 需要的是 aarch64
   版本，其构建脚本同样只存在于 GZ05
   （`/data/adapter/build/inner/compile_oh_adapter_bridge_arm64.sh`），未
   vendor。本轮同样只读消费 GZ05 已编译好的 `.so`（放入 `out/adapter/`，
   `.gitignore` 覆盖，不入库）完成链接验证，未补上这个 arm64 版本的构建脚本。
3. 上述两点意味着：本仓库现在**能证明**"用一份现成的 arm64 依赖产物集合，
   可以从纯本地源码把 `liboh_android_runtime.so` 编出来、且符号级对得上生产
   部署版"，但**还不能证明**"从一棵干净的 OH+AOSP 源码树、不依赖任何预编译
   `.so`，完全在本仓库范围内把整条 arm64 链路编出来"。后者需要把
   `inner_arm64_5583/` 那一整套脚本（连同它们各自可能存在的、尚未审计过的
   硬编码路径）搬进本仓库并重新走一遍这次同款的路径审计——工作量与本轮
   任务（聚焦 `liboh_android_runtime.so` 一个目标）不对等，留给下一个专门
   处理"arm64 native 库全链路自举"的 agent。

### 系统性扫描结果（`build/inner/*.sh` 全量，排除 `build/_deprecated/`、`.bak`
文件、GZ05/ECS 远程编排脚本这三类已有既定排除原则覆盖的范围）

除上面两条已知缺口外，`grep -rEl "/opt/10\.Project|/opt/1F\.Application|
/opt/21\.Game/21\.Game|/data/adapter|/data/aosp|/home/HanBingChen|17-TestLab"`
对 `build/inner/*.sh` + `build/*.sh` 的命中，逐条核实后**全部是注释/文档性
引用**（记录某个来源的历史出处，如 `oh_headers_631_overlay/README.md`
说明 header 是从哪面镜像拷贝来的），**没有发现第二处**"活跃代码路径指向本仓库
以外"的问题；也没有发现除 `egl_inc` 之外，还有别的脚本存在"引用一个从未被
本仓库任何脚本生成过的 `out/` 子目录"这种隐性外部前提。

### 小结（补充上表）

| 目标 | 类型 | 范围判定 | 本轮结果 |
|---|---|---|---|
| `liboh_android_runtime.so`（arm64 / STAGE2-UNITY 完整 43 文件配方） | native .so | adapter 自己产物 | **43/43 编译 + 链接成功，符号级 258/258 完全对齐部署版（+1 个方向正确的已知差异），RenderThread 修复字符串确认在产物内** |
| `third_party/aosp_raw/`（4 个 raw AOSP + 4 个 Khronos 头） | 直接编译进产物的零 diff 上游源码 | 按既定"编入自己产物=需 vendor"原则纳入 | 已 vendor，md5 逐字节核对 GZ05 当天实际使用版本一致 |
| `out/aosp_lib64`（arm64 AOSP native 库预编译产物） | 外部预构建输入 | 构建脚本本身**不在本仓库范围内**（活在兄弟项目） | 未处理，已知缺口，清单已列 |
| `liboh_adapter_bridge.so`（arm64 版） | 外部预构建输入（相对本次目标而言） | 构建脚本本身**不在本仓库范围内**（活在 GZ05） | 未处理，已知缺口，清单已列 |

## 2026-07-10 追加：arm64 构建脚本 vendor + 隔离沙箱实测——脚本缺口已闭合，
但过程中发现一个更深层、此前从未记录过的第三缺口（OH_ROOT 从未为任何 arm64
product 跑过 ninja 构建），"0外链"最终判定仍为**未达成**

### 做了什么

把上面表格里"未处理"的两个构建脚本缺口对应的脚本本体，从
`/opt/1F.Application/02.Noice/adapter/build/inner_arm64_5583/`（Noice app 的
adapter 变体，本仓库此前从未真正 vendor 过这个目录的任何文件，只读引用过）
逐字节复制进本仓库 `build/inner/`，然后做了必要的路径改写（不是简单复制粘贴）：

- `cross_compile_arm64.sh`（631 行）、`cross_compile_extras_arm64.sh`（87 行）、
  `cross_compile_minikin_stack_arm64.sh`（494 行）、`compile_libhwui_arm64.sh`
  （1452 行）、`compile_oh_adapter_bridge_arm64.sh`（544 行）。
- 改动 1：产物目录 `out/aosp_lib` → `out/aosp_lib64`（避免和本仓库已有的
  armv7 流水线同名冲突；匹配本仓库已有的
  `compile_oh_android_runtime_arm64_stage2unity.sh` 的 `AOSP_LIB_DIR` 默认
  期望路径）。
- 改动 2：`OH_ROOT`/`AOSP_ROOT` 默认值 `/home/HanBingChen/{oh,aosp}` →
  `$HOME/{oh,aosp}`；`ADAPTER_ROOT` 默认值 `$HOME/adapter` → 脚本自身位置
  自推导（`$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)`），跟本仓库
  2026-07-09 对 armv7 twin 脚本做过的同款修复一致。
- 每个文件头部新增 `[VENDORED 2026-07-10]` 注释块，写明来源路径、为什么这
  属于同一个 "HanBingChen" WestLake adapter 工程谱系的构建工具链代码（不是
  Noice app 自己的私有业务逻辑）、本次具体改了什么。
- 逐字节 md5（vendor 前，Noice 原始文件）：`cross_compile_arm64.sh`
  `c7b17963c7ddf3ee7a6ea4cae322326c`、`cross_compile_extras_arm64.sh`
  `e4ee1675f859c68ffbf44ea9db802d7a`、`cross_compile_minikin_stack_arm64.sh`
  `84a5c7be6ab5f03d4ff1412e5bd4a148`、`compile_libhwui_arm64.sh`
  `617c2d4e300998ce3a19d1c99a93ed9a`、`compile_oh_adapter_bridge_arm64.sh`
  `e9edc8faae46f3a6bc37ffcc292dad1a`（vendor 后 md5 已变化，因为做了上述两类
  必要改写，diff 只在这些改写点，逻辑/编译参数/link 顺序未变）。

### 隔离沙箱实测（本轮新增，按用户要求把"能否单独把本目录拷到一台全新机器
上、不借助任何 `/opt/1F.Application` 或 GZ05 访问权限、从零编译"这个思考题
转成真实验证动作，不是口头回答）

在本机 OrbStack VM `westlake-build` 里用 `sudo unshare --mount --uts --net
--propagation private` 建立了一个真实的、内核级隔离的 mount+network
namespace（不是简单换目录/改环境变量的"心理隔离"）：

1. 把本仓库当前状态（含新 vendor 的 5 个 arm64 脚本）先 rsync 到 VM 自己的
   本地磁盘 `~/isolated_adapter_src`（`/dev/vdb1`，VM 原生 btrfs 卷，不经过
   mac virtiofs）。
2. 在新 namespace 里，把 OH_ROOT（`/mnt/mac/opt/10.Project/16-WestLake/
   16.12-HanBing/oh`）、AOSP_ROOT（`~/aosp-local`，已是 VM 本地磁盘）、上面
   rsync 好的 adapter 副本分别 bind-mount 到 `/isolated/{oh,aosp,adapter}`，
   然后把 `/mnt/mac`（承载 mac 宿主机整个文件系统的 virtiofs 挂载点，也是
   `/opt/1F.Application` 唯一可达路径）连同 `/Users`、`/Applications`、
   `/Library`、`/Volumes`、`/private` 全部 `umount -l`（lazy unmount，不影响
   已经 bind 出去的 `/isolated/*` 引用，这是标准的"先接到别处、再切断原路径"
   技巧）；同时 `--net` 参数直接给了一个全新的、除 loopback 外空的网络
   namespace。
3. 验证结果（真实命令输出，非推测）：
   - `ls /opt/1F.Application` → `No such file or directory`（直接路径、经
     `/mnt/mac/opt/1F.Application`、经 `/opt/opt/1F.Application` 三条路径
     全部不可达）。
   - `ls /mnt/mac` → 空目录（宿主机 virtiofs 整棵树已被切断，不是"看起来
     切断了但其实还能走"）。
   - `mount | grep -i noice` → 零命中。
   - `ip addr` → 只有 `lo`，`state DOWN`；`ping 8.8.8.8` → `Network is
     unreachable`；`getent hosts oh-build`（GZ05 的 `ECS_HOST`）→ 空——网络
     层面同样物理不可达，不依赖 DNS/防火墙这类可被绕过的软限制。
   - `/isolated/oh`、`/isolated/aosp`、`/isolated/adapter` 三个 bind 挂载点
     内容分别有 41/22/23 个顶层条目，证明输入本身完好（不是"隔离到连自己
     都读不了"）。

**这就是用户要求的"真实执行的构建动作"里"隔离沙箱"这一半，已完成且结论
明确：新 vendor 的 5 个脚本本身架构干净——只通过 `OH_ROOT`/`AOSP_ROOT`/
`ADAPTER_ROOT` 三个环境变量触达外部输入，在这个真实切断了 Noice 项目和
GZ05 网络的环境里，脚本**语法/结构层面**没有任何地方会因为访问不到
`/opt/1F.Application` 或 GZ05 而失败**——因为它们本来就不引用这两处（此前
的人工 grep 审计已确认，见下"全量 grep 复核"）。

### 全量 grep 复核（用户要求的第二种验证方式，两种都做了，不是二选一）

对 vendor 后的整个 `02.unity.cardwords/adapter` 目录树（不止新增文件）跑：

```
grep -rlE '/opt/1F\.Application|/data/adapter|GZ05|ECS_HOST|inner_arm64_5583|oh-build' \
  --include='*.sh' --include='*.cpp' --include='*.h' --include='*.py' \
  --include='*.md' --include='*.txt' --include='*.gn' --include='*.json' .
```

命中的所有文件逐条人工核实：全部是**文档/注释性引用**（README、
PROVENANCE.md 自己的历史记录、脚本头部新写的 `[VENDORED]` 溯源说明、
`build/pull_ecs_artifacts.sh`/`start_container_build_on_gz05.sh`/
`run_gz05_container_build.sh` 三个已知的、不在 `build_all.sh`/
`build_adapter.sh` 调用链上的历史遗留可选脚本），**零处是会在构建期实际
执行的、指向 Noice 或 GZ05 的活跃代码路径**。`compile_oh_android_runtime_
arm64_stage2unity.sh`（此前会话遗留的既有文件，本轮未新增）里大量 GZ05/
Noice 字样也全部是历史沿革注释，不是代码。

### 隔离沙箱里跑真实构建，暴露出一个此前从未记录过的第三缺口（比原先两条
更深层，直接导致"0外链"依然不能判定为达成）

按用户"必须真的跑一遍，不能只改脚本就假设能行"的要求，在上述隔离环境里
用 `OH_ROOT=/isolated/oh AOSP_ROOT=/isolated/aosp ADAPTER_ROOT=/isolated/
adapter` 依次执行 `cross_compile_arm64.sh`→`cross_compile_extras_arm64.sh`
→`cross_compile_minikin_stack_arm64.sh`。**编译大面积失败**——不是"找不到
Noice/GZ05"这类外链错误，而是最基础的 C 标准头文件都找不到：
`fatal error: 'string.h' file not found`、`'features.h' file not found`。

逐层排查根因（非推测，逐条命令验证）：

1. 脚本用 `$OH_OUT="$OH/out/wukong100"` 作为 OH 产物目录（这是 Noice 自己
   设备 "5583" 的 product name，和本仓库 armv7 脚本已经在用、已验证工作的
   `$OH/out/rk3568`——对应 DAYU200/RK3568 板级——是两个不同的 product）。
2. 本机 `OH_ROOT`（`/opt/10.Project/16-WestLake/16.12-HanBing/oh`）的
   `out/` 下确实有一个 `wukong100` 目录，但 `find` 递归只有 **51 个文件**，
   且分两批、每批内所有文件 mtime 精确到秒完全一致（一批是 musl crt 目标
   文件+`libc.a`/`.so`，另一批是 `packages/phone/system/lib64` 下约 20 个
   精确对应 `compile_oh_adapter_bridge_arm64.sh`/`compile_oh_android_
   runtime_arm64_stage2unity.sh` 链接需要的系统库）——这是 `cp -p`/`rsync`
   批量拷贝进来的特征，不是 ninja 增量构建几千个文件、时间戳分散的特征。
   `out/wukong100/obj/third_party/musl/usr/include` 目录**完全是空的**
   （0 个文件，含目录本身都没有生成 `bits/alltypes.h` 这类 musl 自己构建期
   生成的头文件），直接导致 `--sysroot` 找不到任何 C 标准头。
3. 核实这个 OH_ROOT 源码树本身：`vendor/`、`device/` 下只有 `rk3568`（含
   `device/board/hihope/rk3568`、`device/soc/rockchip/rk3568`）有真实板级
   配置且已被 ninja 构建过（`out/rk3568` 有 15520+ 个文件，`bits/
   alltypes.h` 真实存在于 `out/rk3568/obj/.../arm-linux-ohos/bits/`）；
   `wukong100` **在 OH_ROOT 源码树的 `vendor/`/`device/`/`productdefine`
   下找不到任何对应的 product 定义**——即这个 product name 在这棵 OH 源码
   树里根本不是一个可以被 `./build.sh --product-name wukong100` 构建出来
   的合法目标，`out/wukong100` 这个目录完全是人为放进去的缓存，不是这棵
   源码树自己的构建产物。
4. 找到了这些文件真正的来源候选：`third_party/musl` 的 aarch64 头文件
   **确实存在于 OH_ROOT 源码里**（`$OH/third_party/musl/arch/aarch64/
   bits/alltypes.h.in`），但只是模板（`.h.in`），真正生成 `bits/
   alltypes.h` 需要 musl 自己的构建脚本跑一遍（这是 OH ninja 构建
   `third_party/musl` target 时自动做的一步，不是简单拷文件）；同时在
   **另一个兄弟 WestLake 项目** `/opt/10.Project/16-WestLake/16.13-Yue/
   local-arm64-build/oh61-wukong100/out/wukong100/`（跟 Noice、GZ05 都
   无关，是另一条 WestLake 路线自己本地做的一次完整 arm64 OH 构建）找到
   了一份**真正完整**的 `wukong100` 产物（`bits/alltypes.h`、
   `string.h` 等均真实生成存在）——但这恰恰反过来证实：本仓库当前所在的
   这棵 `OH_ROOT`（16.12-HanBing）**自己从未为任何 arm64 product 跑过
   ninja 构建**；16.13-Yue 那份是另一条独立路线、用另一次独立构建产出的
   结果，直接拿来用等于把"从 Noice 拿预编译产物"换成"从 16.13-Yue 拿预
   编译产物"，同样不满足"本仓库自己的脚本 + OH_ROOT 源码树能从零编出来"
   这个要求，本轮未采用。

### 本轮判断：脚本层面的两个缺口已闭合，但完整链路仍然跑不通，"0外链"
维持"未达成"，且缺口比上一轮记录得更深

- ✅ **已闭合**：arm64 版 `out/aosp_lib64` 和 arm64 版
  `liboh_adapter_bridge.so` 各自的**构建脚本本体**，现在都活在本仓库
  `build/inner/` 里，参数化、无 Noice/GZ05 硬编码依赖，经隔离沙箱证明
  不依赖 `/opt/1F.Application`/GZ05 网络访问。
- ❌ **仍未闭合，且是本轮新发现的更深层原因**：这些脚本要能真正跑通，
  前提是 `$OH_ROOT/out/<product>` 下有一个**真正 ninja 构建过的 arm64
  product** 提供完整 musl aarch64 sysroot（含生成头文件）+ 一批 OH 系统
  service `.so`。本机这棵 `OH_ROOT` 源码树里**存在**可用于 arm64 的
  product 候选源码（`vendor/hihope/dayu210`、`vendor/ohemu/
  qemu_arm64_linux_min` 均带 `target_cpu` 64 位配置），理论上"从源码
  构建出这个前提"是可行的，但这本身是一次独立的、量级完全不同的工作
  （完整 OH ninja 构建，历史上armv7 那次就耗时可观，arm64 预计同等或
  更高；不是"再改几个脚本"能完成的），本轮受时间约束未执行，如实标注
  为**未完成、非本轮范围**，不包装成"已解决"。
- 连带结论：上表"`liboh_android_runtime.so`（arm64 / STAGE2-UNITY）
  43/43 编译+链接成功"这条历史记录，其编译期依赖的 `out/wukong100` 在
  本轮实测时已经是这个不完整状态（`usr/include` 为空），说明该记录成立
  时 `out/wukong100` 处于另一种（更完整但同样未记录来源的）状态——这棵
  VM 共享环境的 `out/wukong100` 内容在不同会话之间发生过未被记录的漂移，
  这本身也是一个值得后续关注的、独立于本次 vendor 工作的环境卫生问题。

### 视频突破产物（`android_media_MediaPlayer.cpp`）连带验证结果

`build/inner/compile_oh_android_runtime_arm64_stage2unity.sh` 的 `SRCS`
列表里确认已经包含 `android_media_MediaPlayer.cpp`（第 325 行）。但由于
上述第三缺口（`out/wukong100` 不完整）在本轮隔离沙箱测试中先于这一步
就已经大面积编译失败，**没有走到 stage2unity 这一步**，因此**没有能够
实际验证**"video 突破产物现在能否完整链接通过"这一连带效果——这不是
video 产物本身的问题，是同一个上游环境缺口挡住了整条 arm64 流水线，
如实标注为**待验证，本轮未达成**（不是"验证失败"，是"没有条件跑到那
一步"）。
