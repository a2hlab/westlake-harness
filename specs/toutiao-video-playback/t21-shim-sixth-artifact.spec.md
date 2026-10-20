spec: task
name: "5cd T21 shim sixth-artifact guarded transaction"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t18-bridge-fifth-artifact]
tags: [5cd, shim, rollback, offline]
---
## 意图
从精确T18执行器57affbe派生六件事务，新增runtime webview-t-lib内shim。候选尚未生产时仅交付可审核执行源码，候选SHA和生产原件未冻结必须拒绝execute；不以离线事务通过宣称视频修复。
## 已定决策
- 原T18五件与1800秒窗口、600秒恢复余量、实际holder/boot/parent/host/private namespace守卫保留；stage及backup使用T21独立名字。
- shim前像固定85c789，候选使用单独shim-candidate.json，默认null；候选生产引用、当前源码及fresh admission metadata/label逐哈希绑定后才创建Board。
- 六项前像全齐再首次swap：五份真实文件备份加compat原本ABSENT的持久标记。原apply-plan先持久；partial rollback仅恢复本次前像，foreign与符号链接拒绝。
- rollback保留唯一数字WID归一化和exact5a3恢复；no-parent仅物理恢复，不能冒认旧namespace已恢复。freshboot、真实绑定与截图由外环另验。
## 边界
### 允许修改
- benchmark/2026-10-20-t21-shim-deployment/**
- specs/toutiao-video-playback/t21-shim-sixth-artifact.spec.md
- tools/spec-checks/tests/toutiao_t21_shim_transaction.rs
### 禁止
- 不修改旧T18或冻结运行时源码，不上板、不推送、不写主树，不新增部署例外。
## 完成条件
场景: 精确派生和默认预览
  测试: ttvideo_t21_shim_transaction
  假设 原T18 donor匹配
  当 运行derive和不带execute的三模式
  那么 输出可复现源码且device_calls为0
场景: 未冻结候选拒绝执行
  测试: ttvideo_t21_shim_transaction
  假设 shim候选SHA为空或生产引用缺失或漂移
  当 显式请求execute
  那么 在创建Board前失败且不产生运行目录
场景: 真实事务部分失败恢复
  测试: ttvideo_t21_shim_transaction
  假设 五份文件与ABSENT标记先备齐
  当 实际生成shell在任一替换后失败并执行原回滚构造
  那么 五原件字节恢复且compat删除，foreign及符号链接保持拒绝
场景: 本窗实际恢复复验
  测试: ttvideo_t21_shim_transaction
  审核: human
  假设 候选生产闭包已冻结且外环持锁准入
  当 六件部署与本次apply-plan绑定回滚后freshboot
  那么 外环依原快照和实际namespace及图像裁决，离线交件不声明播放通过
## 排除范围
- 候选编译、原shim行为修复、设备执行、随机退出调查、61b操作及视频验收升级。
