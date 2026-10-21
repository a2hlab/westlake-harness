spec: task
name: "G35 record the bounded locale trial in the API table"
inherits: project
depends: [t33-locale-api-observation, t34-locale-runtime-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
把G34实际过墙、失败画面和恢复证据接入API全表，让源码、构建及真机结果可对照，不将locale错误消失当成原神成功。
## 已定决策
- 以主线86b9fdb1600bdeb15eb7dc74f77a8f7b306b8ced的63条为逐对象不可变前缀，仅追加第64条。历史315与renderer不改，README只追加。
- 输入使用外环采认并已合入的locale-runtime-window/closed、admission-01、g34-launch-addendum、g34-static-prediction及真实远端归档回执。保留G30源码/配方对应关系，不复制运行时实现。
- 明确原事务apply/rollback rc0、36恢复、319双视图/挂载/Boat3/控制图/电源/实际解锁核实。318临时例外已撤销，候选不再部署。清理force-stop正文错误与后续UID清空分列，不将外层rc0当内部动作成功。
- 原神仅一次实际图标点击；首次helper缺远端目录在点击前失败。child29761于23:22:11.437被父进程报告signal11；两张截图白屏到桌面、无游戏帧。locale旧加载错误未见，仅表示本次推进；PC、栈、故障根因和动态provider winner仍unknown，不冻结、不称可玩、不满足2app。
- Dfx原-x和-z组合查询正文CODE-31无效；闭窗后单模式查询为空；完整缓冲采样超时且未覆盖崩溃时段，不能据此说无崩溃记录。前63条的当时未部署/归档待核声明保持历史原意，不随新证据覆写。
- 原renderer生成HTML/CSV/results。G33检查器改严格63前缀允许追加而保留历史语义；新检查器核64条及引用SHA。拒绝历史漂移、截断63、追加65、缺引用、SHA漂移、仅HTML/CSV伪成功、当前部署/冻结/游戏帧/根因已知的伪声明。
- 仅离线表格、文档、检查器与Rust入口；交固定path-only清单和实际测试回执。不上板、不REA、不运行时构建、不触G14/T38、不push。
## 边界
### 允许修改
- benchmark/2026-10-19-api-progress-update/observations.json
- benchmark/2026-10-19-api-progress-update/observations.csv
- benchmark/2026-10-19-api-progress-update/index.html
- benchmark/2026-10-19-api-progress-update/results.json
- benchmark/2026-10-19-api-progress-update/README.md
- benchmark/2026-10-21-g30-api-observation/check_observation.py
- benchmark/2026-10-21-g30-api-observation/SHA256SUMS
- benchmark/2026-10-21-g34-api-observation/**
- tools/spec-checks/tests/commercial_game_g34_observation.rs
### 禁止
- 不改前63对象/历史315、renderer、输入原件、运行时、冻结登记、门禁、主树或设备。
## 验收标准
场景: 第64条串联源码构建实机失败与恢复
  测试: commercial_game_g34_observation
  假设G34固定输入与归档回执已经外环采认并合入主线
  当追加观测并运行原renderer
  那么引用哈希可核且三种输出一致，保留signal11无游戏帧及恢复后未部署状态
场景: 伪成功与证据缺失拒绝
  测试: commercial_game_g34_observation
  假设本轮无游戏帧或PC栈证据
  当伪造成功、当前部署、冻结、已知根因或删除和篡改引用
  那么逐项拒绝，不以截图数和rc0替代真实画面与日志正文
场景: 历史与呈现篡改拒绝
  测试: commercial_game_g34_observation
  假设前63条是固定历史前缀
  当篡改历史、截断63、追加65或单独修改HTML和CSV
  那么逐项拒绝且旧检查仍通过，不把后来真实归档作为历史声明错误
## 排除范围
头条部署、新运行时修复、崩溃根因断言、游戏成功与API冻结。
