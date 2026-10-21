spec: task
name: "G29 append native-route source and build observation"
inherits: project
depends: [t25-loader-observation-update, t26-native-route-candidate]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
将G26已实际构建的公共兼容候选纳入正式API全表，让源码、补丁、配方、工具链、原始日志与适用范围对应可查。明确仅离线候选，保留原神仍未成功的实际状态。
## 已定决策
- 以master83d1a6e07ce8899b241628111e4e4f14112da115的60条观察为严格不可变前缀，追加第61条G26。历史315、原README前文、renderer和既有失败结论保持不变。
- 源与构建证据只引用已主线native-route-candidate及native-route-build-archive：两个精确baseline、hostee5649/ANL640b候选、8条compile/link rc0、每版本ANL37/host50实际生产函数回归但OH回调为替身、导出与NEEDED保持。不得称全源清洁重编；host复用对象的源边界明确。
- 描述精确原神双selector与本域mediandk共享列表、复用d205公共ABI三导入覆盖及atfork DSO-unload限制；不是游戏修改、不是API冻结。实际OH provider赢家、游戏帧、音视频、可玩均未由G26验证，candidate_currently_deployed=false。
- 对照源码文件和patch、两个可执行构建入口及精确编译器/链接器哈希、主线持久archive回执。G26 README原来local-only是交件时刻声明，另列后来outer远端SHA验证e58740f5，不能篡改原README或manifest。
- 用原render.py生成HTML/CSV/results。G25旧checker改为严格原60前缀允许后续追加，保留G24失败语义及原反例；G15/G17约束不减。新checker必须精确61、每条引用SHA与原renderer生成bytes相等，并拒绝HTML-only假成功、截断、追加第62条、历史漂移、假部署/冻结/游戏可玩、丢证据。
- 内环独立树交path-only清单，外环复验合入推送。禁止运行时编译；Rust selector和离线验收可执行。不设备、不REA、不运行G14/T38被拒步骤。
## 边界
### 允许修改
- benchmark/2026-10-19-api-progress-update/observations.json
- benchmark/2026-10-19-api-progress-update/observations.csv
- benchmark/2026-10-19-api-progress-update/index.html
- benchmark/2026-10-19-api-progress-update/results.json
- benchmark/2026-10-19-api-progress-update/README.md
- benchmark/2026-10-21-g24-api-observation/check_observation.py
- benchmark/2026-10-21-g24-api-observation/SHA256SUMS
- benchmark/2026-10-21-g26-api-observation/**
- tools/spec-checks/tests/commercial_game_g26_observation.rs
### 禁止
- 不改renderer、原60条、历史315、冻结登记、运行时代码或G26原包，不设备、不REA、不push。
## 验收标准
场景: 源码构建对应离线事实
  测试: commercial_game_g26_observation
  假设G26固定源码及远端构建归档已主线
  当追加第61条并调用原renderer
  那么JSON及HTML和CSV字节对应，源码配方工具链与原始日志SHA引用可核，明确离线和非当前部署
场景: 历史与假成功拒绝
  测试: commercial_game_g26_observation
  假设前60条不可变且G26未有游戏运行证据
  当篡改前缀或仅改HTML称成功、增加第62条、丢引用、称冻结或当前部署或游戏可玩
  那么checker逐项拒绝，原G15/G17/G25前缀核验有效，不削弱历史失败语义
## 排除范围
新运行时实现、上板验收、头条部署、游戏成功与API冻结。
