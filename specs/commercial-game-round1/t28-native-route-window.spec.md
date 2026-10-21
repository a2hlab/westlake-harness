spec: task
name: "G28 bounded native-route trial on 5ea"
inherits: project
depends: [t26-native-route-candidate, t27-native-route-package, t24-gles-window02]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
使用已实际编译并独立复验的公共兼容候选，验证原神是否越过G24实报atfork装载错误。复用原U7事务及普通桌面入口，保留截图、首个终止点和同窗恢复证据，不把离线通过当游戏可玩。
## 已定决策
- 仅5ea34a4500000000000000001123012c；原神APK与数据不改。host候选ee5649f2778430e1c997f4bb2d4d4f42f53a46208b4a1b1bbaca185ddf401887、ANL候选640b3c87e2f0f86d31b7defbd8b892515636afa61dcbbab5030d422ec1fb7d86；保留G24已验policy878c7019。基线仍host2a871、ANLeebd、policyb8be。
- 原G27包逻辑变更5目标（host1、ANL2、policy2）；实际35写入项中30同SHA。完整319基线和Boat3私有库保持恢复依据，旧74e6路由不改。所有实际manifest与SHA必须先独立复核，不把本契约数字代替机器清单。
- G26全部源/补丁/配方/工具链与实际构建日志须先持久化并入库索引；两基线精确重建及候选真实函数回归已通过，但OH回调测试替身不替代设备。候选全套原preflight必须实际执行，未通过不取得写窗口。
- 外环逐项评审当前原native检查的N1/N2及其他拒绝；只可对有精确对象/SHA/理由/证据的本窗既有容许项签认（按RUNBOOK 2026-10-13旧协议approved_by填outer(claude)，actual_reviewer明确outer(codex)，不冒称Claude模型审核），不沿用撤销的G24窗口签名、不放宽门禁、不略过新发现阻断。无合格准入则留离线包并停止写操作。
- 仅用主树原u7_executor.py apply/rollback及既有bms_batch普通图标入口，不创建部署/首启编排器，不重做G14/T38。内环可准备离线材料，实际执行唯一owner由外环明确；同一块板不得并发写。
- 写前与持锁后核fresh boot/串号、父进程exe/birth、完整基线、BMS UID、mount栈与原电源；使用新journal和本窗锁。最大1800秒，900秒停止新增观察，1200秒前开始恢复；失败仅跟踪原自动恢复，不在本窗重复apply。
- apply active_verified后先看控制应用实图；仅普通图标点击原神一次，保存截图、boot/PID/birth、本次有界hilog及可取得的实际maps。既有三项符号不再报错只算过墙；白黑屏、退出或缺图仍失败/unknown。遇登录/资源下载页仅记录，不登录下载，不hook/注入或绕保护。
- 按fresh UID/完整进程身份用既有停止流程清测试child，原journal原rollback；独立核319文件直接/parent视图、mount、Boat3、控制实图、原电源和锁释放。候选不永久留存；本窗例外恢复后撤销，保留所有原始失败与签认。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/native-route-window/**
- benchmark/2026-10-21-commercial-game/native-route-admission/**
- knowledge/gates/native-predeploy-exceptions.json（仅外环本窗精确签认及撤销）
- 私有持久证据目录及独立本窗rollout包
### 禁止
- 不修改运行时源码、现有部署器/门禁/冻结行为或游戏；不触61b/5cd，不重试G14/T38被拒操作，不永久留候选。
## 验收标准
场景: 精确准入后原事务生效
  测试: u7_executor
  审核: human
  假设本窗实际preflight和精确签认通过
  当唯一执行者核fresh身份持锁运行原apply
  那么原journal证明完整候选及35项计划执行结果，不绕过身份或标签失败
场景: 未准入或身份漂移拒绝
  测试: u7_executor
  假设任一输入哈希、签认、boot或父进程身份不匹配
  当原事务核验
  那么拒绝继续写入，已写部分按原journal恢复，不篡改原失败或增加盲重试
场景: 过墙与真实页面分别判断
  测试: u7_executor
  审核: human
  假设候选active_verified且控制图已查看
  当普通点击原神图标一次并采图和日志
  那么分别记录atfork及FD符号结果、首个实际终止点和真实画面，无游戏帧不得称游戏可用
场景: 所有结果同窗恢复
  测试: u7_executor
  审核: human
  假设试验成功或中途失败
  当原rollback完成并独立复核
  那么完整319基线、挂载、Boat3、控制图、电源、锁与临时例外撤销有证据且1800秒内闭窗
## 排除范围
头条部署、游戏资源下载或登录、游戏保护修改、新公共API实现、永久封板与多板发布。
