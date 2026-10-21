spec: task
name: "G31 append real native-route trial to API progress"
inherits: project
depends: [t29-native-route-api, t28-native-route-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
把G28真实部署、普通图标首启与完整恢复结果接回API全表，区分源码候选、实测过墙和游戏成功。让使用者能沿第62条找到实际源码、构建、运行证据及仍待解决的_ctype_。
## 已定决策
- 以master782b588de8f8d34b70bb343101fd88107973993b的61条观察为严格不变前缀，追加第62条；历史315和原renderer不变，README只追加。
- 仅引用外环已落主线的native-route-window/closed、admission-01、runtime-loader-triage/g28-launch-addendum及G26源码/构建归档。先核这些文件已提交再生成正式行；远端归档状态按实际回执，不猜测。
- 记录原U7 apply/rollback rc0，普通图标一次，child14857白屏到桌面、无游戏帧；_ctype_@LIBC为本轮主库实际首终止，早期MHY __assert2后仍继续。atfork不再报错仅表示报错点推进，不声称实现语义或赢家已证。早maps不能认最终namespace可见性。
- 记录319直接与319父视图、mount/Boat3/控制图和电源恢复，978.404534秒闭窗。候选当前未部署，不冻结，不满足2app，不称游戏可玩。区分闭窗声明与后续held只读回执，不补造原unlock rc原件。
- 原render.py生成HTML/CSV/results；G29 checker升级为严格61前缀允许追加并保留离线候选失败语义；新checker精确62并逐引用核SHA及renderer输出字节。假成功、历史漂移、截断61、追加63、HTML-only假画面、缺引用和SHA漂移必须拒绝。
- 仅离线数据和验收，Rust测试可执行；不设备、不REA、不构建运行时、不运行G14/T38、不push。交固定path-only清单与原始测试结果。
## 边界
### 允许修改
- benchmark/2026-10-19-api-progress-update/observations.json
- benchmark/2026-10-19-api-progress-update/observations.csv
- benchmark/2026-10-19-api-progress-update/index.html
- benchmark/2026-10-19-api-progress-update/results.json
- benchmark/2026-10-19-api-progress-update/README.md
- benchmark/2026-10-21-g26-api-observation/check_observation.py
- benchmark/2026-10-21-g26-api-observation/SHA256SUMS
- benchmark/2026-10-21-g28-api-observation/**
- tools/spec-checks/tests/commercial_game_g28_observation.rs
### 禁止
- 不改renderer、原61对象、历史315、已固定G26/G28证据、运行时与门禁；不设备、不push。
## 验收标准
场景: 第62条对应实际失败与恢复
  测试: commercial_game_g28_observation
  假设G28固定证据已入主线
  当追加第62条并用原renderer生成输出
  那么源码构建与实机证据SHA可查，HTML和CSV与JSON字节对应，明确游戏失败和当前已恢复基线
场景: 假成功或历史篡改拒绝
  测试: commercial_game_g28_observation
  假设原61条不可变且未见游戏帧
  当改历史或仅改HTML称成功、追加63条、截断61条、丢引用或改变SHA
  那么每种反例均失败，G15/G17/G25/G29历史前缀检查仍有效
## 排除范围
新运行时修复、头条部署、游戏成功及API冻结。
