spec: task
name: "T27 bounded buffer metadata observation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t26-yv12-presentation]
tags: [draft, offline, observation, source-reuse]
---
## 意图
为下一轮**同一 native 版本**补齐只读 buffer 元数据观测:CPU 侧 actual layout / native config,以及 R23 import config 与 **actual create 地址**,用于定位 EGL create-null 的 buffer descriptor 与真实 create 槽。只记录,不改任何原始操作结果与 rc;本缺口与 YV12 presentation(T26)、EGL-null 根因分开。本轮只交 spec/蓝本与 parse/lint,实现待外环采认草案后另行授权;草案通过不代替测试,也不授权设备或上板。

## 已定决策
- 严格复用 cx `t25-observation-blueprint` 的四处既有插入点,不新增代码路径:① R15 `provider_adapter.c:77–81`(转换成功、CONVERTED 发布后、回 R14/map 前);② **Android 最终输出:在 T26 `prepare_output` 之后、publish 之前**(answer 完成),记录**实际返回的 YV12 scratch**(width/height/pixel-stride/format),**原生 packed descriptor 另记**;③ R23 `egl_import.c:56`(create_buffer 返回非空、仍持有新 window-buffer 时);④ R23 `egl_import.c:73–75`(被选 create_image 调用前后)。
- **调用计数**:原生命周期/变更类 provider 调用(lock/map/flush/request/release 等)计数**不变**;已准入的 `GetConfig`/`FromNativeWindowBuffer` getter 调用**允许且单独计数**;getter 缺失或解析到外来实例时**零 getter 调用**(标 UNKNOWN,不调用)。
- **交付形态(集成不等长报告)**:交 `observer.c/h` + **明确接线 patch/接口**;T26 的 R14/R15 派生 glue 由 **cx 拥有**,**不交整份 R14 覆盖 T26 seam**,只给 observer 在四点被调用的接口与补丁位置;R23/platform 派生副本可在 **T27 独立持有**,最终由 cx 统一链接。**先交最小 API 给 cx**,再补实现与 host 测试。
- 只经**已验证 provider getter**:`OH_NativeBuffer_GetConfig`(无 rc、5 个 signed32 字段、usage 仅 `usage_low32`、上 32 位 UNKNOWN)与 R23 侧既有公共 `FromNativeWindowBuffer`;且只通过**已持有的** T20 owner / R23 HWUI handle 解析。**禁止新 dlopen(含 NOLOAD)、raw +0x18 尾读、MapPlanes、额外 map/acquire/reference、新 C++ getter**。缺失或解析到非已验证 provider 实例 → 该字段 UNKNOWN,不把原本成功的操作改成失败。
- actual create 地址:将被选 create_image 函数指针复制一次,`dladdr` 记 address/base/file/relative offset,并记 display/context/target/window-buffer/attribs 指针;然后调用**同一指针一次**并记返回。**不得用 current-display provider 的 base 冒充该函数 owner**;attribs 指针不做无界遍历,其内容属另一 exact-caller 调查。
- EGL error 由既有路径负责,**T27 不额外 consume `eglGetError`**(它会消费 application-visible thread-local 错误态);HWUI caller 已读该错误,其 `SkDebugf` 输出可能落在 hilog。EGL error 在本观测留 UNKNOWN,除非原 caller 已记录。**操作注记(非 T27 代码):下轮取 EGL error 应在触发后、回滚前以实际 PID `hilog -z` 有界采集,不以只读 stderr 无 error 推断路由。**
- 记录的 `GetConfig.format`(与 import 侧真实 descriptor)用于**离线对照** Mali 当前恢复态 `eglCreateImageKHR` 接受集(exact `e0cb1081` @0x33e814:`{3,12,13,20,24,25,28,29}`;`11` 直接 NULL 不入 Impl)以**确认或证伪** create-null 的 buffer 格式预测。对照仅在分析侧完成:T27 **不读 Mali、不改 EGL target/context/attrs、不读 raw +14 header**;格式只来自公共 `GetConfig`。
- 生命周期:CPU 侧由既有 owner/request 引用保护,采样须在 flush/abort 前;import 侧由 create_buffer 成功引用保护,采样须在 release_failed_create/destroy 前。**不新增 acquire、不泄漏引用、不改返回值**;并发沿用原 table/provider 同步,诊断不得制造 lock-order 反转。
- 记录为**有上限**的结构化事件:固定 **256** 槽(编译期常量),每事件带 PID/TID/事务 ID 与操作 ID;**满时丢弃最新事件并递增 `dropped` 计数**(不覆盖旧、不无界增长)。**每条记录在产生时同步写入现有 stderr 日志出口(有界 256 行,到顶一条 drop marker),崩溃前即可见,不仅存内存 ring 等外部 drain**(内存 ring 仅供 host 快照)。输出**不等待消费者、不持任何新增 provider 锁、不新增无界分配或线程**;**不承诺所有 stdio 绝不阻塞**——仅保证不因观测持 provider 锁、不无界增长、不加锁序反转。
- **errno 语义**:纯观测入口(CPU/Android-output/import)保留**入口 errno**,完全透明;**create 入口以调用方 errno 运行真实 create_image(非 dladdr 的 errno),单次调用后立即捕获并事后保留 provider errno**(真实 create 行为不变),从不调 `eglGetError`。
- **独立新单元 + 明确派生 glue,仅在 T27 目录产生;最终由 cx 统一链接进 T26,本车道不自出另一上板版本**。原 T20/T23/T25/T26 及 R14/R15 原件只读。

## 约束
- 外环已采认:**允许离线实现 + host 测试**;仍**禁止设备、部署、HDC、推送、改旧冻结文件、以及独立上板/生产版本**。实现只在 T27 目录与允许文件内进行,最终由 cx 统一链接进 T26 单一上板版本。
- 未来实现仅可在 T27 目录产生源码、测试、配方、原始 receipt 与独立 Rust 选择器;不改播放器 ELF、EGL import 行为、网络或音频;构建前 `check_frozen`。
- 无任意 wrapper 解引用、raw 尾读、新 provider 加载、无条件成功、尺寸修正或 `eglGetError` 消费;`GetConfig` 无 rc、usage 仅 low32、不冒充完整 64 位。

## 边界
### 允许修改
- benchmark/2026-10-20-t27-buffer-observation/**
- specs/toutiao-video-playback/t27-buffer-observation.spec.md
- tools/spec-checks/tests/toutiao_t27_buffer_observation.rs
### 禁止
- benchmark/2026-10-20-t20-provider-link-slice/**
- benchmark/2026-10-20-t23-egl-import/**
- benchmark/2026-10-20-t25-geometry/**
- benchmark/2026-10-20-t26-yv12/**
- knowledge/frozen/**

## 完成条件
场景: CPU actual layout 与 native config 观测
  测试: ttvideo_t27_cpu_observe
  假设 真实派生 glue 在 R15 转换成功发布后、且 T26 prepare_output 之后 publish 之前,持有既有 owner/request 引用
  当 对已记录事务读取 GetConfig 与返回的 YV12 scratch 字段
  那么 记录 window/window-buffer/native 身份、操作 ID、GetConfig 的 width/height/format/stride/usage_low32、实际返回 YV12 scratch 的 width/height/pixel-stride/format,以及另记的原生 packed descriptor
  并且 native byte stride 与 Android pixel stride 分别记录不互相替代,flush/abort 后不读,原返回值与 rc 与原生命周期调用计数不变,getter 调用单独计数

场景: R23 import config 与 actual create 地址观测
  测试: ttvideo_t27_import_observe
  假设 R23 create_buffer 返回非空且新 window-buffer 仍被持有,被选 create_image 指针可复制
  当 经既有公共 FromNativeWindowBuffer 回转并 GetConfig,且 dladdr 该 create_image 指针
  那么 记录原 input native 指针、converted 指针、window-buffer、slot/generation,以及 create address/base/file/relative offset、display/context/target/window-buffer/attribs 指针与单次调用返回
  并且 不用 current-display base 冒充该函数 owner,attribs 不无界遍历,import 结果与 EGL error 状态不被改动

场景: getter 缺失或外来实例标 UNKNOWN 不改原结果
  测试: ttvideo_t27_unknown
  假设 GetConfig 或 FromNativeWindowBuffer 无法经已持有 handle 解析,或解析到非已验证 provider 实例
  当 执行观测
  那么 该字段标 UNKNOWN、不新 dlopen、不 raw 尾读,原本成功的 CPU 或 import 操作仍成功
  并且 errno 与 EGL thread-local 错误态保持;原生命周期/变更类调用计数不变;foreign 或缺失 getter 时零 getter 调用且不调用,已准入 getter 单独准确计数

场景: 有界记录与并发事务标识
  测试: ttvideo_t27_bounds
  假设 事件数超过 cap 且多线程并发事务
  当 真实路径持续产生观测事件
  那么 每事件带 PID/TID/事务 ID 与操作 ID,超 256 槽丢弃最新并递增 dropped 计数、不覆盖旧、不无界增长
  并且 输出不等待消费、不持新增 provider 锁、不增无界分配或线程(不承诺 stdio 绝不阻塞),不制造 lock-order 反转,不新增引用或 acquire

场景: 崩溃前有界 stderr 出口与 errno 语义
  测试: ttvideo_t27_durable
  假设 fixture 让 dladdr 与真实 create 各自改 errno,且事件数超过 256 打印上限
  当 四类观测入口在真实路径被调用并产生超限事件
  那么 每条记录在产生时即写入现有 stderr(至多 256 行),超限只计数并发一条 drop marker,内存 ring 仅供快照
  并且 纯观测入口保留入口 errno,create 入口以调用方 errno 运行真实 create 并事后保留 provider errno,全程不调 eglGetError

场景: 生命周期与引用不泄漏
  测试: ttvideo_t27_lifetime
  假设 CPU 侧在 flush/abort 前、import 侧在 release_failed_create/destroy 前采样
  当 观测完成
  那么 不新增 acquire、不泄漏引用、不重写返回值,采样严格在释放前
  并且 cache/pair/create-buffer 引用计数与原路径一致

场景: 缺证据拒绝与可复现构建
  测试: ttvideo_t27_receipt
  假设 构建先核冻结且使用已钉同 native 版本输入
  当 缺 exact 插入点证据或源/工具/依赖 SHA 或原始 rc0 日志,或 check_frozen 不通过
  那么 receipt 明确拒绝,不以事后清单补成通过
  并且 完整输入时先重链基线 byte-identical 再产独立观测候选,原始失败日志保留

场景: 离线观测不升级播放签认
  测试: ttvideo_t27_receipt
  审核: human
  假设 真实 C 与构建证据完成而实际新窗口尚未授权
  当 外环审核蓝本与 receipt
  那么 结果最多 OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED,实际 writer/EGL 结果保持 unknown
  并且 不称视频 PASS、不改历史 API 等级,最终由 cx 统一链接进 T26 单一上板版本

## 排除范围
- 本轮实施授权、设备观测、部署、播放器修改、EGL null 归因、色彩空间扩展、任意 YUV 支持、随机退出诊断、独立上板版本与长期封板。
