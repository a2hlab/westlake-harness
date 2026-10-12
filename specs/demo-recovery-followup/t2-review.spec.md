spec: task
name: "Independent recovery review and bounded execution recipe"
inherits: project
depends: [t1-watchdog]
---

## 意图

从真实部署脚本和本轮 83–93 原件独立建立故障与所有权表，准备默认仅预览的最小变更、验证与回滚配方，识别当前 seal run 是否仍可用及何种变更必须新计划。随后审 t1 候选具体字节，输出 blocker/accept；没有候选时先交真实对象审查，不空等。

## 边界

### 允许修改
- benchmark/2026-10-12-toutiao-recovery-review/**
- tools/spec-checks/tests/toutiao_recovery_review.rs

## 验收标准

场景: 当前证据身份一致
  测试: toutiao_recovery_review_evidence
  假设 本轮部署脚本、83–93 索引与本轮 receipt 均在本地
  当 生成审查表并重新计算来源 SHA
  那么 每项结论绑定当前 boot/PID/seq，旧 boot 材料仅为历史；来源缺失或哈希漂移则检查失败

场景: 默认预览零副作用
  测试: toutiao_recovery_review_preview
  假设 配方调用面下所有 hdc/kill/部署命令均被隔离假命令记录
  当 执行默认预览并输入过期或错误 boot/plan 授权
  那么 默认预览不执行板命令；错误授权拒绝且保留 stop、数据、原始证据与主 spawner

场景: 候选缺陷不能被签成通过
  测试: toutiao_recovery_review_candidate
  假设 候选缺失、未钉 SHA 或含自动同意/数据轮换/不安全 PID 控制
  当 执行独立审查并写结果
  那么 缺失为 pending，已知缺陷为 blocker；仅审查实际 SHA 且行为证据完整才给离线 accept，不签 UI/seal

## 排除范围

- 真实上板、运行时二进制修复、修改冻结登记、自动签封板与推送。
