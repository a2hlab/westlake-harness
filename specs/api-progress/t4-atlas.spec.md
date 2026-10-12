spec: task
name: "Merge and validate the Chinese API progress atlas"
inherits: project
depends: [t1-registry, t2-java, t3-native]
---

## 意图

把三个独立分片合成可浏览的中文总表及 CSV/JSON，呈现已知实现、验证范围、冻结状态与缺口。校验真实来源、冻结覆盖与版本证据，给出明确覆盖边界。

## 已定决策

- ID 去重，API 交叉关系用 frozen_ids 与 related_ids 表达；分类与统计从 JSON 生成。
- 附录保留两份历史 NDK 逐符号数据与 JNI 占位清单；标明快照日期、版本与计数差异，不作为现态成功声明。
- 校验器只验证结构与来源完整性，语义仍由外环抽查，不把机器 PASS 当成 API 新实测。

## 边界

### 允许修改
- benchmark/2026-10-12-api-progress/**
- specs/api-progress/**
- tools/spec-checks/tests/api_progress.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: 总表覆盖冻结登记并与导出一致
  测试: api_progress_atlas
  假设 三个分片已交付且 frozen.json 可读取
  当 合表并生成中文 Markdown 与 CSV
  那么 所有冻结 ID 均被覆盖，JSON 与 CSV ID 集一致且来源 SHA 校验通过

场景: 缺文件和哈希漂移被检出
  测试: api_progress_atlas
  假设 一条来源缺失或 SHA256 不符
  当 校验来源
  那么 校验失败并指出行 ID 和来源路径，不把未核验来源计为已核验

场景: 不同证据层级不会被合并成全量成功
  测试: api_progress_atlas
  假设 同一能力有静态存在、历史过墙与 t20 截图记录
  当 生成总表
  那么 各级证据、历史与当前部署、未知版本分别保留，首页说明覆盖边界与待补证据

## 排除范围

- 新运行时构建与板测、公开发布或推送、修改 #91 封板条件。
