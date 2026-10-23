spec: task
name: "T89 bound host lifecycle and existing launch latency"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t87-current-boot-manual-reopen]
---
## 意图
保留61b当前可操作信息流，转离线定位普通桌面重开约27秒才spawn、约89秒见feed的延迟。以已部署HAP的源码链与现有ability/window trace为依据，避免将旧源码或缺少回调直接当根因。
## 已定决策
- Codex是分析owner，无板命令。起点是已核HAP b18978的T78结果、T32部署/构建证据、sources/api-implementations/source-build-host/westlake-java/apps/imehost/EntryAbility.js和T87既有trace；先核producer/input/output SHA链，未绑定的源码只能作为候选，不代表部署实现。
- 分析范围仅自有HAP的UIAbility普通生命周期/窗口加载和已录ability/window事件，不读watchdog/reentry脚本、不重试此前安全拒绝的源码或故障/内存分析。REA仅已批准且注册工具可用时对既有自有HAP做静态结构检查，不因工具缺失停主线，不换工具绕拒绝。
- 重用已有T87分段结论，不重做截图报告；从trace补出实际可证的宿主ready/foreground及child首窗口事件时刻。没有trace事件不等于没有执行，不从缺失onNewWant单独推因果，不把异步阶段总耗时全归HAP。
- 至多6分钟首交：若发现已绑定源码里的明确普通生命周期缺陷，给最小候选和能复现缺陷的离线测试；否则只给已证事实、剩余缺口和一项必要下一步，不能写无依据补丁或扩大搜索。报告至多一页，关键发现立即报外环。
- 不修改冻结件或部署配置；候选只放benchmark子目录，含来源SHA与测试命令。外环采认并走独立部署契约之前，不上板。没有候选也必须如实交unknown，保持全目标未完成。
## 边界
### 允许修改
- benchmark/2026-10-23-host-lifecycle-latency/**
### 禁止
- 任何设备调用、修改既有源或运行时、读取此前拒绝脚本、内存/故障归属、网络与进程操作、未绑定源码归因
## 验收标准
场景: 已绑定源码缺陷可独立复现
  审核: human
  测试: host_lifecycle_latency_review
  假设当前HAP与来源链可核且有明确生命周期错误证据
  当离线分析并执行候选测试
  那么提交来源SHA、原失败/候选通过的测试证据与最小候选，不宣称部署修复
场景: 来源或因果不足
  审核: human
  测试: host_lifecycle_latency_review
  假设来源未绑定或缺少可复现缺陷
  当6分钟限时结束
  那么交已证时段和缺口，结论unknown，无猜测性代码，无设备修改
## 排除范围
子进程退出根因、原神、冷启动验收、改写启动监督器、部署与封板签认。
