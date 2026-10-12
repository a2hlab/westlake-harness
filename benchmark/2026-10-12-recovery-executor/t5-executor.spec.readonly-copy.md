spec: task
name: "Concrete recovery placement and autonomous executor"
inherits: project
depends: [t4-integration]
---

## 意图

把已交的真实启动链变成可由外环执行的新封板候选，闭合截图格式、控制件部署、启动槽和回滚。复用既有 driver/provider，避免继续只交 pending 清单而无执行路径。

## 已定决策

- 写独立包，引用 e5763d36 集成和 9763171a 控制件，不改两份历史字节；确有缺陷需要改候选时，新文件、新 SHA、独立回归，旧证据不借用。
- 先本地查实际 snapshot_display 与 screen-gate 的源码/导入/格式实现，选最小兼容修正；不能仅把 AUTH 格式字段置 yes。ARM 执行由外环提供现场窗口，内环本阶段只离线实现和测试。
- 默认 preview 零设备调用。执行器只有完整 serial/boot/expiry/plan/member/preimage 绑定及显式执行才可调用白名单设备；未知元数据或失败即停止，不自动回滚到危险旧 watchdog。
- 复用 PLACE-ONLY 自启路径，不运行会删除 live bind 底座的 installer，不重跑清 stop/轮换数据的旧 overlay。每版一次重启，重启前快照与 sepolicy 门，重启后独立新证据。
- 部署窗口的 boot/expiry 授权与封板后不可变自启配置分离；正常拔电重开不依赖 Mac 生成票据，运行时使用每次真实 boot/UID/WID/进程身份，不沿用今天的 PID 或窗口 ID。

## 边界

### 允许修改
- benchmark/2026-10-12-recovery-executor/**
- tools/spec-checks/tests/recovery_executor.rs

## 验收标准

场景: 完整绑定输出精确部署和恢复操作
  测试: recovery_executor_plan
  假设 集成文件和逐目标 preimage 已钉 SHA 与元数据
  当 用隔离设备录制器执行新部署候选
  那么 先备份再写控制件并逐件读回，保留旧 stop 与用户数据，默认 preview 零设备调用

场景: 错误身份或缺备份拒绝执行
  测试: recovery_executor_reject
  假设 serial boot expiry SHA 或一个 preimage 不满足计划
  当 显式执行或请求回滚
  那么 非零退出并且零未授权设备写，不签 UI 或 seal，不控制主 appspawn-x

场景: 格式和启动链失败不可伪报成功
  测试: recovery_executor_format
  假设 使用实际截图格式实现证据和真实入口脚本
  当 测试兼容格式与损坏图片以及启动准备失败
  那么 兼容图片被真实解码路径识别，坏图与准备失败非零且不报告 READY，必要权限与启动触发器逐件列入新 placement

场景: 已批准自启配置跨开机仍独立有效
  测试: recovery_executor_autoboot
  假设 已批准不可变自启配置且部署窗口票据已经过期
  当 隔离执行两次不同 boot 和不同窗口 ID 的实际启动脚本
  那么 两次均从当次身份建立守卫且不读取 Mac 新票据，错误成员 SHA 或当前控制 stop 则拒绝启动，不清历史 stop

## 排除范围

- 内环真实板/VM/远端访问，实际授权签名、重启、上板和推送；实际操作由外环另行审查执行。
