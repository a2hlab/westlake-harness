spec: task
name: "Android reference playback and bounded trace"
inherits: project
satisfies: [REQ-TTVIDEO]
tags: [android-reference, human-review]
---
## 意图
以同APK安卓设备作播放对照，记录真实20秒内容变化与trace/logcat时序；不把安卓通过当OH通过。
## 已定决策
- 仅序列号N100CU025C18D000128，先持同规范独占锁；总窗不超过20分钟，每条采集命令host超时10秒，trace后台自止20秒，用后释放锁。
- 实际截图先行，以普通桌面图标打开已装头条并正常进入视频；如需凭据立即停止UI。不得重装、强停、清数据或日志、改账号网络，不点赞关注评论。
- 尽量选择木子很甜或我觉得小伙说的挺合理的同片，找不到则明确different_clip；在t0/t5/t10/t20保存截图，内容ROI与控件变化分开。
- 使用已验证存在的perfetto或atrace，保留原始argv/stdout/stderr/rc及时间；失败或partial不冒充trace成功。APK精确SHA与OS/API/ABI记录，原隐私日志截图仅持久私存。
## 边界
### 允许修改
- benchmark/2026-10-20-t23-android-reference/**
- specs/toutiao-video-playback/t24-android-reference.spec.md
- tools/spec-checks/tests/toutiao_t24_android_reference.rs
### 禁止
- 不改OH设备、运行时代码、冻结项或用户数据；不绕过锁屏、不提权、不推送。
## 完成条件
场景: 正常播放对照与时序
  测试: ttvideo_t24_android_reference
  审核: human
  假设 精确APK与安卓独占锁已核且截图显示可普通操作
  当 正常图标打开视频并采集20秒trace和t0/t5/t10/t20截图以及有界logcat
  那么 实际内容帧与时间可对应且同片或不同片明确，不以控件前进代替画面，不签OH通过
场景: 锁屏凭据与权限失败
  测试: ttvideo_t24_android_reference
  审核: human
  假设 锁屏需凭据或trace命令权限不足或超时
  当 采集实际错误与已有原件
  那么 停止受阻操作且不提权重装强停，不将partial判成功，保留unknown并释放自己的锁
场景: 截止与隐私交付
  测试: ttvideo_t24_android_reference
  审核: human
  假设 每命令10秒限时与20分钟总窗生效
  当 完成或到限收口
  那么 记录实际开始结束和截图数，私存原件，公开只给SHA与技术摘要；不清数据日志、不改网络账号、不点赞关注评论，释放自己的锁
## 排除范围
- 安卓源码改造、OH新窗口、随机崩溃根因、账号操作、追求相同推荐而无限导航。
