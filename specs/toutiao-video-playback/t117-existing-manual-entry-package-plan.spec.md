spec: task
name: "T117 existing approved manual-entry package applicability"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t115-launch-policy-provenance]
---
## 意图
检查T34已批准手动重入恢复包能否按既有构建配方生成适用于5cd的包，为复用已验证修复提供可审核计划。只做适用性和构建入口核对，不盲跨板复制或实际部署。
## 已定决策
- Codex只读T34发布/恢复metadata、构建与参数化包装器、既有原始构建日志/测试结果。watchdog实现及其改名副本内容不读，不重新运行T71/T74/T91停止分析或预检；优先已批准不变的源/制品哈希与现成builder支持的board参数。
- 明确5cd需要改哪些纯部署身份字段，哪些实现字节必须保持一致，现成builder是否支持serial/root参数；T116当前实装元数据到后补精确回滚前像。没有可复用参数化配方就标缺口，不自行改实现或凑候选。
- 给可审核原始命令、输入/输出身份、批准证据和板前检查/回滚计划；不得使用payload/recovery.cfg直接覆盖系统init配置。五分钟首交；本卡不构建、不设备执行、不部署。
## 边界
### 允许修改
- benchmark/2026-10-23-manual-entry-package-plan/**
### 禁止
- 设备调用、源码实现修改或读取停止实现、部署、审批配置变更
## 验收标准
场景: 已验证包存在参数化入口
  审核: human
  测试: manual_entry_package_applicability_review
  假设原批准包和builder元数据明确支持目标身份
  当核对SHA与原构建记录
  那么给可复现适用性计划及回滚引用，不把计划称已经修复
场景: 配方或身份缺口
  审核: human
  测试: manual_entry_package_applicability_review
  假设只有61b包或输入/批准链不完整
  当核对适用性
  那么列明缺项，不盲复制或声称跨板已验证
## 排除范围
新恢复策略、随机崩溃预防、实际构建上板、修改冻结行为。
