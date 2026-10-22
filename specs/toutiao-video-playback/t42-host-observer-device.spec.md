spec: task
name: "T42 observe ordinary lifecycle requests in the owned host application"
inherits: project
depends: [t41-host-observer-package]
satisfies: [REQ-TTVIDEO]
---
## 意图
把已独立验收的 T41 被动观察宿主应用在 5cd 做一次正规同签名更新，取得真实启动请求与回调记录，随后恢复当前 b189 宿主。此实验只回答记录是否在真实设备产生以及普通启动请求对应哪些回调，不认定头条白屏已修复。
## 已定决策
- 只使用 5cd1e3dd00000000000000000923012c。T41 最终包、源码、工具、验签与逐成员证据须先由外环采认；候选 SHA 从该最终交件固定，不从变动中的目录选包。
- 先只读取得当前 boot ID、bm dump 宿主身份、实际 HAP 路径与 SHA、实际 filesDir、原有两个观察文件状态及运行时指纹；当前 HAP 必须为 b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0。锁前与写前复核对象，保留同一 b189 恢复包；不可使用旧 T32 的 df385 回退目标或旧 context/holder。
- 按现成正规 bm install -r -p 语义更新自有 org.westlake.imehost 应用，不卸载、不清数据。保留原始传输、远端返回码、安装正文及安装后 HAP 哈希；身份、证书、权限、数据目录身份和运行时指纹必须前后一致。
- 最多发出三次明确记为 automated_request 的普通 aa start 宿主启动请求并逐次采证。本窗不点击、不滑屏、不唤醒或修改电源设置，不调用旧 desktop_launch/capture 整体 helper；仅用原始 snapshot_display 截图。不把自动请求称为人工点击，不把 onNewWant 当作必然发生；缺回调/文件未更新也原样记录。逐次保存 launch-observation.json 与独立 window-state.json，不能以最终单文件代替历史。
- 候选记录 manual_origin 必须为 unverified、eligible_for_reentry 必须为 false。截图用 snapshot_display，核接收前后 SHA 并目读；截图不替代回调证据，回调不替代亮屏证据。不询问用户重复听声音。
- 不编写或运行新的设备编排器；执行现成普通应用管理及观察命令，逐命令保存原始 argv、时间、stdout、stderr、真实返回码到持久目录。保留失败，不修改权限或换通道重试被拒操作。
- 实验最多20分钟，另留10分钟恢复。结束恢复 b189 并复核实际 HAP、身份、指纹与数据目录身份，以及候选宿主 PID/birth 已退出，然后释放本轮独占锁。不能只凭磁盘HAP恢复就认定运行中候选已退出；无法确认则报告恢复未确认，不据此操作guardian或第三方。不能把历史回退脚本存在说成历史回退实跑过。
- 安装超时、断连或远端rc缺失均为结果unknown，不能当作未更新。先只读核实际HAP及bundle身份，只有身份和状态明确后才按本轮依据恢复；身份无法确认时停止写入，保留证据并报告，不能盲目重复安装。
- 现有环境可能自行响应宿主窗口；观察其现象，不修改、启动、停止或编排 guardian/运行时/第三方进程。此卡不是 T38 运行时编排或任何已停止内容的重试。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-host-observer-device/**
- tools/spec-checks/tests/toutiao_host_observer_device.rs
### 禁止
- 不修改冻结项、T32/T39/T40/T41原件、宿主源码、运行时配置、guardian状态、第三方应用、其他设备或权限；不调试第三方、不使用REA、不重启、不commit、不push。内环交路径与SHA，外环合入。
## 验收标准
场景: 真实宿主观察并恢复
  审核: human
  测试: toutiao_host_observer_device
  假设最终候选已采认、5cd身份符合基座且本轮持有独占锁
  当正规更新后执行至多三次普通启动请求并逐次采证再恢复
  那么逐命令原始argv、时间、stdout、stderr和远端rc可核SHA，最多三次请求均为automated_request；候选与恢复后的HAP哈希准确、身份指纹及数据目录身份不变、候选PID/birth已退出，截图经目读，结果只报告实际回调与画面且不宣称白屏修复
场景: 身份不符或操作失败
  测试: toutiao_host_observer_device
  假设候选未采认、基座不符、锁冲突、安装失败或证据缺失
  当执行本轮准入或检查回执
  那么停止后续实验并保留明确失败；安装结果unknown时先只读确认实际HAP及身份、不盲重装，已确认更新时按本轮b189恢复依据恢复，不把shell进程rc0单独当成功
场景: 回调缺失或恢复未证实
  测试: toutiao_host_observer_device
  假设请求后没有新回调、记录无效或恢复哈希未确认
  当汇总实验
  那么缺回调记为observed_absent或unknown且不伪造事件，恢复未确认不得签认关闭；被动回执检查器不执行设备命令
## 排除范围
第三方崩溃诊断、重入策略修复、自动拉起、视频音频再次验收、原神、61b部署与封板。
