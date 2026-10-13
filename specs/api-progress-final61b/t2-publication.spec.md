spec: task
name: "Publish final61b views at their exact physical landing depth"
inherits: project
depends: [t1-evidence]
---
## 意图

在独立发布说明中固定实际build子目录到最终MAIN视图的展平映射。直接从已落地HTML物理目录解析所有证据链接，不用生成器固定逻辑origin自证；实际新表未落时保留pending。

## 已定决策

- 冻结core20件不变，实际build/views展平为benchmark/2026-10-14-api-progress-final61b/views。
- 原真实315 MAIN视图只作物理校验控制，不能签认新的61b表。
- 校验器只读，逐个解析HTML内evidenceLinks并核真实目标路径和SHA，JSON/CSV/两语315一致；不存在最终物理目录必须拒绝。

## 边界

### Allowed Changes
- benchmark/2026-10-14-api-progress-final61b-publication/**
- specs/api-progress-final61b/t2-publication.spec.md
- tools/spec-checks/tests/api_progress_final61b_publication.rs

### Forbidden
- 不修改已冻core、MAIN、运行round，不执行设备或新增表架构；未知实际回执不得填通过。

## 验收标准

场景: 原MAIN物理视图链接控制
  测试: api_progress_final61b_publication
  假设 原315 MAIN视图和原证据文件已存在
  当 从真实HTML父目录解析两语evidenceLinks和Markdown
  那么 每个相对链接目标路径和fullSHA匹配声明且315数据与CSV一致
  并且 控制回执声明actual_final61b_checked为false

场景: 多一层目录或错误链接拒绝
  测试: api_progress_final61b_publication
  假设 请求目录深度多一层或者渲染href多一级
  当 执行只读物理校验
  那么 返回非零且不产生最终新表通过回执

场景: 缺最终实采表保留pending
  测试: api_progress_final61b_publication
  假设 未提供实际authority和最终新表
  当 准备精确发布映射
  那么 实际回执字段保持null且冻结core20件SHA不变
