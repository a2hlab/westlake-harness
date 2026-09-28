# oh_headers_631_overlay — 6.1.0.31 (real device) interface-header shim

**这不是一棵 OH 源码树，只是 4 个接口声明头文件的只读快照。**

## 为什么存在

`app_scheduler_adapter.h` / `session_stage_adapter.h` 里两个方法
（`ScheduleMemoryLevel`、`NotifyAppForceLandscapeConfigEnableUpdated`）的
override 签名，在 2026-07-09 被改成对齐真机 HarmonyOS 6.1.0.31 的接口形状
（而不是本机唯一可用的、更老的 "api24" 代次 OH 源码树 `$OH_ROOT` 的形状）。
`compile_oh_adapter_bridge.sh` 用这里的 4 个文件替换 `$OH_ROOT` 里对应的
同名文件（`-I` 优先命中，见该脚本 `INCS_OVERLAY_631` 段的详细注释），使得
本地独立编译能验证到 link，而不必拥有一整棵 6.1.0.31 源码树。

## 来源

逐字节拷贝自 `/opt/1F.Application/02.Noice/adapter/local_oh_headers/oh_mirror/`
——另一个项目（Noice）的、面向真机 6.1.0.31/wukong100 世代的只读头文件镜像
（同一份镜像在 `/opt/10.Project/16-WestLake/16.13-Yue/local-arm64-build{,-YUE}/
oh61-wukong100/adapter/local_oh_headers/oh_mirror` 等处还有多份拷贝互相印证）。
拷贝时间：2026-07-09。详见仓库根目录 `PROVENANCE.md` "二次追加：代次缺口已解决"
一节，含完整 diff 核对记录。

## 文件清单（4 个，48K）

- `foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include/appmgr/app_scheduler_host.h`
  （与 api24 逐字节相同，只是为了让同目录下 `#include "app_scheduler_interface.h"`
  的 quote-include 落在本 overlay 目录内，不回退到 api24）
- `foundation/ability/ability_runtime/interfaces/inner_api/app_manager/include/appmgr/app_scheduler_interface.h`
  （与 api24 只差 1 行：`ScheduleMemoryLevel` 参数个数 2→1）
- `foundation/window/window_manager/window_scene/session/container/include/zidl/session_stage_stub.h`
  （与 api24 相比减少了几个 V7-only 新增方法对应的 `HandleXxx` 私有声明，不影响
  本 overlay 关心的目标方法）
- `foundation/window/window_manager/window_scene/session/container/include/zidl/session_stage_interface.h`
  （与 api24 相比减少了几个 V7-only 新增纯虚方法，且目标方法
  `NotifyAppForceLandscapeConfigEnableUpdated` 参数个数 1→0）

## 明确不包含

appmgr/zidl 目录下其它同样存在代际差异的文件（`ams_mgr_*.h`、
`app_mgr_*.h`、`fault_data.h`、`app_jsheap_mem_info.h`、
`running_process_info.h`、`session_stage_proxy.h`、
`session_stage_ipc_interface_code.h` 等）——因为本仓库代码目前没有任何地方
对它们做 `override` 触发编译期检查，刻意不 vendor，避免引入未审计过的新漂移。
仍是残留风险，见 PROVENANCE.md 记录。
