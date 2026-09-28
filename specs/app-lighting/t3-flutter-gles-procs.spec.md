spec: task
name: "T3 Flutter 扩展 GL proc 缺口"
inherits: project
tags: [flutter, gles, native, claude-only]
---

## 意图

6 个 Flutter app 全部未亮。LocalSend 已定位:此版 libflutter 默认走 Impeller 并废弃了 opt-out,首帧在 `libflutter+0x4b6560` 调用 `.bss` 分发表槽 #468 的空函数指针,原因是某个扩展 GL proc 在 OH GLES 驱动的 `eglGetProcAddress` 上返回 NULL。本任务先点名缺失的 proc,再用 GLES shim 补上,目标是用同一个 shim 覆盖 6 个 Flutter app 中的多数。LocalSend 的 blocker 已具名,所以本任务不等 T0,可与 T0 并行。

## 已定决策

- 第一步只做记录器:LD_PRELOAD 拦截 `eglGetProcAddress`,把返回 NULL 的名字写 stderr,不改变返回值
- LD_PRELOAD 库不导出任何 libc 符号(导出 `sigaction` 会破坏 OH 运行时的 dlopen,见 DIGEST D补)
- 补口顺序:名字有驱动已导出的等价核心函数(`*EXT` / `*OES` 去后缀)时转发过去;没有等价物才给 no-op stub,并在被调时打 stderr
- shim 经 `native_libraries` 带入 staging,不改 APK
- 对照:同一记录器用 NDK 编一份 bionic 版,在安卓参考机 N100CU025C18D000128(userdebug,`ro.debuggable=1`)上经 `setprop wrap.<pkg> LD_PRELOAD=…` 挂到 LocalSend,取正常安卓上 Flutter 查询的 proc 全集;OH 缺口 = OH 上返回 NULL 且安卓上非 NULL 的名字

## 边界

### 允许修改
- benchmark/*-flutter-gles-procs/**
- tools/spec-checks/**

### 禁止
- 不对 libflutter.so 打二进制补丁
- 不修改 OH 系统分区的 GLES 库

## 验收标准

场景: 记录器点名缺失 proc
  测试: t3_recorder_names_null_procs
  假设 记录器随 LocalSend 部署在一块白名单板上
  当 LocalSend 走到首帧
  那么 stderr 至少有 1 行 `eglGetProcAddress NULL <name>`
  并且 `results.json` 列出全部返回 NULL 的名字

场景: 安卓对照给出 proc 全集
  测试: t3_android_oracle_proc_set
  假设 bionic 版记录器经 `setprop wrap.<pkg>` 挂到安卓参考机上的 LocalSend
  当 LocalSend 走到首帧
  那么 `results.json` 的 `android_queried` 列出安卓上查询的全部 proc 名
  并且 `oh_gap` 等于 OH 上返回 NULL 且安卓上非 NULL 的名字集合

场景: LocalSend 越过 pc=0 崩溃
  测试: t3_localsend_passes_first_frame
  审核: human
  假设 GLES shim 覆盖记录器点名的全部 proc
  当 启动 LocalSend 并等待 30 s
  那么 没有 `libflutter+0x4b6560` 处的崩溃
  并且 截图显示 LocalSend 自身界面

场景: stub 被调用时留痕
  测试: t3_stub_calls_logged
  假设 某个 proc 只能给 no-op stub
  当 app 运行期间调用它
  那么 stderr 出现 `[gles_shim] CALLED <name>`
  并且 `results.json` 记录该名字的调用次数

场景: 其余 Flutter app 用同一 shim 重扫
  测试: t3_other_flutter_apps_resweep
  假设 fd-fluffychat、fd-immich、fd-kitchenowl、fd-libre、fd-saber 使用同一 shim
  当 逐个重扫
  那么 `results.json` 为每个 app 记录判定、截图路径与首个 blocker

场景: 记录器与 shim 不导出 libc 符号
  测试: t3_preload_exports_no_libc_symbols
  假设 构建出的记录器与 GLES shim 两个 `.so`
  当 用 `readelf --dyn-syms` 列出已定义的导出符号
  那么 导出集合只含 `eglGetProcAddress` 与 `gl*` 名字
  并且 不含 `sigaction`、`malloc`、`dlopen` 等 libc 符号

场景: 有等价核心函数时转发而非 stub
  测试: t3_forward_preferred_over_stub
  假设 记录器点名的某个 `*OES` proc 在驱动上有去后缀的核心版导出
  当 shim 解析该名字
  那么 返回的是核心版函数地址
  并且 该名字不出现在 `[gles_shim] CALLED` 的 stub 日志里

场景: 记录器导致启动失败
  测试: t3_recorder_breaks_launch_detected
  假设 挂上记录器后 LocalSend 在首帧之前退出
  当 与不挂记录器的对照启动比对
  那么 `results.json` 标记记录器不可用
  并且 记录退出信号与原文证据行

## 排除范围

- Impeller 渲染正确性(颜色、动画、性能)
- 非 Flutter 的 GL app
