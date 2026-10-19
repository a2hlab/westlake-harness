spec: task
name: "5cd exact owned-child exit then one manual icon reentry"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t12-5cd-existing-parent-icon]
tags: [bounded, device, human-review]
---
## 意图
T12仅证明旧START_FAILED经一次图标到feed，尚未证明child退出后再次手点可重开。T13在同boot收养已明确的当前owned child，观察其退出后等待唯一一次真实桌面到图标转换，验证新child及实际feed；不诊断随机退出，不永久部署。
## 已定决策
- [platform-specific] 唯一设备5cd1e3dd00000000000000000923012c，boot0525bb05-f714-42ad-90f0-ecdb10356c4f，parent19163/birth7265322，收养child31210/birth7485570，UID20011300，SceneBoard UID20010017。只读preflight重核boot/UID/birth/parent/namespace/exeSHA/run私有inode及cfg/runtime/helper完整SHA；child已退出、歧义或身份漂移立即拒绝，不替换其他child，不启动替代child。
- 复用R2 main的TT_CHILD_PID/BIRTH收养分支及child_owned、monitor_child、rc_reentry_loop，禁止缺child回落首次do_one_launch。收养seq0→1不是新spawn，唯一新图标spawn成功seq1→2；保留T12 STOP/截止guard，停止阈值为seq>=2，不使用T12的seq>=1。进入外部spawn后的任何未知结果保持sticky hold，不重试；前置失败不自动重启。
- 全新icon-manual-5cd-t13-*控制目录；旧T12 guardian必须已退出且无其他controller，旧状态/STOP/失败回执不删不改。T13独占锁与window-start绑定，600秒含采集与恢复，监护uptime截止提前60秒；到限仅同回执STOP/恢复补救各60秒，不追加TERM/UI/spawn。
- 退出方式预先选择natural或term-once。natural仅等待；term-once只在收养instance/guardian精确绑定完成且child仍alive时，重复完整child_owned及boot/parent核对后调用既有rb_signal 31210 7485570 TERM一次。禁止parent/group/其他child信号、KILL升级及自动重发；TERM rc0不是已退出证据，未退出即unknown收口。若收养前已退出则拒绝；收养后自然退出可继续但不补发TERM。
- 精确确认原child已不存在或同birth为Z，并记录AWAITING_REENTRY；身份不明/PID复用拒绝。外环先看到t13_desktop_seen及真实桌面截图，再只手点一次精确图标；初始host、锁屏、owned旧窗口、读取未知或STOP到达不spawn。新child必须与原PID/birth不同并通过既有readiness及owner核对。
- 沿T12读取原Timeout/OverrideTimeout、临时awake86400000、收尾恢复原Override并核Timeout不变；正常/失败/截止均STOP新guardian、核其退出并恢复awake。仅新guardian允许按既有精确PID/birth/argv的TERM收尾；不杀新child。恢复失败保锁报recovery_required。原JIT/host_spawn顺序和所有runtime helper不变；不改cfg、JAR/APK/runtime、应用数据，不重启。
- 工具默认preview零设备零写，preflight显式只读；apply、term-once、stop、restore仅外环execute且保存原始argv/stdout/stderr/host和remote rc。截图/真实图标/新feed判为human；机械门不等于feed或播放，不自动同意隐私。
## 边界
### 允许修改
- benchmark/2026-10-20-5cd-owned-child-reentry/**
- specs/toutiao-video-playback/t13-5cd-owned-child-reentry.spec.md
- tools/spec-checks/tests/toutiao_5cd_owned_child_reentry.rs
### 禁止
- 不修改project、T12/source-profile、冻结helper、旧attempt、运行时、其他板、历史签认，不推送。
## 完成条件
### Rule: exact-adoption — 仅收养指定当前对象
场景: child缺失或复用拒绝
  测试: ttvideo_t13_adoption_refuses_drift
  假设 固定child已退出、birth/UID/ppid/boot/inode不符或出现其他guardian
  当 preview或preflight及apply再次核对
  那么 preview零设备，错误身份拒绝且零TERM零spawn，不挑选其他child
场景: 收养保持首轮零spawn
  测试: ttvideo_t13_adopts_without_spawn
  假设 固定child和parent全部身份与回执一致
  当 实际R2收养分支进入monitor_child
  那么 instance记录seq1及固定child，外部spawn调用数0，缺TT_CHILD_PID/BIRTH拒绝而非首次启动
### Rule: one-exit-one-icon — 受限退出和唯一图标重入
场景: TERM精确范围与失败拒绝
  测试: ttvideo_t13_signal_exact_child
  假设 term-once已选且固定child仍owned，或identity在信号前变化
  当 监护收养后外环执行TERM请求
  那么 仅既有rb_signal对固定PID/birth发送一次TERM，漂移发送0次；parent/group/替代child从不收到信号；TERM失败不重发不KILL
场景: 自然退出和死亡读不确定
  测试: ttvideo_t13_exit_classification
  假设 原child自然退出、同birth僵尸、PID复用或stat读取未知
  当 实际monitor_child与exit-verdict判定
  那么 仅确定退出转AWAITING_REENTRY且无自动spawn；其他情况拒绝，等待退出模式发送0次TERM
场景: 唯一真实图标到新feed
  测试: ttvideo_t13_one_reentry
  审核: human
  假设 收养seq1原child确定退出且外环已核真实桌面
  当 唯一普通图标使同parent对应host前台
  那么 最多一次外部spawn产生新PID/birth并到seq2，经过readiness后实际截图确认feed；初始host或旧owned窗口不spawn，未知spawn保持hold；结论仅一轮受限重入而非永久部署或视频通过
### Rule: bounded-cleanup — STOP与awake恢复
场景: 截止或STOP跨过采样拒绝
  测试: ttvideo_t13_stop_deadline
  假设 STOP或uptime截止发生在focus读取、owner检查或JIT之后
  当 即将派发spawn或exec real-spawn
  那么 保留T12派生前置guard并拒绝新的调用，不因seq1的收养计数提前停止；seq2不再接受新spawn
场景: 故障收尾与参数恢复
  测试: ttvideo_t13_cleanup
  审核: human
  假设 窗口成功、命令失败、TERM未退出或600秒截止
  当 外环执行同回执stop与restore
  那么 核新guardian退出、原Override恢复和Timeout未改，失败保锁recovery_required；原parent和新child不被收尾信号，runtime/cfg不变且原始facts不重算为存活
## 排除范围
- 随机退出根因、视频播放修复、反虚拟化、永久服务、换cfg/运行时、重启、批量重试、其他板和远程推送。
