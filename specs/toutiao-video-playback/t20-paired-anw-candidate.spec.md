spec: task
name: "Build exact-shim paired CPU window candidate"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t19-anw-integration-readiness]
tags: [native-window, static, production-candidate]
---
## 意图
针对T18头条实际首墙ANativeWindow_lock返回-19，复用精确85 shim原入口及未改R14/R15，构建可独立复核的同路由PIC候选。预计移走首致命点key=toutiao，仅为条件预测；本任务不执行设备验证。
## 已定决策
- 未改C对象重链必须得到精确85；从已绑定原源码重编须除非ALLOC的.comment外逐字等价，再以两个Android入口替换和独立pair单元派生。
- 不增PRELOAD、不改已有网络包；保留非player原返回和一次日志。仅精确player路径且同base可进入新路径。
- 有效ANativeWindow调用契约下复用精确dca owner的get/acquire/release；拒绝raw-OH fallback，不构造任意指针注册表。
- 七OH接口必须属于owner真实Reference/Unreference GOT所绑定的同一实例；仅artifact SHA或dlsym结果不构成实际实例证明。
- 每次lock成功或retained失败保留一份owner引用；重复lock仅释放本次新引用，成功unlock才释放已有引用，不强行清除失败状态。
- 用户已确认本次同视频音频；本候选只处理画面墙，不回退该事实，也不承诺动态播放。
## 约束
- 任何构建前运行冻结检查；原R14/R15和历史证据不改，运行时stdout/stderr/rc持久保存，失败不删除。
- 生产DSO须保持原defined exports与DT_NEEDED，新增输入逐项SHA及真实构建命令可定位。
## 边界
### 允许修改
- benchmark/2026-10-20-t20-provider-link-slice/**
- specs/toutiao-video-playback/t20-paired-anw-candidate.spec.md
- tools/spec-checks/tests/toutiao_t20_paired_candidate.rs
### 禁止
- 不调用设备、不部署、不推送、不改冻结项或旧R14/R15；不研究随机退出。
## 完成条件
场景: 原基线与生产增量
  测试: ttvideo_t20_paired_candidate
  假设 精确原对象源码与链接输入已取得
  当 检查真实构建回执和输入索引
  那么 生产DSO须保持原defined exports与DT_NEEDED，新增输入逐项SHA及真实构建命令可定位。
  并且 任何构建前运行冻结检查；原R14/R15和历史证据不改，运行时stdout/stderr/rc持久保存，失败不删除。
  并且 基线85完全相同，原C对象除.comment外逐字一致；未改原网络PRELOAD，输出文件和JSON记录AArch64 PIC候选而非部署通过
场景: 实际pair引用生命周期
  测试: ttvideo_t20_paired_candidate
  假设 主机fixture链接实际pair及未改R14和R15
  当 成功lock重复lock再unlock以及retained失败后重复调用
  那么 成功链引用守恒，retained只保留一引用，错误实例与同名foreign caller拒绝
场景: 真机唯一判据待复验
  测试: ttvideo_t20_paired_candidate
  审核: human
  假设 外环另以已审六件CAS和回滚执行候选
  当 复核同child实际paired绑定、owner与provider回执及连续帧
  那么 只有实际正常lock/unlock和动态画面可签视频通过，离线测试及有声均不冒认画面通过
## 排除范围
- 本任务上板、冻结登记、全APK回归、随机崩溃修复、编造未知对象布局。
