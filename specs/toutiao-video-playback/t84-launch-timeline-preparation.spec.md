spec: task
name: "T84 parallel preparation for ordinary launch timing evidence"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
就绪谓词的14例离线回放未发现误拒；准备一次可区分前台切换、就绪拒绝和后续hold的普通启动时间线采集。先准备工具与证据判定，本卡不执行重启、启动或trace录制。
## 已定决策
- CC capability车道仅只读61b锁/boot及hitrace/uitest/aa本机help和支持类别，不启动trace，不改设备。只选择窗口/Ability/调度元数据，排除内存、故障、第三方安全机制和网络内容。3分钟首交实际支持命令及错误。
- cx-env collector车道离线制作有绝对单调截止的现有记录工具包装器：时间戳、argv、rc、stdout/stderr分离，普通WMS/ps/事件采集；只生成可审查计划，不执行hdc。复用既有rec.py及采图流程，用假命令测试截止、首失败、原始输出保留，不做启动控制。
- cx-seal historical车道离线抽取T61B/T72成功画面附近已有普通WMS/ps/点击/启动事件，表中逐项SHA/时间/boot，缺采样不得补造。不得查源码或故障记录。5分钟首交，记录成功和失败的证据覆盖差别。
- cx-reentry-peer analysis车道制定比较字段和可证伪判据：点击时间、宿主PID与窗口ID、focus状态、启动命令返回、首次新child/首次feed；所有跨时钟需明确转换依据。不得把后来focus当拒绝瞬间证据，不检查watchdog/reentry源码。
- 四车道写不同子目录，只commit各自分支或既有批准的path-only交件，不push。不能因工具不足切换权限或绕过拒绝；CC等待外环审查收齐后的独立执行卡，准备完成不等于白屏已修。
## 边界
### 允许修改
- benchmark/2026-10-23-launch-timeline-preparation/capability/**
- benchmark/2026-10-23-launch-timeline-preparation/collector/**
- benchmark/2026-10-23-launch-timeline-preparation/historical/**
- benchmark/2026-10-23-launch-timeline-preparation/analysis/**
### 禁止
- 设备写入、trace录制、启动/重启/关闭进程、数据或配置修改、守护/重入源码诊断、故障与内存分析、权限变化
## 验收标准
场景: 可形成支持的时间线采集计划
  审核: human
  测试: launch_timeline_preparation_review
  假设help能力和历史证据可读
  当各车道交付独立计划与假命令回放
  那么采集计划有单调截止和原始回执，并区分被支持命令与未验证假设，不访问设备写入
场景: 能力缺失或证据不足
  审核: human
  测试: launch_timeline_preparation_review
  假设命令缺失、数据无时间绑定或工具拒绝
  当遇到对应边界
  那么保留原文并将字段标unknown，不扩大扫描、不记录虚假trace执行或修复成功
## 排除范围
真正录制、启动实验、代码部署、APK内部诊断、冷启动封板。
