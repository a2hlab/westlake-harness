spec: task
name: "T75 actual power cycle and first desktop launch"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
独立于已停止的T74静态分析，直接验证用户最重要的演示路径：61b真实断电后上电自动恢复，首次普通桌面头条点击显示信息流。物理断供必须有现场确认，不用软件重启或USB掉线代替。
## 已定决策
- 仅61b0657200000000000000000324012c，A阶段只读核板锁、boot_id/uptime、实际power与网络状态，准备既有普通UI采集入口。原始回执落持久目录，不读取凭据、faultlog、内存或T74被拒绝源码，不修改运行时。A阶段完成即报READY_FOR_PHYSICAL_POWER，不锁板等人。
- B阶段仅在外环收到用户现场就绪、确认切断的是整机供电后派发；先独占板锁再通知现场动作。30分钟总窗，20分钟停止实验。外部等待超过10分钟则保留pending、释锁，不擅自reboot。
- 实际掉电和重新供电由用户确认时间/动作，另保留旧新boot_id、uptime和枚举。HDC仅观测及普通UI，不手工bootstrap/部署/start_service/aa启动，不补连WiFi。允许普通唤醒解锁，不清数据。
- 上电后先读boot与网络；自动联网最多观察180秒；READY指设备可用而非应用成功。记录从上电到桌面、网络就绪、图标点击、首张feed的分段时间。若需UI定位用新鲜layout，不套历史坐标。
- 网络就绪后一次桌面图标点击，优先由用户手指并确认点击时间，否则明确标UITest普通UI代点。10/30/60/120秒取实图，首次feed即交外环读图；首次失败保留，禁止再点刷成功。5至10秒是优化目标，超过10秒照实报告，不自动把120秒作为体验达标。
- 出现feed即保留给用户，后续随机退出不作为崩溃修复任务；未出现则保存失败并回桌面。恢复新boot本阶段UI前power实际数值（不得盲用A阶段旧boot值）、读回并释锁。只commit不push；本卡选择器为human回执审核，未实现自动测试不得声明lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-physical-power-first-launch/**
- 私有$HOME/.local/share/westlake/physical-power-first-launch-20261023/**
- B阶段已持锁61b普通唤醒解锁、桌面UI与power恢复
### 禁止
- 电源控制能力未知时自行切断设备、软件重启替代断供、运行时/配置/网络偏好变更、崩溃或被拒绝静态分析、其他板
## 验收标准
场景: 实际断电后首次图标进入信息流
  审核: human
  测试: physical_power_first_launch_receipts_review
  假设现场确认整机断供并重新供电且本轮独占锁成立
  当自动恢复联网后首次普通桌面图标点击
  那么保存新boot绑定的真实feed截图与从点击到feed时间，区分真人输入与UITest，恢复power释锁
场景: 没有真实断供证据或首启失败
  审核: human
  测试: physical_power_first_launch_receipts_review
  假设外部动作未确认、网络180秒未就绪或点击120秒仍没有feed
  当达到对应停止条件
  那么保留pending或失败，不用reboot与再次点击补成功，恢复power释锁并交最小事实
## 排除范围
随机崩溃归因、T74被拒绝分析延续、启动链修改、长时稳定保证、原神与全量APK。
