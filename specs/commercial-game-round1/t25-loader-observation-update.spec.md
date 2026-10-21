spec: task
name: "G25 append actual loader trial without upgrading game status"
inherits: project
depends: [t17-launch-observation-update, t24-gles-window02]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
将G24真实候选部署、游戏失败与恢复结果接入正式API观察表，并让读者找到候选源码、构建配方和原始日志。
## 已定决策
- 以master b2d14677a6757dbbee3797d17bfc17f2762d0ddd的59条观察为不可变前缀，追加一条G24观察；历史315行、已有README原文、renderer及旧验收结果保留。
- 只采已在主线的gles-loader-candidate、gles-window02/launch-review-01和closed证据。明确原apply/rollback rc0、普通图标白屏后桌面/exit1、未见游戏帧；GLESv2依赖错误未见而出现__register_atfork不等于GLES功能或游戏可用。原__errno/Unity JNI仍存在，游戏child maps未采到。
- 条目链接精确源码、配方、工具链与原始build归档及G24执行归档；当前设备为已恢复基线，候选不标当前部署。不得新增公共API冻结、2app验证或原神可玩声明。
- 使用原render.py生成JSON对应HTML/CSV/results。将G17 checker改成严格核验原59前缀，允许后续追加；G15原58前缀约束保持。新checker核60条、引用SHA、渲染一致性及历史不可变，负例拒绝漂移和假成功。
- 内环独立worktree交path-only清单；外环复验后采认推送。原始大日志不复制入git，引用已验证远端归档。
## 边界
### 允许修改
- benchmark/2026-10-19-api-progress-update/observations.json
- benchmark/2026-10-19-api-progress-update/observations.csv
- benchmark/2026-10-19-api-progress-update/index.html
- benchmark/2026-10-19-api-progress-update/results.json
- benchmark/2026-10-19-api-progress-update/README.md
- benchmark/2026-10-21-launch-observation-update/check_observation.py
- benchmark/2026-10-21-launch-observation-update/SHA256SUMS
- benchmark/2026-10-21-g24-api-observation/**
- tools/spec-checks/tests/commercial_game_g24_observation.rs
### 禁止
- 不改renderer、原59对象、历史315、旧验收结果、冻结项或运行时代码；不设备、不REA、不构建、不执行或重新生成G14/T38被拒步骤，不push。
## 验收标准
场景: 实测及源码构建对照完整
  测试: commercial_game_g24_observation
  假设主线G24已完成候选实测与恢复
  当追加一条观察并运行原renderer
  那么60条JSON和HTML及CSV一致，源码配方与两类原始归档引用SHA均可核，当前部署明确为基线
场景: 历史和失败语义不能漂移
  测试: commercial_game_g24_observation
  假设新条无游戏帧且原59条不可变
  当篡改历史对象或标游戏成功或将候选写成当前部署或破坏引用
  那么checker拒绝每个反例，原G15和G17前缀核验仍有效
## 排除范围
新的运行时修复、静态草稿结论、游戏可玩验收和头条部署。
