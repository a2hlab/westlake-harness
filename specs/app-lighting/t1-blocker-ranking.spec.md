spec: task
name: "T1 blocker 直方图与修复族排序"
inherits: project
depends: [t0-sweep-forensics]
tags: [analysis, offline]
---

## 意图

把 T0 产出的 43 份 `triage.json` 聚成 blocker 直方图,按「一个修复能覆盖的未亮 app 数」给修复族排序,决定先做哪几族。这一步纯离线,不占板子;它是后续每个修复任务的开工门:没进排序表前两名的修复族不开工。

## 已定决策

- 归一化键:`native-symbol` 按缺失符号所属簇(如 `libandroid:AConfiguration_*`);`java-exception` 按异常类加最深一帧 `android.*` 框架方法;`null-service` 按服务名;`main-thread-blocked` 按主线程栈顶第一个框架方法
- 排序分等于该族覆盖的未亮 app 数;同分时先比技术栈种类数,再比是否有修法先例(telephony 桩、GLESv1_CM stub)
- 交叉引用 2026-09-28 的静态判别结果:`pm:call:resolveService`(24 未亮 / 0 亮)、`svc:download`(15/0)、`svc:account`(13/0)
- 产物 `benchmark/<date>-blocker-histogram/results.json`,每族列出 `apps`、`evidence_refs`、`proposed_fix`、`precedent`

## 边界

### 允许修改
- benchmark/*-blocker-histogram/**
- tools/spec-checks/**

### 禁止
- 不连接任何板子
- 不修改 T0 的原始 `triage.json`

## 验收标准

场景: 每个未亮 app 恰好归入一族
  测试: t1_every_blocked_app_in_one_family
  假设 T0 产出 43 份 `triage.json`
  当 生成直方图
  那么 43 个 app 每个恰好出现在 1 个族的 `apps` 列表里

场景: 排序表可复现
  测试: t1_ranking_is_deterministic
  假设 输入的 `triage.json` 集合不变
  当 连续生成两次 `results.json`
  那么 两次输出逐字节相同

场景: no-marker 单列不参与排序
  测试: t1_no_marker_listed_separately
  假设 某些 app 的 `first_blocker.class` 为 `no-marker`
  当 生成排序表
  那么 这些 app 列在 `unclassified` 下
  并且 `unclassified` 不占排序名次

场景: 同簇缺符号归为同一族
  测试: t1_symbol_cluster_normalization
  假设 app A 缺 `AConfiguration_new`,app B 缺 `AConfiguration_getDensity`
  当 按归一化键分族
  那么 A 与 B 落在同一个 `libandroid:AConfiguration_*` 族

场景: 证据引用可回溯
  测试: t1_evidence_refs_resolve
  层级: integration
  假设 某族的 `evidence_refs` 指向 T0 的证据文件
  当 逐条检查引用路径
  那么 每条路径都存在且包含被引用的原文行

场景: triage 记录缺失或损坏时拒绝出表
  测试: t1_rejects_missing_or_malformed_triage
  假设 43 份 `triage.json` 中有 1 份缺失或不是合法 JSON
  当 生成直方图
  那么 生成器以非零状态退出并打印该 app 名
  并且 不写出 `results.json`

## 排除范围

- 实施任何修复
- 按商业价值或知名度给修复族加权
