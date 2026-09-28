spec: task
name: "T3 Flutter 扩展 GL proc 缺口"
inherits: project
tags: [flutter, gles, native, claude-only]
---

## 意图

6 个 Flutter app 全部未亮。LocalSend 已定位:此版 libflutter 默认走 Impeller 并废弃了 opt-out,首帧在 `libflutter+0x4b6560` 调用 `.bss` 分发表槽 #468 的空函数指针,原因是某个扩展 GL proc 在 OH 驱动的 `eglGetProcAddress` 上返回 NULL。本任务先证明记录器挂在真实调用链上,把崩溃槽对应到具体 proc 名,再用 GLES shim 补上。交付性质是诊断加 LocalSend 点亮尝试;其余 5 个 Flutter app 用同一 shim 重扫并逐图人审,「多数点亮」不作门槛。LocalSend 的 blocker 已具名,本任务是 T1 开工门的批准例外。

## 已定决策

- 记录器只导出 `eglGetProcAddress`,`dlsym(RTLD_NEXT)` 转发,不改返回值;每条记录写目标进程、记录器与 libflutter 的实际加载路径和哈希、原函数地址、调用方返回地址所在的库
- LD_PRELOAD 库不导出任何 libc 符号(导出 `sigaction` 会破坏 OH 运行时的 dlopen,见 DIGEST D补)
- 安卓对照用驱动级探针:同一批 proc 名分别在安卓参考机(Mali-G57)与 OH 板上直接调用 `eglGetProcAddress` 查询,得到两端的 NULL/非 NULL 表;安卓上的 LocalSend 走 Impeller-Vulkan、不查询 GL proc,所以不用 app 级追踪做对照
- 崩溃槽 #468 须对应到具体 proc 名(给该槽赋值的那次 `eglGetProcAddress` 调用),缺口以此为准;`oh_null ∩ android_nonnull` 只作旁证
- 补口顺序:该名字去掉 `EXT`/`OES` 后缀的核心版在驱动上有导出,且 Khronos 头文件里两者签名一致时才转发;否则逐 proc 判断是否承重,只对证实不承重的 proc 给 no-op stub(被调时打 `[gles_shim] CALLED <name>`),承重的记 `next_blocker`
- shim 经 `native_libraries` 带入 staging,不改 APK;使用独立的 app-input 副本与 OUT_ROOT
- 所有 OH 侧运行在与 5ea `framework-2`(cab462ff)同一构建的基座上;5cd 的 `framework-1`(81b2dbd1)上 libflutter 映射报 EACCES,不作判定用

## 边界

### 允许修改
- benchmark/*-flutter-gles-procs/**
- tools/spec-checks/**

### 禁止
- 不对 libflutter.so 打二进制补丁
- 不修改 OH 系统分区的 GLES 库
- 不修改共享的 `~/a2hlab/app-inputs/localsend`

## 验收标准

场景: 记录器挂在 libflutter 的真实调用链上
  测试: t3_recorder_hits_libflutter_callsite
  假设 记录器随 LocalSend 部署在一块持锁的白名单板上
  当 LocalSend 走到首帧
  那么 至少一条记录的调用方返回地址落在 libflutter.so 内
  并且 记录里的 libflutter 哈希与 APK 内的一致

场景: 记录器未命中时记 unknown
  测试: t3_recorder_miss_marked_unknown
  假设 挂上记录器后首帧前没有任何 `eglGetProcAddress` 记录
  当 生成 `results.json`
  那么 `oh_null` 记为 `unknown`,不输出任何推断的名单

场景: 记录器点名 OH 上返回 NULL 的 proc
  测试: t3_recorder_names_null_procs
  假设 记录器已证明命中 libflutter 调用链
  当 LocalSend 走到首帧
  那么 `results.json` 的 `oh_null` 列出全部返回 NULL 的名字及各自调用顺序

场景: 驱动级对照给出两端查询表
  测试: t3_android_driver_oracle
  假设 同一批 proc 名分别在安卓参考机与 OH 板上用驱动级探针查询
  当 汇总两端结果
  那么 `results.json` 的 `driver_table` 对每个名字给出安卓与 OH 两端的 NULL/非 NULL
  并且 记录两端的 GL_VERSION 与扩展串

场景: 崩溃槽对应到具体 proc
  测试: t3_crash_slot_mapped
  假设 LocalSend 在 `libflutter+0x4b6560` 调用槽 #468 的空指针
  当 比对给该槽赋值的那次 `eglGetProcAddress` 调用
  那么 `results.json` 的 `crash_slot` 写明槽号、偏移与对应的 proc 名

场景: 记录器与 shim 不导出 libc 符号
  测试: t3_preload_exports_no_libc_symbols
  假设 构建出的记录器与 GLES shim 两个 `.so`
  当 用 `readelf --dyn-syms` 列出已定义的导出符号
  那么 导出集合只含 `eglGetProcAddress` 与 `gl*` 名字
  并且 不含 `sigaction`、`malloc`、`dlopen` 等 libc 符号

场景: 签名一致的核心版优先转发
  测试: t3_forward_preferred_over_stub
  假设 某个 `*OES` proc 在驱动上有去后缀的核心版导出,且两者签名一致
  当 shim 解析该名字
  那么 返回的是核心版函数地址
  并且 该名字不出现在 `[gles_shim] CALLED` 的 stub 日志里

场景: 承重 proc 不用空实现冒充
  测试: t3_stub_only_non_load_bearing
  假设 缺口里某个 proc 的返回值或输出参数会被首帧逻辑使用
  当 设计补口
  那么 该 proc 不给 no-op stub,`results.json` 记它的签名、语义与 `next_blocker`

场景: LocalSend 越过 pc=0 崩溃
  测试: t3_localsend_passes_first_frame
  审核: human
  假设 GLES shim 覆盖崩溃槽对应的 proc
  当 启动 LocalSend 并等待 30 s
  那么 没有 `libflutter+0x4b6560` 处的崩溃
  并且 外环读图签认后交付状态记 `lit`,否则按正证据记 `advanced` 或 `no-change`

场景: 其余 Flutter app 用同一 shim 重扫并逐图人审
  测试: t3_other_flutter_apps_resweep
  审核: human
  假设 fd-fluffychat、fd-immich、fd-kitchenowl、fd-libre、fd-saber 使用同一 shim
  当 逐个重扫
  那么 `results.json` 为每个 app 记录交付状态、截图路径与首个 blocker,新增 `lit` 均有外环签认

场景: 最终 shim 上的回归
  测试: t3_final_shim_regression
  审核: human
  假设 13 个 LIT app 在装有最终 shim 的同一基座上重扫
  当 外环逐张读图
  那么 13 个全部仍判为 LIT

场景: 记录器导致启动失败时标记不可用
  测试: t3_recorder_breaks_launch_detected
  假设 挂上记录器后 LocalSend 在首帧之前退出,而不挂时能走到首帧
  当 比对两次启动
  那么 `results.json` 标记记录器不可用
  并且 记录退出信号与原文证据行

## 排除范围

- Impeller 渲染正确性(颜色、动画、性能)
- 非 Flutter 的 GL app
