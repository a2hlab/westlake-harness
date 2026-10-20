spec: project
name: "T30 recover only proven resource-free request failure"
satisfies: [REQ-TTVIDEO]
---
## 意图
T29实测Request返回40601000且buffer为空，后续provider阶段未调用，但保守retained使R14/R26长期FAILED并拒绝后续lock。T30仅解除可证明未取得资源的一次失败造成的持续拒绝；首次Request错误的原因仍UNKNOWN。
## 约束
- 从T29实际生产对应源另派生，不改历史T18/T20/T23/T26/T27/T28/T29源码、旧回执及冻结API登记；只授权本契约和离线实现准备，上板与生产由外环另行组织。
- 不新增provider选择、调用循环、定时重试或force reset；不改几何、YV12布局/转换、RGBX输出、三槽same-provider门、owner实例验证、8槽alias和生命周期前提。
- 恢复只针对本次Request非零且明确无buffer/native/map/fence资源；任何已取得资源、cleanup失败或资源状态不明仍保留FAILED及引用保护。禁止把首错吞成成功。
- 锁内只转移当前占有reservation，保持既有mutex/线性化点；错误报告含原Request raw rc与实际调用/retained字段，成功路径顺序、调用次数、输出和errno保持原行为。
- 离线fixture必须调用真实派生pair/R14/R26实现，只有外部OH/provider/sink为替身。机器通过不等于真机切换恢复；运行时图像由外环审核，不用进程存活替代。
