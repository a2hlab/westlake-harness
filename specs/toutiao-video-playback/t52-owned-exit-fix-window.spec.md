spec: task
name: "T52 bounded normal-boot validation of accepted owned recovery fix"
inherits: project
depends: [t51-owned-exit-fix-package]
satisfies: [REQ-TTVIDEO]
---
## 意图
在5cd以正常开机链验证T50自有恢复修复候选，核对实际部署副本及退出分类事件，然后恢复原控制文件。复用T48已执行的维护隔离流程，实测与离线结果分开；这不是T38流程重试，也不诊断第三方为何退出。
## 已定决策
- 先做只读fresh准入与计划准备；只有T51包经外环独立采认并绑定完整SHA及本窗新签认，才可写设备。使用T51六文件候选及六前像，正常启用/维护禁用env与expected由实际成员表派生，分别列文件SHA与内容SHA；不沿用旧boot/stage/backup/signature。
- 只读准入核白名单5cd实际serial/boot/锁、九控制与十三成员、ready设置cfg/script、宿主HAP/UID、runtime124/boot36、目录身份、原电源及六文件mode/owner/SELinux标签。源码到实际运行boot副本逐件绑定；传输rc0不能覆盖正文报错。任何拒绝如实停止，不换端口或路径绕行。
- 写窗保持T48正常禁用→重启维护态→正文替换→完整启用链→正常重启；回滚正常禁用→重启隔离→六前像恢复→正常重启。每次先核ready来源、该boot目录不存在、无本ROOT进程。保留全部stop/旧boot/审计/锁/数据；不用信号、手工启动guardian或清锁取得隔离。
- 每个写命令与重启前单独检查持锁人、当前阶段boot、剩余时间、父目录身份及标签；guard不能放在无pipefail的管道里。只用全新stage/backup和替换临时名，拒绝既存/符号链接，写后读回完整SHA/mode/owner/label。每条原始argv/start/end/stdout/stderr/rc持久保存。
- 窗口最多1800秒，1200秒开始恢复，每次重启最多180秒。候选正常桌面定位后只点一次图标，观察最多180秒，采实际截图、自然出现的恢复/拒绝事件；不诱发崩溃、不杀进程、不声明未发生的退出分类。无退出则记未触发。预算不足立即进入既定回滚，不反复尝试。
- 恢复后核六文件和十三成员、runtime/boot/宿主/目录/电源及残留临时对象，记录实际新inode，恢复态正常图标启动观察后解锁。保留stage/backup需列身份及原因。截图白屏则明确白屏仍存在，事件RECOVERING不等于画面恢复。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-owned-exit-fix-window/**
- tools/spec-checks/tests/toutiao_owned_exit_fix_window.rs
### 禁止
- 未采认具体计划的设备写、其他板写、T38流程或测试、已拒绝调试路径、REA、第三方崩溃诊断、修改init/ready/权限或额外身份门、手工guardian启动、终止第三方进程、删除旧对象或放宽门禁；不commit/push。
## 验收标准
场景: 只读准备不提前激活
  测试: toutiao_owned_exit_fix_window
  假设包未获最终采认或设备fresh准入有漂移
  当执行准备与计划审核
  那么保留准入原始记录并标具体缺口，没有设备写、候选激活或沿用历史签认
场景: 正常窗口与恢复都有原始证据
  审核: human
  测试: toutiao_owned_exit_fix_window
  假设新签认计划与fresh准入全部符合
  当实际执行四次正常重启的候选验证与恢复
  那么回执绑定每阶段boot/实际副本SHA/原始日志，截图与事件分别判定，六前像和约定metadata恢复并按时解锁
场景: 缺证据或guard失败不能完成
  测试: toutiao_owned_exit_fix_window
  假设缺原始恢复回执或guard不成立或截图仍白
  当执行回执核验
  那么缺失证据非零拒绝完成，guard失败不执行后续写，白屏不得标修复或封板通过
## 排除范围
主动触发第三方退出、原因诊断、人工关闭重开最终验收、其他设备推广、原神和封板签认。先得到这个正常启动窗口的实际证据再决定下一步。
