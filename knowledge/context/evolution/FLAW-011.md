---
kind: context
id: FLAW-011
title: "代理线索被提升为实际调用或因果证据"
repo: A2OH/westlake-harness
layers: [Verification, Measurement]
status: open
severity: S2
recurrence: 3
fingerprint: verification/proxy-not-target
issue:
cards: [EVO-0148, EVO-0149, EVO-0150]
filed: 2026-10-19
---

## 复发证据

- r3：直接使用 cppcrash 报告偏移和残留寄存器字符串推断调用参数；实际 PC、maps、PT_LOAD 和指令给出不同 ELF 偏移及 x0 参数。见 `benchmark/2026-10-19-toutiao-rea-methods/video-1919-r3-live-review/`。
- r4：普通 HWUI swap、未见 decoder 日志、可选 avmdl ENOENT 和一次线程等待采样被扩展为播放器渲染、未启动解码或网络排除。独立证据只证明三 GOT 槽正确、三组画面仍为封面。见 `benchmark/2026-10-19-toutiao-rea-methods/video-1919-r4-live-review/`。
- r5 静态：`addTask(PreloaderURLItem)` 正文仅委托 `_addTask`，未含 pending 原句；公开 `proxyUrl` 的零 DEX 入边也未覆盖反射、JNI、hotfix。不能据此断言 pending 仅属预加载或生产路径绝不调用。原 ACK 和外环纠偏保留在战役板；相关方法及完整 REA 结果位于内环 `static/evidence/r4-nextstate/rea-raw/`，修订未采认前不合入其因果判词。

## 处置

每个结论绑定对象 SHA、实际方法/指令/进程、证据范围与 unknown。字符串归属须在所引方法正文逐字存在，入口委托不能替代被调用方法；零入边须附扫描覆盖，不升级成运行时不可达。实际路径优先沿已观测栈 `VideoPlayerImpl.doPrepareAction → TTVideoEngine.play → X.4cC.play` 追踪。

外环已用精确原件 disassembly、进程内只读指针、REA normalized method 正文分别复核，纠偏同步内环。静态定位与运行时播放分开验收；文件名、目录标签、日志缺失都不替代截图或实际调用。

## 未完成

现有工具能提供精确证据，但尚无通用门禁约束自然语言因果声明。本记录保持 open；不能因新增散文规则就宣称该类错误已消除。
