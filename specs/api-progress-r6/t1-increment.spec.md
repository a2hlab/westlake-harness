spec: task
name: "Append one nativeUpdate row and regenerate original table CSV HTML"
inherits: project
---
## 意图

只新增NATIVE-173与独立签pin证据，调用原atlas生成表/CSV/HTML同步，不修改原314行。

## 已定决策

- 原schema与生成器源码逐SHA复用；只有新增一行与增量日期变化。
- 成功专属child用requested几何；主窗/failedchild用1200x1920；不根据SurfaceView名字就判成功。
- Boat root功能审定与五popup报告分别保留原boot和证据强度；全128和能力冻结pending。

## 边界

允许修改: benchmark/2026-10-13-api-progress-r6/**、specs/api-progress-r6/**、tools/spec-checks/tests/api_progress_r6.rs、README.md、.octos/KNOWLEDGE-DIGEST.md。
禁止修改: 原主树atlas/源码/runtime、冻结登记、设备、运行中的串行脚本与refs。

## 验收标准

场景: 一行增量与表CSV HTML原生成链一致
  测试: api_progress_r6
  假设 原314行和生成器固定全SHA且新R6证据均可读
  当 离线重建独立全图并校验所有视图
  那么 原314行逐字段相同且只有NATIVE-173新增
  并且 表CSV HTML同源与源hash校验及原缺证据负例保持

场景: 范围与证据不跨族不升格
  测试: api_progress_r6
  假设 实测Boat b711与五popup db429证据来源分离
  当 检查增量行的members/version/status/validations/gaps
  那么 仅nativeUpdate受限路径标partial且OH只有6.1.0.31
  并且 Androidunknown/source-only、full128 pending与frozen_ids空均显式保留
