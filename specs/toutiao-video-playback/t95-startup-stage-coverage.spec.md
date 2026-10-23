spec: task
name: "T95 ordinary successful startup stage coverage"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t93-existing-success-startup-log]
---
## 意图
T93前300行在APK扫描阶段截断，无法覆盖首次渲染前的普通启动进展。补收同一已有成功进程普通日志的128KiB前缀，依据显式阶段和时间记录缩小性能观测缺口。
## 已定决策
- 外环唯一采集者，先读61b0657200000000000000000324012c的锁与boot；他人持锁或boot不等于61aa5791-fd69-4bbb-a7b5-333b5d913c81立即停止。只stat及head -c 131072读取/data/service/el1/public/appspawnx/adapter_child_6291.stderr；零设备写入/截图/UI/重启/部署。
- 新原件落持久home独立目录，不覆盖T93。每命令15秒，总60秒；保留argv/起止/rc/stdout/stderr，核预期文件前缀和原T93前缀SHA，不能用应用正文No such file作传输失败。失败不重试，不换对象。
- Codex分析收到的普通启动阶段日志；仅提取初始化/资源加载/首个渲染相关阶段与显式时间，核覆盖是否到达首个trace marker。now时钟未证明则保留原数，不推阶段耗时、不判断退出原因。4分钟首次交件；只在自己analysis树写结果并提交、不push。
- 公开输出不含token/地址/网络/用户内容；私有原件不入仓库。CC不分析，无新REA、无T91动作或先前停止对象分析。
- Addendum 2026-10-23 T95B：首批128KiB已成功但截在WebView加载途中。允许同样前置/单命令/总时间约束下，独立一次收取同路径前4194304字节，落私有目录extended-01，不覆盖/否定首批；先核原128KiB前缀一致。这是扩大成功日志覆盖，不重试失败或被停止动作。此补充只有一次，不再按小段反复采；分析若仍不覆盖首次渲染则明确缺口。复核车道首批收尾后主责分析此新片段，时间锚点/阶段/脱敏限制不变。
- Addendum 2026-10-23 T95C：仅离线对照已保存T86普通日志末200行（私有existing-launch-output-20261023/raw2/tail.stdout，SHAdd9c799a1ecc7e0782cf72550eeee1c39fabc5b1b8a8a65d7eeb330e208f107a）和T95B成功前缀中的普通初始化检查点/明确Java依赖与配置提示。先核两件SHA和显式PID/墙钟身份；覆盖不等及旧行可能性保留，不把未见当未执行，不推信号/退出或内存原因。3分钟首交，无新采集；只判断是否存在可复现的普通初始化输入差异，缺证据不写修复。
## 边界
### 允许修改
- benchmark/2026-10-23-startup-stage-coverage/**
- 私有 $HOME/.local/share/westlake/startup-stage-coverage-20261023/**
### 禁止
- 设备写入、其他日志路径、运行时修改、故障/信号/内存分析、T91预检、先前停止对象
## 验收标准
场景: 成功取得有界前缀
  审核: human
  测试: startup_stage_coverage_review
  假设目标同boot且无holder
  当只读取指定日志前128KiB并核旧前缀一致
  那么按原始行号列阶段和有证时间，覆盖不足明确unknown，零设备改动
场景: 身份或传输失败
  审核: human
  测试: startup_stage_coverage_review
  假设boot变化、锁占用、超时或读取命令失败
  当前置检查或传输返回失败
  那么保存原始失败并停止，不重试且不把旧结果声明为新结果
## 排除范围
修复部署、冷启动签认及重试先前被停止动作。
