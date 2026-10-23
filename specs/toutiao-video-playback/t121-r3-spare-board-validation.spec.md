spec: task
name: "T121 immutable r3 spare-board ordinary reboot validation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t120-qualified-r3-board-package]
---
## 意图
在5cd单板验证已批准r3固定实现配上实际目标配置是否恢复普通图标启动；61b保持现状。复用已批准版本，不修改随机崩溃相关实现。
## 已定决策
- 先Codex离线准备、peer核包、外环技术复验，再由CC唯一设备执行。用户已授权部署和软件重启，无需再求用户批准。准备阶段不设备调用，执行须外环明确确认具体包SHA与计划。
- T120禁用包和原始构建记录保持原样。离线另建promotion目录，固定17实现件SHA全部不变；仅startup.env的ENABLED=1/APPROVED_BY=outer(codex)及对应expected摘要派生，记录父包hash、外部证据和完整差异。不能调用旧T71/T74/T91停止流程或修改审批设置。
- init以T116当前5cd原始配置为输入，必须匹配19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152；仅把唯一westlake-u13-toutiao-overlay服务boot-entry路径换成T120 ROOT，其余结构和属性不变，原字节为精确回滚前像。禁止安装生成payload/recovery.cfg。
- 发布可逐字执行且对象白名单的计划、payload逐件SHA/mode、init前后diff和回滚命令；禁止默认联网/后台无界任务/额外改系统配置。对promotion允许差异和init仅单argv变更做离线断言测试，原始生成日志持久保存。路径必须普通文件、无符号链接/路径穿越。
- 设备阶段先只读held/boot/当前init/原ROOT关键SHA/网络及宿主身份；任一身份偏离交件立即停止交外环，不按过期前像写。持有5cd锁，总窗15分钟，保留3分钟回滚预算，新ROOT必须不存在或与已批准候选完整一致。
- 部署只新ROOT和精确init变更，旧ROOT所有文件保留。核部署实际SHA/mode后一次普通软件reboot，等新boot/网络/桌面就绪；凭新截图或layout定位头条，执行一次普通图标点击，不用命令直接启动头条。
- 点击后按10/30/60/90/120秒实际采图、进程身份与普通状态，截图是地面真相。若进入信息流，Home后普通点击回到应用再采10/30；若自然退出后可再次点击，另记录恢复现象但不人工制造崩溃。不以存活或READY替代截图，不把120秒上限说成可接受速度。
- 无feed/异常/预算耗尽：按已审回滚恢复原init精确SHA、软件重启回原ROOT，核稳定与恢复电源超时并释锁；不自动重复部署试验。本次实验无论截图是否亮都在采集后恢复原init并软件重启回原ROOT，取消人工等待及feed保留分支；先交证据由外环判定，后续正式保留另作具体技术决定，不能自行写封板或宣称多次冷启动可靠。
## 边界
### 允许修改
- benchmark/2026-10-23-r3-spare-board-validation/**
- 私有 $HOME/.local/share/westlake/r3-spare-board-validation-20261023/**
- 仅授权执行阶段5cd新ROOT及精确init配置与恢复
### 禁止
- 61b/5ea写、修改固定运行时实现、随机崩溃预防或退出归因、强制崩溃、旧停止流程
## 验收标准
场景: 离线具体包可审核
  审核: human
  测试: r3_spare_board_validation_review
  假设T120包独立复验通过且固定实现SHA未变
  当派生promotion和单argv init配置
  那么给精确字节差异、原始日志、白名单命令和回滚，未执行设备阶段
场景: 普通图标首启
  审核: human
  测试: r3_spare_board_validation_review
  假设具体包经外环复验且fresh板身份符合
  当CC有锁部署软件重启后普通点击
  那么按实际截图记录信息流或白屏及真实耗时，不以脚本状态宣布成功
场景: 失败恢复
  审核: human
  测试: r3_spare_board_validation_review
  假设身份偏离、未亮或窗口超限
  当停止实验
  那么保留原件并恢复精确原init和原ROOT启动状态，释锁且失败不隐藏
## 排除范围
物理断电证明、全面封板、修改随机崩溃机制、新运行时实现。
