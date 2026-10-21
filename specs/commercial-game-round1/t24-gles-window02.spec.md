spec: task
name: "G24 actual GLES loader trial after verified transport recovery"
inherits: project
depends: [t21-gles-bounded-window, t23-shell-heredoc-status]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
在 G21 window01 已完整恢复并解锁、G23 修复已实际恢复成功的基础上，内环执行新一次有界原神普通图标验证，外环独立检查截图及恢复结果。验证现有 GLES 可见性候选是否移走已观察的装载失败。
## 已定决策
- 仅5ea34a4500000000000000001123012c。复用主树原 scripts/lab/u7_executor.py、原 bms_batch 普通桌面入口和现有 g21-rollout-01 精确包；不写新的部署或首启编排器。
- 主树必须含226d658b04传输修复与已采认G22启动上下文；不修改源码、游戏、标签配方、门禁、冻结项或已保存包。原生候选仍878c7019，基线仍b8be63d2，逻辑变化仅两个别名。
- 外环作本窗口新的精确例外决定，不继承已撤销的window01例外。内环先跑原全套dry-run，deployable=true才通知外环核验；外环明确GO后取新锁并执行，全部记录用新目录，旧journal不复用。
- 写前及持锁后核实际boot、服务配置、唯一系统parent的exe/birth、BMS UID、完整进程表和原电源；原U7全量基线检查保持。已安装原神UID由fresh BMS确认，不读environ，不跨板。
- 从新锁取得起最多1800秒，1200秒前开始恢复，最晚900秒停止新增观察。若apply失败只跟踪原自动回滚并恢复，不在同窗重新apply。
- 候选active_verified后保存控制应用截图，使用已存在的普通桌面UI入口点击原神一次；记录启动日志、截图、boot/PID/birth和可获得的maps。不得下载游戏资源、登录、改APK、hook或注入。遇明确拒绝不换方法重试。
- 观察后按fresh BMS UID/完整进程身份用既有正常停止流程收掉测试child，再用原journal原rollback；核319基线及mount栈、Boat3私有SHA、控制实图及原电源，解锁。候选不永久保留。
- 以实际截图和首个终止错误判结果；没有错误不等于图像成功、控制图不等于原神成功。外环判断，内环不得替代签字。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/gles-window02/**
- benchmark/2026-10-21-commercial-game/gles-outer-native-admission/window02/**
- 私有持久执行证据目录
- knowledge/gates/native-predeploy-exceptions.json（仅外环本窗审签及撤销）
### 禁止
- 不改运行时源码、工具、游戏代码或保护行为，不处理G14/T38被拒编排，不操作61b/5cd，不永久留候选。
## 验收标准
场景: 新窗口精确准入和原事务生效
  测试: u7_executor
  审核: human
  假设完整dry-run和外环本窗核准均通过
  当内环fresh核身份并持新锁执行原apply
  那么原journal证明完整候选哈希和启动验证，不绕过任何身份或标签失败
场景: 普通桌面原神启动有直接证据
  测试: u7_executor
  审核: human
  假设候选active_verified且未达观察时限
  当正常点击原神图标一次并采图及启动日志
  那么按实际画面和终止错误记录结果，缺失或白黑屏保留为失败或unknown，不称可玩
场景: 所有结果均同窗恢复
  测试: u7_executor
  审核: human
  假设实验成功或中途失败
  当使用原journal原rollback完成恢复
  那么319目标、原挂载、Boat3私有库、控制实图、电源及锁释放均有证据，窗口在1800秒内关闭
## 排除范围
头条部署、永久封板、原神资源下载或登录、新公共API修复、整包重扫及重复REA。
