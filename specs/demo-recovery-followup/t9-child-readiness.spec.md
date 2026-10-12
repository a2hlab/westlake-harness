spec: task
name: "Route B bounded child readiness and predicate evidence"
inherits: project
depends: [t8-exe-alias]
---

## 意图

为成功 spawn 刚返回的子进程添加短暂只读就绪等待，并将失败字段精确记入诊断。真实5968在仍存活时被拒，9544首次出生后60ms起24次检查全通过；UID竞态是未证假说，不能写成已确认根因。此候选改善异步初始化处理与可观测性，不放松最终身份判据。

## 已定决策

- 只对本轮成功spawn返回的唯一PID和首次birth允许最多2秒只读等待；显式attach继续立即完整校验。
- 只有四UID全0且SHA、exe绝对路径、birth、父PID、私有命名空间、run.sh inode均符合预期时可暂等；其他UID或任一身份漂移立即拒绝，最终仍调用原完整child_owned。
- 每次未通过输出机器可读的谓词名、实际值和期望值；全0超时、退出、读失败、boot变化均非零，不能发布READY或发信号。
- 提取新候选，不改原9436、0cc5及其发布字节；一次刷新watchdog、entry、members、startup绑定。父进程不可被信号处理，保留用户数据与历史stop。

## 边界

### 允许修改
- benchmark/2026-10-12-child-readiness/**
- tools/spec-checks/tests/child_readiness.rs

## 验收标准

场景: 新子进程从root过渡到准确宿主UID
  测试: child_readiness_transition
  假设 成功spawn的PID和birth固定且所有非UID身份检查匹配
  当 四UID由全0变为准确宿主UID并在2秒内通过原完整守卫
  那么 就绪成功且只读等待没有信号或额外spawn并保留逐项证据

场景: 永久错误与漂移不能被等待放行
  测试: child_readiness_reject
  假设 永久root、其他UID、错SHA、错路径、错父PID、全局命名空间、错inode、birth变化或boot变化的负例
  当 执行候选就绪检查
  那么 每项非零且报告具体谓词并无READY、信号或新增spawn

场景: 显式attach与发布绑定保持严格
  测试: child_readiness_bindings
  假设 现有进程attach与新候选发布文件
  当 检查attach分支和全部发布SHA
  那么 attach不使用等待分支且原严格守卫与历史原件不变并且新绑定逐项匹配

## 排除范围

- 板上执行、重启、签字、原随机SIGSEGV或WebView崩溃修复、恢复provider扩展、重试已退出的未接管子进程、放宽永久root-child身份。
