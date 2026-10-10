spec: task
name: "First-board feedback: coverage grading and missed seccomp hints"
inherits: project
depends: [t1-capture]
---

## 意图

修复首次真板验收暴露的对比盲区；数据完整性与部署覆盖分开，不把标签差异升级成根因证明。

## 已定决策

- 每块板、每轮必须给独立 --out；既有原始证据不覆盖。
- 无计划是覆盖警告，完整采集的已观察字段仍可比较；complete 保持严格，推演器不借此放宽。
- sandbox JSON 标签、const.cust 参数与已采集 /system 路径的 data 标签计数列为非因果启发。
- 修前文本与修后快照分开；61b/5cd 已知答案只是注明来源和归一限制的字段回放。

## 验收标准

场景: Distinct board outputs preserve prior evidence
  测试: board_state_readonly
  假设 Two boards share a parent output directory
  当 Captures use distinct subdirectories and an old directory is reused
  那么 Separate captures succeed while reuse refuses without changing prior bytes

场景: Missing plan does not invalidate observed comparison
  测试: board_state_readonly
  假设 Reads and boot identity succeed without a deployment plan
  当 Snapshot coverage is graded and the snapshots are compared
  那么 Observed comparison is allowed but complete coverage remains false and raw drift still refuses

场景: The previously missed sandbox label becomes a hint
  测试: board_state_readonly
  假设 The sourced 61b and 5cd selected-field replay contains the sandbox label difference and 24 versus zero observed data labels
  当 Seccomp observations are generated
  那么 The sandbox label and scoped counts are present as noncausal hints even though filter SHA and cust parameters match
