spec: task
name: "T58 current61b boot-first-use demo scope"
inherits: project
depends: [t55-61b-demo-current-state]
satisfies: [REQ-TTVIDEO]
---
## 意图
用户明确把演示验收收窄为开机后直接从桌面打开头条、看到信息流并点进内容操作，取消关闭进程后重开的验收条件。先验证当前已留板启动链，其他Android演示APK做有界抽验，不承诺全部115个通过。
## 已定决策
- 仅61b0657200000000000000000324012c；T57已释锁后fresh只读核boot、cfg/ROOT、宿主HAP、guardian、实际power前像、当前锁及无遗留远端hash任务。与T55/T57前像核对；漂移先交外环。此轮不换制品，不把未核全runtime说一致。
- 新board_note独占锁下通过标准HDC reboot执行一次正常软件重启。记录前后boot不同，等待系统就绪；不运行任何手工bootstrap/start/guardian/aa命令。此轮是normal_reboot，physical_power_cycle和真人触屏仍未验证，不伪称断电测试。
- 重启后用已验普通UI唤醒、无密码解锁、Home及当前layout定位图标，不使用旧坐标。头条第一次点击最多观察120秒，30/120秒截图及现有state/events；信息流可见才点一个当前可识别内容、返回并滚动一次，逐步读图确认。白屏或无可操作内容则记录失败并停止头条动作，不追加重开，不研究随机崩溃。
- 如时间允许，正常Home进入已安装Android OpenCalc(com.darkempire78.opencalculator)和2048(org.secuso.privacyfriendly2048)各一次，先核历史清单/当前图标身份；每个最多60秒。OpenCalc可输入1+1验证结果2，2048可普通滑动一步观察棋盘变化；不碰原生com.ohos.calculator，不操作个人数据。不因头条失败跳过独立样本，不把2个样本泛化到115个。
- 同板动作串行，所有UITest副作用记录；窗口20分钟停止实验，留10分钟恢复实际power前像并核读回，释锁后写报告。任何拒绝、密码/权限提示、身份不明即停止该操作，不更换入口绕过。启动失败不部署/回滚猜测版本，不杀进程不清数据。
- 原始argv/start/end/stdout/stderr/rc、截图SHA和包名持久保存；报告每个APK的启动/内容/操作三个独立结果，另列manual_touch=unverified。复用既有普通命令，不新增编排工具或镜像测试；人工回执选择器未实现，不报lifecycle PASS。
- 外环准入addendum：T58 fresh读取发现T55自有只读全树hash残留shell27497/27501，精确argv与原runtime_sha回执对应；原“已无残留”判断撤回。允许把这两个已识别的只读任务作为明确例外，由本卡原定标准reboot结束；不发进程信号，不重放扫描，保留初次准入拒绝原件。重启后必须核新boot且无该采集作业，再做任何UI测量；这不豁免其他未知工作或锁。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-boot-first-use/**
- 私有$HOME/.local/share/westlake/61b-boot-first-use-20261023/**
- 持锁下61b一次标准软件重启、正常UI/截图及power前像恢复
### 禁止
- 源码/运行时/HAP/权限/冻结项/应用数据修改、手动后台启动、信号/force-stop、关闭重开实验、随机崩溃诊断、T38、REA、environ/FD2、其他板；不提交推送。
## 验收标准
场景: 重启后首次图标使用
  审核: human
  测试: existing_61b_boot_first_use_receipts
  假设fresh身份完整且本轮持锁
  当正常重启后只经当前桌面图标进入头条并在有内容时点进返回滚动
  那么逐步保存实际画面与启动状态，明确没有手工后台启动，分别报告启动和操作，按实际power前像恢复并释锁
场景: 启动失败或身份与操作被拒
  审核: human
  测试: existing_61b_boot_first_use_receipts
  假设首屏仍白屏、身份不符或操作被拒绝
  当达到停止条件
  那么保留原始失败并停止对应操作，不改权限、不重开刷成功、不猜版本部署，缺证据写unknown
场景: 其他APK独立抽验
  审核: human
  测试: existing_61b_boot_first_use_receipts
  假设OpenCalc和2048当前图标可确认且窗口有余量
  当分别从桌面启动并做一次无个人数据操作
  那么按包名记录内容与操作结果，不把OH原生应用或115个历史首屏当本次Android抽验通过
## 排除范围
关闭进程重开、随机崩溃、全量115复验、物理断电、原神和部署修复。
