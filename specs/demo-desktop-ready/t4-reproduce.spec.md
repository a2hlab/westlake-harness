spec: task
name: "Remote reproducibility audit and closure"
inherits: project
depends: []
---
## 意图
逐件核对V2运行时产物的源码快照、补丁序列、工具链哈希、构建脚本、rc0原始stdout/stderr与远端归档。独立区分部署恢复、确定性补丁重放、从源码重建；缺项不签全量可复现，优先复用已有新环境验证。

## 已定决策
- 原始证据与最终判断分别记录；raw rc、SHA、路径、来源与未知字段保持可追溯。
- 使用已验证脚本与实现；不推断未执行的设备行为或远端构建成功。

## 边界
### 允许修改
- benchmark/2026-10-14-demo-reproducibility/**
- tools/spec-checks/tests/demo_reproduce.rs

### 禁止
- 不修改原V2签认、冻结文件或其他车道工作区。
- 不以进程存活、静态命中或历史成功替代本轮证据。

## 完成条件
场景: 远程复现证据完整
  审核: human
  测试: demo_reproduce
  Given all runtime artifacts referenced by final V2 signoff
  When auditing persistent remote recipe receipts
  Then every artifact has a source-build status and an evidence-backed restore status

场景: 远程复现缺项明确
  审核: human
  测试: demo_reproduce
  Given an artifact without paired original build logs or source
  When evaluating reproducibility
  Then the row remains blocked or partial and not source-reproducible
