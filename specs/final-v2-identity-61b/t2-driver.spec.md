spec: task
name: "61b original Mac full128 driver narrow hook adaptation"
inherits: project
depends: [t1-proof]
---

## 意图

复制已审 Mac driver，只绑定新61b身份门与额外输入约束，保持原计划、执行、收集与special slots语义。

## 已定决策

- 复用7cc72083原driver，主控/锁/nativeHDC留Mac，prelock及前后identity hook走Orb。
- 原manifest/tier source精确pin，不接受128子集、tier改变或历史结果充当fresh结果。

## 边界

允许修改: benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-identity-61b/**、本契约、tools/spec-checks/tests/final_v2_identity_61b.rs。
禁止修改: 原driver、board_run、collect实现、兄弟工作树与设备。

## 验收标准

场景: 原128计划与收集机制保留
  测试: final_v2_driver_61b
  假设 完整128清单和121t10+7t20已pin
  当 生成离线round并比较原driver AST
  那么 8窗口默认disabled且resolve/records/collect和特殊槽完整保留

场景: 减成员或错绑定被拒
  测试: final_v2_driver_61b
  假设 manifest或tiers或hook/proof SHA改变
  当 进行离线准备或mock执行
  那么 原绑定门拒绝且不发生设备调用

场景: 缺record或失败窗口不能变成完成
  测试: final_v2_driver_61b
  假设 mock窗口失败或缺少真实本窗record
  当 原execute逻辑处理窗口
  那么 保留失败STOP与partial collect并不产full-round成功
