spec: task
name: "V1 concrete seal and restoration assembly"
inherits: project
---

## 意图

提前把已有 v1 封存编译器、部署件来源和恢复 provider 接成可执行的材料装配器。最终现场证据未到时明确拒绝出 seal，证据到齐后无需再人工重写整套材料。

## 已定决策

- 复用主树 t5 编译器和 wiki 的已批准 Plan2 参考，范围是 v1 无 Boat、61b20-key 加 5cd既有128交叉对照；不得扩回61b全量128。
- 查明真实 base provider、Route B provider、回滚程序和归档来源，以参数接受新 executor 和 live snapshot，不猜 SHA 或签名。
- 输出独立目录，保持历史 t5、旧 plan/run 不变；默认仅本地预览。未知或模拟输入不能编译成真实完成 seal。

## 边界

### 允许修改
- benchmark/2026-10-12-v1-seal-assembly/**
- tools/spec-checks/tests/v1_seal_assembly.rs

## 验收标准

场景: 真实材料装配映射完整
  测试: v1_seal_assembly_inventory
  假设 已有 U13 和 Route B 来源与 Plan2 参考
  当 运行本地装配预览
  那么 列出每个 provider 文件 SHA 和恢复顺序以及20-key与128参考路径，执行板命令数为零

场景: 未验收输入拒绝生成完成封板
  测试: v1_seal_assembly_reject
  假设 缺现场快照、交互签认、归档 SHA 或任一个恢复 provider
  当 请求生成最终 seal 和启用恢复配置
  那么 非零退出列出确切缺项且不产生可执行 seal，不修改历史件或冻结表

场景: 合成材料只生成标明合成的测试结果
  测试: v1_seal_assembly_fixture
  假设 一套标为 synthetic 的完整隔离材料
  当 测试编译器和恢复计划的序列号投影及文件漂移
  那么 合成输出保持 synthetic 且不得准入真实设备，文件漂移非零退出并指出对象

## 排除范围

- 实际板访问、恢复演练、签字、编造缺失现场结果、修改历史 t5、Boat 和 API 全表扩展。
