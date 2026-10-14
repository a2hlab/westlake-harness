# Contract Review: API implementation source delivery on default branch

## Intent

把API全表对应的实际实现源码、补丁与可重建入口合入默认主分支master，使接收方无需访问agent工作树即可定位实现。对所有315记录出来源映射；历史桩不得冒充已冻结实际实现，缺源码不签完整交付。

## Decisions

- 优先使用源码快照和冻结blob/构建SHA匹配的现有本地、VM、远端原件，保留上游许可。
- 新源码交付放独立sources目录；不替换当前板产物或改冻结期望。每项区分仓内完整源码、上游锁定依赖与未闭环缺口。
- 中文英文表格从同一增量源生成，保留既有验证事实及unknown版本，实际点击链接验证后合入master。

## Boundaries

**Allowed:**
- benchmark/2026-10-14-api-source-delivery/**
- sources/api-implementations/**
- tools/spec-checks/tests/api_source_delivery.rs

**Forbidden:**
- 不修改冻结实际运行时文件或原签认证据，不把旧空桩当成生产实现。
- 不提交凭据或大型构建产物，不伪造原构建日志。

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 2 | 0 | 0 | 0 | 0 | 0.0% |

- 👁️ 实现定位完整
  - test: `api_source_delivery`
- 👁️ 拒绝缺失源码
  - test: `api_source_delivery`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | 实现定位完整 | api_source_delivery | found | pending_review | computational |
| — | 拒绝缺失源码 | api_source_delivery | found | pending_review | computational |
