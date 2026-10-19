spec: task
name: "5cd existing-child normal play observation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t11-5cd-icon-readiness]
tags: [bounded, device, human-review]
---
## 意图
在外环新只读回执绑定的5cd当前存活头条中，执行一次可见播放操作，取得真实播放器加载或失败证据。缺库静态推导不代替播放动作，不将T13重开任务扩大为视频试验。
## 已定决策
- [platform-specific] 唯一serial为5cd1e3dd00000000000000000923012c；boot、parent/child/host PID及birth/UID/exe、private mount namespace和run SHA由新profile绑定；不预设T13 child。身份漂移停止，默认preview零设备命令，执行必须显式execute和exact holder。
- 复用bms_batch.Board的boot/lock/remote rc及固定增量逻辑。600秒含恢复，UI及采集在540秒前停止，60秒只恢复；原power Timeout/Override持久记录后才-o86400000，每次uitest后刷新，最后-o原Override并核两字段，失败保锁报告recovery_required。
- 正常wakeup、外环亲读截图决定的解锁/当前活头条前台操作；视频tab最多一次、可见play最多一次。每次坐标需对应本窗最新截图SHA与外环review标记；无自动重试、无猜坐标，UI动作先记intent再执行，未知不得重放。
- 播放前stat保存日志dev/inode/size，播放后同child同inode定长读新增最多65536字节。HDC已证stdout/stderr合流，使用声明长度及唯一边界/后guard marker；dd短读、错误、marker缺失、超时均PARTIAL，原bytes保留，配置JSON命中不当异常执行。
- 只允许本窗截图、layout、dd诊断临时文件；无guardian启动、无应用启动/信号、无部署/attach/reboot/应用数据修改。正常应用自身写入不由工具阻止。
## 边界
### 允许修改
- benchmark/2026-10-20-t14-play-observation/**
- specs/toutiao-video-playback/t14-normal-play-observation.spec.md
- tools/spec-checks/tests/toutiao_t14_play_observation.rs
### 禁止
- 不改t13、旧观察器、冻结源码、runtime、APK、配置、旧证据或其他板，不推送。
## 完成条件
场景: preview与身份错误拒绝
  测试: ttvideo_t14_offline
  假设 preview或profile/holder/boot/child身份不匹配
  当 请求操作
  那么 preview设备命令为0，错误输入停止且不执行UI
场景: 一次可见播放需独立审核
  测试: ttvideo_t14_offline
  审核: human
  假设 同child真实feed且外环已读本窗截图
  当 外环逐次提供tab与play坐标
  那么 每种最多一次且旧截图或重复请求拒绝，真实加载与动态播放由截图及原日志判定而非脚本PASS
场景: 合流日志失败保持partial
  测试: ttvideo_t14_offline
  假设 日志发生短读、dd错误、marker缺失或host超时
  当 读取固定字节增量
  那么 原stdout/stderr保存且非完整frame拒绝，缺失player attempt为unknown
场景: 截止或失败恢复power
  测试: ttvideo_t14_offline
  审核: human
  假设 原power已保存且临时保活
  当 窗口结束、身份漂移或命令失败
  那么 停止UI并在同boot和holder下恢复原值，失败保锁且recovery_required，不信号任何应用
## 排除范围
- 视频修复、optional库提取部署、随机退出诊断、自动拉起、网络/内容服务策略修改与完整播放封板验收。
