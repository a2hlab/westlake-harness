spec: task
name: "T114 owned host lifecycle evidence after retry-limit icon click"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t112-after-reboot-icon-recovery]
---
## 意图
T112已证RETRY_LIMIT之后一次普通桌面点击90秒没有新child。只读核自有HAP是否收到生命周期回调，区分用户事件到宿主与后续拉起两个环节，不因onNewWant源码缺失直接认bug。
## 已定决策
- CC唯一5cd只读采集：先held/boot/当前host PID与birth，序列号5cd1e3dd00000000000000000923012c；不新UI、重启、信号或配置写入。若holder冲突或身份不稳定停止。
- 精确HAP状态文件/data/app/el2/100/base/org.westlake.imehost/files/window-state.json，stat及最多8KiB内容；它是已绑定EntryAbility.js自己的filesDir记录，不读其他用户数据。保留mtime、字节SHA和当前event/time/details；最后一条可能覆盖之前回调，不能据此证明没发生。
- 沿T23已验证PID-tail规范读取普通host hilog：hilog -P ACTUAL_PID -z 2000 -L D,I,W,E,F -v epoch，host timeout8秒。不组合-x，正文CODE错误拒绝；保存完整私有原件，公开仅WL_IME_HOST回调字段和覆盖范围。采集前后boot/PID/birth复核，全批60秒停止。
- Codex接件离线对照T112一次点击真实时间与T89已经绑定的EntryAbility.js源9dc302d9，只分析自有HAP普通生命周期事件/文件覆盖。未覆盖点击时间或缺日志则unknown，不把无记录当无回调。没有明确缺陷不改代码；本卡不构建部署。
## 边界
### 允许修改
- benchmark/2026-10-23-host-lifecycle-after-retry-limit/**
- 私有 $HOME/.local/share/westlake/host-lifecycle-after-retry-limit-20261023/**
### 禁止
- 61b/5ea操作、UI和设备状态更改、停止对象T71/T74/T91、内存/信号故障或保护分析、部署
## 验收标准
场景: 点击窗口有宿主回调证据
  审核: human
  测试: host_lifecycle_after_retry_limit_review
  假设fresh身份和普通日志覆盖本次点击
  当对齐已有点击回执及HAP源事件
  那么给明确已发生的回调与原始行引用，区分后续无child，不泛化根因
场景: 日志缺失覆盖不足或读取失败
  审核: human
  测试: host_lifecycle_after_retry_limit_review
  假设PID变化、CODE错误、超时或日志未覆盖点击
  当形成结论
  那么保留原始失败并标unknown，不重放UI或猜事件，停止设备动作
## 排除范围
重试次数策略修改、随机退出原因、运行时构建部署、原神。
