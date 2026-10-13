spec: task
name: "61b complete candidate proof from exact T4 planned selfcheck"
inherits: project
---

## 意图

只消费 T4 已 pin 的 candidate plan、完整 planned selfcheck 和同板来源，生成 disabled proof/smoke；沿用原只读 Reader 与完整 runtime/boot 判据。

## 已定决策

- 完整 expected union 来自 T4；校验319+4替换、Boat18对象及 RouteB487/HAP，不另造 seal。
- 精确 BMS UID 来自 T4 专用 bookended 原回执；读取失败、未知、任何缺失或错 SHA 均拒。

## 边界

允许修改: benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-identity-61b/**、本契约、tools/spec-checks/tests/final_v2_identity_61b.rs、README.md、.octos/KNOWLEDGE-DIGEST.md。
禁止修改: 兄弟源码、设备、原 Reader/driver/运行时、授权与历史签认。

## 验收标准

场景: 完整计划生成 disabled 身份门
  测试: final_v2_identity_61b
  假设 同一 T4 plan 与 planned selfcheck 的全部输入逐SHA匹配
  当 本地编译 proof 和 smoke
  那么 完整319保留且4替换正确并覆盖954完整对象及RouteB实际存在
  并且 输出默认disabled且不发生设备调用

场景: 身份删减与串板材料拒绝
  测试: final_v2_identity_61b
  假设 一条原319或RouteB项缺失或输入来自5ea
  当 编译或load_proof执行校验
  那么 非零拒绝且不写可执行输出

场景: 真实读回错误拒绝
  测试: final_v2_identity_61b
  假设 SHA读取失败或BMS UID漂移或boot改变
  当 mock原只读transport执行身份门
  那么 保留原失败关闭规则并拒绝PASS
