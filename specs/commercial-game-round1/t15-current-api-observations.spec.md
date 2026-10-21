spec: task
name: "G15 publish current source build and install observations"
inherits: project
depends: [t11-source-api-closeout, t13-installer-device-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
将G11草稿和G13真实安装结果接入现有正式API观察页，用户可从表内找到具体实现、构建和验证范围。保留315行历史语义与现有50条观察，避免只有独立报告而总表缺项。
## 已定决策
- 主线benchmark/2026-10-19-api-progress-update/observations.json是当前观察权威输入；现有50个row对象逐项保持不变，追加G08/G09/G13、T35、T36/T37、T38、G14的有界观察，关联JAVA-042但不把OH安装组件或应用守护称为新增Android公共API。
- G13只采accepted-install-01：原APK安装成功、UID20011077、实际候选加载、原安装器恢复且包保留；游戏未启动，无原神截图、无可玩声明。工具链/配方/原始构建日志/远程归档沿native-build的精确源链引用。
- T35白屏现场、T36/T37离线候选和T38/G14安全停止分别标明；所有相关文件只作为文字/JSON证据读取，不执行或重新生成被拒的测试、编排与参数，不请求别的模型重做。
- 复用原render.py，以精确SHA验证引用后生成HTML/CSV/results。旧315历史表、冻结登记和源实现只读。每条写平台版本证据及unknown边界，当前部署为实际恢复状态，历史候选不能标当前部署。
- 更新README最新数量与新增证据导航；G11草稿作为历史来源保留不改。渲染成功只证明本地表完整，远程发布由外环实际push后另记。
## 边界
### 允许修改
- benchmark/2026-10-19-api-progress-update/observations.json
- benchmark/2026-10-19-api-progress-update/index.html
- benchmark/2026-10-19-api-progress-update/observations.csv
- benchmark/2026-10-19-api-progress-update/results.json
- benchmark/2026-10-19-api-progress-update/README.md
- benchmark/2026-10-21-current-api-observations/**
- tools/spec-checks/tests/commercial_game_current_api_observations.rs
### 禁止
- 不改renderer、历史315行、已有50条对象、冻结项、运行时代码或既有证据；不设备、不REA、不构建、不执行T38/G14被拒步骤，不push。
## 验收标准
场景: 正式表的源码构建与证据链接
  测试: commercial_game_current_api_observations
  假设G11来源及G13安装闭窗证据已在主线
  当追加观察并运行原render.py
  那么HTML/CSV/JSON显示对应实现、配方、日志、验证范围，所有引用SHA匹配，前50对象及315历史表逐字语义保持
场景: 状态不得外推
  测试: commercial_game_current_api_observations
  假设G13仅安装成功而T38和G14未执行
  当检查新增观察
  那么原神未启动和头条修复未实板验证明确，恢复原件与候选区别明确，不称新增API冻结或远程发布已证
场景: 输入漂移拒绝
  测试: commercial_game_current_api_observations
  假设引用缺失或SHA改变或原50对象被修改
  当校验并渲染
  那么拒绝提交结果并报告具体缺项，不用空链接或unknown掩盖可确定源码
## 排除范围
设备首启、头条修复部署、任何被拒步骤重试、原神可玩验收、历史等级重判。
