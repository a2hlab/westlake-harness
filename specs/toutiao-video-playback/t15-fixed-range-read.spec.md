spec: task
name: "T14 exact historical log range recovery"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t14-normal-play-observation]
tags: [readonly, bounded, human-review]
---
## 意图
补采T14已发生交互的固定日志范围，避免64KiB头段遗漏实际点击。只读已知regular日志，不重放UI、不改T14原件、不选择新child；完整原bytes供外环判断实际播放器首个错误。
## 已定决策
- [platform-specific] 5cd既有T14 profile SHA eb2887fbdbdaf23d6fc1cd2840b0d8d80ea5854962753e7d4d13ce311346a077钉boot/parent/child1601与birth/UID/exe/private namespace，执行前后fresh guard；日志dev66352/inode178230，唯一选区[26377929,57241402)，共30863473字节。
- 新持锁窗口最多300秒，单次transfer最多180秒并留20秒收口；复用bms_batch.Board及T14身份guard。默认preview零设备调用，显式execute绑定exact holder和时间；无app操作、信号、启动、power、重启、部署、attach。
- block dd读完整固定范围，4096对齐最多额外4095前缀，尾部bs1最多4095字节；不以bs1读取几十MB。selected最大64MiB，源范围不跟随文件追加扩大。不足范围、身份/inode变化、短读或dd错误拒绝完整。
- HDC合流采用长度声明、唯一end双dd rc与后guard marker，stdout/stderr直接落持久文件，超时保留全部已到bytes并标PARTIAL。仅新独占临时目录保存dd诊断，原日志/应用数据不改；测试不冒认设备PASS。
## 边界
### 允许修改
- benchmark/2026-10-20-t14-fixed-range-read/**
- specs/toutiao-video-playback/t15-fixed-range-read.spec.md
- tools/spec-checks/tests/toutiao_t15_fixed_range.rs
### 禁止
- 不改T14、已签证据、runtime、APK、应用数据、其他板，不推送。
## 完成条件
场景: exact范围与preview
  测试: ttvideo_t15_offline
  假设 默认preview或错误profile/范围/holder
  当 请求补采
  那么 preview设备命令为0，错误输入拒绝且不执行UI
场景: 固定块读取保留binary原字节
  测试: ttvideo_t15_offline
  审核: human
  假设 同child/inode及固定结束位置已经核实
  当 原文件继续追加且读取完整frame
  那么 selected字节严格等于固定范围，附SHA和source offset，实际首错误由原文独立判定而非截图推测
场景: 短读或超时不得完整
  测试: ttvideo_t15_offline
  假设 dd错误、短读、marker缺失、身份漂移或host timeout
  当 固定范围读取失败
  那么 已到stdout/stderr持久保留并标PARTIAL，停止且不扩大读取或重试
## 排除范围
- 新UI播放、全量hilog、根因重新研究、库修复部署、随机崩溃诊断、演示封板签认。
