spec: task
name: "U4 predictions and discriminating experiments"
inherits: project
---

## 意图

把离线候选变成可复核的上板步骤，区分过墙预测与上屏实测，记录失败拆分和恢复步骤。

## 已定决策

- 固定J3 25亮/41未亮与66键四片；N3b包含整个N3增量，U3不能只换runtime。
- J5 SHA、真实WebView输入及第四OH板未交付时保留未就绪，不发执行命令。
- 先控组后目标再四片全量；多变量结果不得归因，间歇先三次同条件复验。
- VLC追上下文/主题选择、Termux追finish调用者；缺诊断值返回unknown，不由白屏猜根因。

## 边界

### 允许修改
- benchmark/2026-09-30-u4-plan/**
- specs/u4-offline-plan/**
- tools/spec-checks/src/lib.rs
- README.md

### 禁止
- 板操作、生产代码修改、历史预测改写、自动分配第四板或替用户审批
- 用新JAR补齐boot类承诺、把功能过墙计新增亮

## 验收标准

场景: 逐app预测与分片覆盖
  测试: u4_predictions_cover_cohort
  假设 J3实测与四分片可读取
  当 生成逐key预期与来源SHA
  那么 66键无重无漏且25个既亮保护保留
  并且 未编入的修复不计候选收益

场景: 离线命令与缺件拒绝
  测试: u4_commands_fail_closed
  假设 第四板或J5输入仍缺
  当 请求四片执行命令
  那么 列缺件并非零退出且零设备IO
  并且 完整本地测试输入生成master批跑命令但不执行

场景: 判别实验与退路
  测试: u4_experiment_protocols
  审核: human
  假设 目前只能规划VLC与Termux运行期取证
  当 交付精确采集点、通过失败unknown判据与恢复顺序
  那么 计划先排多变量且不凭无日志判通过
  并且 设备效果与截图数均保留unknown
