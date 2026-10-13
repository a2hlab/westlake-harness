spec: task
name: "RouteB exact current-prestate recovery rehearsal"
---

## 意图

为当前5cd备机完整Boat加RouteB恢复演练补齐真实前像重绑定。旧43bc恢复历史不能作为362f当前执行授权；保留原487目标与签认来源，复用既有事务，新增独立派生配方。

## 已定决策

- 输入必须为同板同boot真实497捕获、原940 R5及其487历史、当前全部22目录和补集目录metadata/inode原回执。
- 复用原487成员集合、字节来源、原事务全备份与部分写失败观察；当前前像逐件用实测SHA/metadata与本地精确来源绑定。无未知SHA豁免。
- 已有目录作为精确前置条件保留，不伪造absence、不删除数据；本修订要求29目录全部真实存在，缺失即拒；原r4b缺失目录恢复保持独立，非空未知内容不清除。
- runtime源文件写入采用独立临时inode、前像CAS、metadata及SHA读回再rename，避免截断正在映射的旧inode。旧executor保持原字节，新派生仅此写入与当前前像准入接线。
- 新授权独立钉recipe/plan/executor/当前boot/holder/expiry，默认disabled预览零设备；原seal/旧gate/旧487原始回执不可改。
- 完整恢复必须真实487逐件placed及事务回执、目录补集结果、零附加重启；已有态验证不得冒充恢复。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/routeb-fresh-restore/**
- specs/demo-recovery-followup/t12-routeb-fresh-restore.spec.md
- tools/spec-checks/tests/routeb_fresh_restore.rs

### 禁止
- 不改已冻结provider/selfcheck/executor、原seal、旧授权、现运行目录及用户数据。
- 不操作设备、VM、远端；不推送；61b零操作，不新增验收门或应用集合。

## 验收标准

场景: 当前前像可复现编译
  测试: routeb_fresh_compile
  假设 真实同boot497文件和完整目录metadata及原487来源均已独立钉SHA
  当 默认离线编译恢复配方
  那么 目标恰487且源字节完整SHA与原R5逐项一致，新boot和前像逐项可追溯，输出disabled且设备调用为零

场景: 漂移与未知前像拒绝
  测试: routeb_fresh_reject
  假设 输入存在旧boot混入、目录inode变化、源SHA漂移或签名角色缺失
  当 编译或准备执行
  那么 非零拒绝且任何send或rename之前停止，旧gate原字节保持

场景: 实际事务形状与回滚
  测试: routeb_fresh_transaction
  假设 使用真实487计划形状和recording transport注入部分写失败
  当 执行apply及rollback
  那么 所有备份首写前验证，独立stage与前像CAS成立，失败记录精确observation并可恢复原字节元数据，未知文件保留且非零

场景: 完整恢复结果不借旧证
  测试: routeb_fresh_receipt
  假设 本次事务已生成487独立placed回执与目录补集回执
  当 汇编恢复结果或输入缺失一个回执的负例
  那么 仅完整绑定本次plan及executor_rc0时出恢复完成，缺件拒绝，原487历史保留且零额外重启

## 排除范围

- 新的运行时构建、61b部署、旧签认修改、演示UI签认、全128验收替代及原生崩溃修复。
