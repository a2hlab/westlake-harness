spec: task
name: "Toutiao video dynamic playback and API delivery"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t2-minimal-repair]
tags: [media, waiting-for-candidate, human-review]
---
## 意图
在外环分配的空闲板验证候选实际播放，再与图标重开主任务合流到61b。交付有声动态帧、暂停恢复退出证据与实现/构建/API表对照，不把一张封面或探针结果当头条通过。
## 已定决策
- 外环分配serial并持板锁，开窗前核只读身份与原回滚；先空闲5cd或5ea，61b图标任务锁释放且候选通过后另开窗口。APK/视频内容/网络条件和runtime指纹均记录。
- 两个周期各播放20秒、暂停3秒、恢复10秒、退出回feed并手点图标再次进入；120秒观察窗包含视频进入与回退，超出30分钟实验限时则保存未完证据并回滚解锁。
- 每周期采t0/t5/t10/t20及暂停/恢复/退出snapshot_display，记录视频内容ROI、播放时间与对应Surface；内容帧变化排除spinner/字幕/控件假动，声音须外部录音或人工听验具名回执，音频计数不能替代听到声音。
- 更新独立API增量表：精确API→源码blob/commit→构建配方→产物SHA→OH完整版本/ABI→APK SHA与targetSdk→实测范围与证据；生成与当前主表的合并清单，由外环统一出版，历史版本/unknown不改写。
- 失败保留运行目录/facts并按原基线回滚；没有第二个app验证同API时标unfrozen。正式合代码与远程发布由外环执行。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/runs/**
- benchmark/2026-10-19-toutiao-video-playback/api-delta/**
- specs/toutiao-video-playback/t3-playback-seal.spec.md
### 禁止
- 不夺板锁、不覆盖历史签认、不重签旧boot、不改冻结登记或主API表历史证据；不删用户数据。
## 完成条件

### Rule: evidence-before-verdict — 先绑定证据再判断
场景: 两轮有声播放暂停恢复退出
  测试: ttvideo_playback_receipt
  审核: human
  假设 空闲板serial已分配且持板锁，只读身份及真实APK和候选SHA及原回滚均核对
  当 在120秒观察窗按两轮20秒播放3秒暂停10秒恢复及退出序列执行并保存t0/t5/t10/t20的snapshot_display与ROI和声音回执
  那么 两轮视频内容持续变化、声音与内容对应、暂停停止前进、恢复继续、退出显示feed且图标可再打开
  并且 保留按实际captured计数的facts而非计划截图数
场景: 封面冻结静音或服务拒绝拒绝通过
  测试: ttvideo_playback_receipt
  审核: human
  假设 只有封面变化或无听验或网络服务拒绝
  当 审查当前boot证据
  那么 记failed或external_blocked而非playback_pass并保留原始证据和facts回滚结果；30分钟超时同样回滚解锁
场景: 图标任务占锁与回归拒绝
  测试: ttvideo_playback_receipt
  审核: human
  假设 61b仍由图标任务占用或候选使图文入口回归
  当 准备61b发布
  那么 不写61b且前者等释放后重排，后者回滚并禁止封板
场景: API源码构建实测对应
  测试: ttvideo_playback_receipt
  审核: human
  假设 实测结论与候选源构建证据已定
  当 生成api-delta与主表合并清单
  那么 每个变化API有源码blob/commit、构建配方、产物SHA、OH完整版本/ABI、APK SHA/targetSdk和实测边界且只有单app时冻结状态为unfrozen
## 排除范围
- 随机崩溃根因、安全机制改造、用户数据清理和自动远程推送。
