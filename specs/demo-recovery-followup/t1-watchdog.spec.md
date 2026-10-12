spec: task
name: "Data-preserving Toutiao recovery candidate"
inherits: project
---

## 意图

以真实部署 watchdog 与 overlay 为基准，在独立目录实现可复核的恢复候选。修正自动同意、数据轮换、把截屏失败当应用失败以及无从识别人手同意这四项已知控制缺陷；同时保留进程身份守卫与失败退避。先找本地已验证实现，README 写来源路径与 commit。

## 边界

### 允许修改
- benchmark/2026-10-12-toutiao-recovery-candidate/**
- tools/spec-checks/tests/toutiao_recovery_candidate.rs

## 验收标准

场景: 人工隐私与截屏降级
  测试: toutiao_recovery_candidate_consent
  假设 真实候选在隔离目录使用假命令录制全部副作用
  当 输入 privacy、feed、snapshot_error 和 unknown 序列
  那么 隐私序列无自动触摸；feed 无需自动 consent 标志；截屏失败不清理仍活的应用、不冒报 UI READY

场景: 重入与恢复保留数据
  测试: toutiao_recovery_candidate_data
  假设 隔离测试的现存 app-data/data/webview 各有哨兵内容
  当 实际候选经过首次启动、进程退出和重复重入
  那么 内容不删除不轮换；重试有上限或退避；日志含 boot、seq、PID/birth 与具体失败原因

场景: 身份不符拒绝控制
  测试: toutiao_recovery_candidate_ownership
  假设 进程 PID 重用、根 appspawn-x、无主或仍有效的锁与 stop 标志
  当 实际候选尝试启动或清理
  那么 拒绝不匹配身份的信号和锁接管；stop 不自行清除；不杀主进程；命令返回失败可观察

## 排除范围

- 真实上板、运行时二进制修复、修改冻结登记、自动签封板与推送。
