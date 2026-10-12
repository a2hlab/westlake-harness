spec: task
name: "Route B deployed executable alias identity"
inherits: project
depends: [t5-executor]
---

## 意图

修复本轮真实开机的父进程身份误拒绝。已采 PID 5153 的实际 exe 为 /data/local/tmp/asx/appspawn-x，SHA、UID、私有命名空间、run.sh inode、窗口字段全部符合；旧判断只接受 asx-spawner，导致桌面点击后 START_FAILED。

## 已定决策

- 新版本仅增加已证明的绝对路径别名，保留 SHA、UID、birth、私有命名空间和 inode 检查，拒绝按 basename 或进程名放行。
- 父进程与子进程守卫分别核实；信号约束不放宽，主 appspawn 永远不接受信号。
- 保留原976与80及9436发布原件；在新包一次刷新修改文件、entry硬编码SHA、members和startup绑定。

## 边界

### 允许修改
- benchmark/2026-10-12-recovery-exe-alias/**
- tools/spec-checks/tests/recovery_exe_alias.rs

## 验收标准

场景: 真实父进程路径的已知答案通过
  测试: recovery_exe_alias_identity
  假设 使用新开机采得的绝对exe路径及逐项身份字段
  当 执行新候选的实际parent_owned函数
  那么 appspawn-x别名通过而原asx-spawner合法对象仍通过

场景: 身份字段漂移拒绝
  测试: recovery_exe_alias_reject
  假设 SHA或UID或birth或命名空间或inode有一项不符
  当 运行候选守卫
  那么 每种不符均非零且没有信号或启动动作

场景: 包内绑定完整且历史原件不变
  测试: recovery_exe_alias_bindings
  假设 新候选全部文件已冻结
  当 核对entry及members及startup与原始发布
  那么 每个新绑定匹配实际字节且原9436与976与80保持原SHA

## 排除范围

- 实机写入、重启、签字、内存崩溃根因、恢复适配器扩展、放松身份条件。
