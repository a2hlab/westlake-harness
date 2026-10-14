spec: task
name: "API implementation source delivery on default branch"
inherits: project
depends: [t4-reproduce]
---
## 意图
把API全表对应的实际实现源码、补丁与可重建入口合入默认主分支master，使接收方无需访问agent工作树即可定位实现。对所有315记录出来源映射；历史桩不得冒充已冻结实际实现，缺源码不签完整交付。

## 已定决策
- 优先使用源码快照和冻结blob/构建SHA匹配的现有本地、VM、远端原件，保留上游许可。
- 新源码交付放独立sources目录；不替换当前板产物或改冻结期望。每项区分仓内完整源码、上游锁定依赖与未闭环缺口。
- 中文英文表格从同一增量源生成，保留既有验证事实及unknown版本，实际点击链接验证后合入master。

## 边界
### 允许修改
- benchmark/2026-10-14-api-source-delivery/**
- sources/api-implementations/**
- tools/spec-checks/tests/api_source_delivery.rs
### 禁止
- 不修改冻结实际运行时文件或原签认证据，不把旧空桩当成生产实现。
- 不提交凭据或大型构建产物，不伪造原构建日志。

## 完成条件
场景: 实现定位完整
  审核: human
  测试: api_source_delivery
  Given API rows and pinned actual implementation source hashes
  When delivering source files on the default branch
  Then every delivered row resolves to exact tracked source files and a documented build entry

场景: 拒绝缺失源码
  审核: human
  测试: api_source_delivery
  Given a missing implementation or an old stub conflicting with frozen source
  When generating the source coverage table
  Then the row reports the missing source and cannot be marked complete
