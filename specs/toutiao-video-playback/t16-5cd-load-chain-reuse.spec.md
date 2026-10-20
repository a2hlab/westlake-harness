spec: task
name: "5cd exact observed player load-chain reuse"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t15-fixed-range-read]
tags: [5cd, reuse, deployment-plan, human-review]
---
## 意图
移走T15已证明的头条libttmplayer装载首阻断SL_IID_ANDROIDSIMPLEBUFFERQUEUE，复用现有R8四件观察包及R3/R4加载/cache修复；预期影响key仅toutiao。当前交件仅静态参数和证据，执行器已派生但外环准入独立另审，不能由本机测试升级为上板许可。
## 已定决策
- 唯一目标5cd1e3dd00000000000000000923012c，UID20011300、cfg19d0201b、原run5a3aef63、mediafecf91e1/playerb427614d；不复用61b的UID/cfg/回滚计划/APPROVED。
- R8现成四件：5cd派生run、compat6e83e924、mediad2882303、player0b4d95c5；源码/构建原始日志及产物SHA均沿主仓档案复用，不重建、不重新REA。run只允许已审模板owner UID和实测host WID派生；29只是历史值。
- 先持唯一板锁并只读钉boot/parent/birth/UID/exe/private namespace、物理/私有inode、preimage/metadata/label、cfg/control、provider与兼容库确实不存在；未知项拒绝。精确执行器源SHA及新外环admission齐备前保持DISABLED。
- 沿既有CAS和backup/swap逻辑派生5cd执行器，全部原备份及apply-plan持久化后才能第一处替换；已存在compat或外国字节拒绝。中途失败只按本次5cd原apply-plan恢复，不使用61b或新WID猜原件。
- 经实际启动器证据允许唯一WL_PARENT_ID数字行派生：完整原字节先保存并核SHA，将唯一该行规范化29后必须与已钉before/after逐字一致，其他差异拒绝；活parent时还须fresh WMS与parentenv一致。无parent仅rollback可走物理恢复支，绑定本次原apply-plan/source/holder/start/备份与freshboot/cfg，恢复精确5a3；不把物理恢复当运行态恢复。
- 一窗最多30分钟，至少预留10分钟恢复；候选需freshboot，以新child验证。失败/到时即恢复原四件状态、freshboot、同一snapshot-plan对照与实际图标/feed。正常UI可暂时保活但必须原值恢复；不清数据，不追随机退出。
- 成功只可声明实际IID加载错误消失及player进入下一阶段；ANW/网络/音频仍可能阻断。动态有声播放仍按project两周期标准，封面或prepare不算播放。
## 边界
### 允许修改
- benchmark/2026-10-20-t15-player-load-reuse/**
- specs/toutiao-video-playback/t16-5cd-load-chain-reuse.spec.md
- tools/spec-checks/tests/toutiao_t16_reuse_plan.rs
### 禁止
- 不改旧候选/旧证据/冻结源码/61b；本交件不执行设备、不编译、不推送。
## 完成条件
场景: 静态交件参数与原件绑定
  测试: ttvideo_t16_reuse_plan
  假设 本次原range与五条公开excerpt及既有四件包
  当 离线检查参数、原字节SHA和实际CAS/唯一WID派生负面测试
  那么 定位精确source offset且板UID/cfg/before均为5cd，模板只做两项派生，状态仍DISABLED
场景: 上板准入不能由静态检查代替
  测试: ttvideo_t16_reuse_plan
  审核: human
  假设 尚缺fresh只读字段或5cd新执行器独立审查
  当 外环评审部署请求
  那么 拒绝执行；齐备时核CAS/部分应用回滚及30分钟预算后单独签认
场景: 真实加载进展与恢复
  测试: ttvideo_t16_reuse_plan
  审核: human
  假设 已独立准入且新child实际触发正常播放
  当 收集日志并按本次apply-plan恢复
  那么 IID错误消失须真实证据，后续首错原文保留，原5cd状态与图标feed复核；无动态有声证据不得封板
## 排除范围
- R9网络修复、R10 ANW修复、MediaPlayer假桩、重新研究已知IID问题、随机退出诊断和设备实际执行（本交件仍未执行）。
