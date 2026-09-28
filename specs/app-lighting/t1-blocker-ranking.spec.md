spec: task
name: "T1 blocker 直方图与修复族排序"
inherits: project
depends: [t0-sweep-forensics]
tags: [analysis, offline, critical-path]
---

## 意图

把 T0 产出的 43 份 `triage.json` 聚成 blocker 直方图,按「一个修复能覆盖的未亮 app 数」给修复族排序,决定先做哪几族。这一步纯离线,不占板子;它是后续修复任务的开工门:没进排序表前两名的修复族不开工。两个已批准的例外不受此门限制:T3(LocalSend 的 blocker 已具名)与 T4 的离线段;T4 的上板段仍受此门控制。

## 已定决策

- 分族只用 `candidate_blocker` 与 `confirmed`,不用 `observations` 里的背景噪声;归一化键:`native-symbol` 按缺失符号所属簇(如 `libandroid:AConfiguration_*`);`java-exception` 按异常类加最深一帧 `android.*` 框架方法;`null-service` 按服务名;`main-thread-blocked` 按主线程栈顶第一个非 `Looper`/`MessageQueue` 的框架方法
- 只剩 `MessageQueue.next`/`Looper.loop` 空等的主线程栈不构成一族,归入 `unclassified`
- 族内 app 必须共享同一失败调用;排序分等于该族覆盖的未亮 app 数,同分时依次比技术栈种类数、是否有修法先例(telephony 桩、GLESv1_CM stub)、族键字典序
- 静态判别结果 `pm:call:resolveService`(24 未亮 / 0 亮)、`svc:download`(15/0)、`svc:account`(13/0)只作线索;为它们各设一个最小动态探针(真实 service 返回值与调用后果),有动态证据前不计入任何族的覆盖数
- 产物 `benchmark/<date>-blocker-histogram/results.json`,每族列 `apps`、`evidence_refs`、`proposed_fix`、`precedent`;另列 `unclassified` 与 `static_leads`

## 边界

### 允许修改
- benchmark/*-blocker-histogram/**
- tools/spec-checks/**

### 禁止
- 不连接任何板子
- 不修改 T0 的原始 `triage.json`

## 验收标准

场景: 族与 unclassified 构成 43 个 app 的完整互斥分区
  测试: t1_partition_is_complete_and_disjoint
  假设 T0 产出 43 份 `triage.json`
  当 生成直方图
  那么 各族 `apps` 与 `unclassified` 的并集恰好是清单里的 43 个 key
  并且 任意两个集合没有交集

场景: 同簇缺符号归为同一族
  测试: t1_symbol_cluster_normalization
  假设 app A 缺 `AConfiguration_new`,app B 缺 `AConfiguration_getDensity`
  当 按归一化键分族
  那么 A 与 B 落在同一个 `libandroid:AConfiguration_*` 族

场景: Looper 空等不聚成一族
  测试: t1_looper_idle_not_a_family
  假设 5 个 app 的主线程栈都只剩 `MessageQueue.next` 空等
  当 生成排序表
  那么 这 5 个 app 全部列在 `unclassified`
  并且 排序表里没有以 `Looper` 或 `MessageQueue` 为键的族

场景: 输入顺序打乱结果不变,成员变化结果随之变化
  测试: t1_ranking_responds_to_membership
  假设 同一组 `triage.json` 以两种不同顺序输入,另一组把某族的一个 app 改到别的族
  当 分别生成 `results.json`
  那么 两种顺序的输出逐字节相同
  并且 改动成员后两族的计数与名次按新成员变化

场景: 同分时按固定规则决出名次
  测试: t1_tie_break_is_stable
  假设 两个族覆盖的 app 数相同
  当 生成排序表
  那么 名次按技术栈种类数、修法先例、族键字典序依次决出

场景: 静态线索没有动态证据时不计覆盖
  测试: t1_static_leads_need_dynamic_evidence
  假设 `pm:call:resolveService` 出现在 24 个未亮 app 的静态缺口里,但没有对应的动态探针结果
  当 生成排序表
  那么 它只列在 `static_leads`,不计入任何族的覆盖数

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
