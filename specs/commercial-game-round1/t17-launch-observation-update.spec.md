spec: task
name: "G17 append actual icon launch observation"
inherits: project
depends: [t15-current-api-observations]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
将normal-ui-01实际启动失败加入正式观察表，避免安装记录被误读为尚未尝试启动，同时保留全部历史证据。
## 已定决策
- 主线89ce2f77bd的58条观察对象完整保留，追加1条普通图标启动观察；G13/G14历史记录不改。新条明确t2白屏/t20桌面、无游戏帧，原始日志显示exit1，三处错误分层不写成未经验证的根因。
- 证据仅引用normal-ui-01已入库原件/摘录/原始SHA与exact-static已有REA方法记录；不把OH安装或app启动状态当新增安卓API或冻结项。
- 用原renderer生成HTML/CSV/results并精确验SHA。G15旧checker调整为只严格验证其原58条前缀和8条新增快照，允许后续追加；旧G15结果不改。新checker严格验证59条、原58对象未动及引用一致。
- 报告说明G16定位仍在途，不采未经固定清单的G16草稿。输出path-only清单，原README行原样保留后追加说明，避免land丢行。
## 边界
### 允许修改
- benchmark/2026-10-19-api-progress-update/observations.json
- benchmark/2026-10-19-api-progress-update/observations.csv
- benchmark/2026-10-19-api-progress-update/index.html
- benchmark/2026-10-19-api-progress-update/results.json
- benchmark/2026-10-19-api-progress-update/README.md
- benchmark/2026-10-21-current-api-observations/check_observations.py
- benchmark/2026-10-21-current-api-observations/SHA256SUMS
- benchmark/2026-10-21-launch-observation-update/**
- tools/spec-checks/tests/commercial_game_launch_observation.rs
### 禁止
- 不设备、不REA、不编译运行时、不改原58对象/315历史/renderer/冻结项，不运行或重做G14/T38，不push。
## 验收标准
场景: 历史追加保持
  测试: commercial_game_launch_observation
  假设主线58条观察已采认
  当追加普通图标启动观察
  那么原58对象完全相等，新条只有启动失败证据而无游戏亮屏或API冻结声明
场景: 渲染引用可复核
  测试: commercial_game_launch_observation
  假设normal-ui-01和旧REA已在主线
  当渲染并核SHA
  那么59条HTML/CSV一致，缺引用或改原58对象拒绝，G15前缀checker仍通过
## 排除范围
修复实现、部署、G16未交报告的结论及游戏可玩验收。
