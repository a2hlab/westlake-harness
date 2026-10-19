spec: task
name: "5cd same-boot existing-parent icon recovery"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t11-5cd-icon-readiness]
tags: [bounded, device, human-review]
---
## 意图
修复T11移除已验证保活前置后，正常图标启动在前台守卫处拒绝的问题。保留5cd现存parent，在全新独立attempt内等待真实桌面到头条图标前台转换，最多生成一个child，为视频验证恢复可观测前提，不诊断随机退出。
## 已定决策
- [platform-specific] 唯一设备5cd1e3dd00000000000000000923012c，boot0525bb05-f714-42ad-90f0-ecdb10356c4f、UID20011300、SceneBoard UID20010017、parent19163/birth7265322必须由只读preflight重核；精确cfg19d0201b与run5a3aef63绑定完整SHA和路径，不套61b入口。未知或变化即拒绝。
- 单锁窗600秒，window-start与holder时间绑定，固定monotonic预算与板uptime截止；预留收尾恢复时间。只允许全新icon-manual-5cd-t12-*控制目录及本窗截图/dumpLayout，旧attempt原件、cfg及runtime/JAR/APK代码不变，应用数据不清理或迁移，保留原JIT准备与应用正常写入，不重启、不清数据、不信号parent或child、不attach/GOT读取。
- tool默认preview零设备调用，preflight显式只读，apply/stop/restore显式execute；每条保存原始命令stdout/stderr/host与remote rc。新目录存在、源pin漂移、错误身份、旧guardian仍活或业务child存在时拒绝apply。
- 临时awake为本任务的明确例外：preflight读power-shell dump -s的Timeout及OverrideTimeout；apply临时-o86400000并只核Override=86400000与Timeout合法，每次普通UI后保持该值；close必须-o原Override并读回，同时核Timeout未改。不以-r猜测恢复，也不猜默认10秒。恢复失败保锁并报告recovery_required。截止后只允许同boot/holder/回执的STOP与恢复各60秒补救预算，不允许追加启动/UI。
- 复用10-12existing-parent授权模式与10-19ownership/WMS/reentry函数，派生只取消立即首次spawn、以child=none开始等待desktop→host；初始host、锁屏、歧义、失去身份或owned窗口均不spawn。child=none不作为数字PID传窗口parser。spawn-prepared的前台检查、JIT及host_spawn顺序保留。
- 最多一次图标触发spawn，原guardian不存在才启动新guardian。结果未知不重试。到限或外环STOP只写新attempt stop并核新guardian退出，必要时仅对精确PID/birth/argv的新guardian TERM，不碰parent/child；旧控制及失败证据永久保留。
- 真实图标、feed和同child视频动作由外环读实际截图；脚本状态与离线测试不冒认图标或播放成功。机械门通过仅pending_review，播放/声音仍unknown；不自动同意隐私或猜坐标。
## 边界
### 允许修改
- benchmark/2026-10-20-5cd-icon-recovery/**
- specs/toutiao-video-playback/t12-5cd-existing-parent-icon.spec.md
- tools/spec-checks/tests/toutiao_5cd_icon_recovery.rs
### 禁止
- 不改t11、project、旧attempt、冻结代码、运行时、其他板或任何已签原件，不推送。
## 完成条件
### Rule: bounded-icon-recovery — 真实图标先于单次启动
场景: preview与源身份拒绝
  测试: ttvideo_5cd_recovery_offline
  假设 preview或source pin、serial、boot、UID、cfg/run路径不符
  当 生成或检查方案
  那么 preview调用设备为0，错误输入拒绝且不写设备
场景: 桌面到host只启动一次
  测试: ttvideo_5cd_recovery_offline
  审核: human
  假设 精确existing parent且无child与旧guardian，外环已核真实桌面
  当 普通图标使同parent对应host前台且无owned窗口
  那么 新attempt至多一次spawn，原前台守卫不削弱；初始host或未知状态不启动，实际feed由截图独立确认
场景: awake恢复与错误收口
  测试: ttvideo_5cd_recovery_offline
  审核: human
  假设 已记录原Timeout及OverrideTimeout且新attempt临时保活
  当 正常结束、命令失败或截止
  那么 STOP保留，核新guardian终止并恢复原Override读回；未完成恢复明确recovery_required且保锁，旧parent与数据不动
场景: 不可判定spawn不重试
  测试: ttvideo_5cd_recovery_offline
  假设 spawn返回失败或输出不能绑定child，或identity/窗口读取未知
  当 继续处理事件
  那么 不再spawn、不清旧状态、不杀parent或child，保留失败原件且播放unknown
## 排除范围
- 随机崩溃根因、视频实现修复、永久自启部署、换运行时、其他板、设备重启和远程推送。
