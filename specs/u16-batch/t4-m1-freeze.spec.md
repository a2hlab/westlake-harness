spec: task
name: "T4 M1 拆文件进 U16 runtime + FZ-009 登记"
inherits: project
tags: [split, freeze, m1]
depends: []
---

## 意图

M1(白窗双桥修复)当前是单文件实现;按冻结规则『冻结前先把实现拆成只含这一项的独立文件』,本任务把 benchmark/2026-10-03-m1-split/ 的拆分落进 U16 runtime(一版 JAR 里),对三个代表 app 复验行为不变,然后登记 FZ-009(M1)。

来源:benchmark/2026-10-03-m1-split/(拆分产物与等价性证明)。

## 已定决策

- 拆分以 m1-split 的 split-equivalence 证明为据:方法体逐条等价(只允许类名/引用名不同);落地时不得顺带改行为。
- 复验选 3 个 M1 受益 app(从 m1-split 记录的受益键取),U16 窗口各跑 1 次,auto=same 或外环确认。
- FZ-009 登记条件:拆分文件就是 U16 部署件 + 3 app 复验无回退 + 126 亮键回归无暗(与 T3 的 lit-regression 分片共用)。
- 观察点:3 个复验 app 进 U16 键表 movers(来源=本任务/M1 split);check_fix_observers 命中 runtime JAR。

## 边界

### 允许修改
- benchmark/2026-10-03-u16-t4-m1-freeze/**
- runtime JAR 里 M1 的拆分文件(来自 m1-split)
- tools/spec-checks/tests/u16_t4_m1.rs

### 禁止
- 不改 M1 的任何方法行为(只拆文件)
- 不在复验失败时强登记 FZ-009

## 验收标准

场景: 拆分等价
  测试: u16_t4_split_equivalence
  假设 U16 runtime JAR 反编译出 M1 拆分文件
  当 与拆分前方法体逐条比对
  那么 指令级等价(类名/引用名差异除外,同 m1-split 的 compare 方式)

场景: 三 app 复验 + 回归
  测试: u16_t4_replay_and_regression
  假设 U16 窗口跑 3 个 M1 受益 app + 126 亮键
  当 pair_sheet 汇总
  那么 3 app auto=same(或外环确认,审核: human)且 126 亮键无一翻暗

场景: 三 app 任一未复现 → 不登记 FZ-009
  测试: u16_t4_no_registration_on_miss
  假设 复验中任一 M1 受益 app 未出现 [M1-COPY] 语义等价复现(auto 不同且外环判非 same)
  当 登记检查执行
  那么 登记失败:FZ-009 不登记(条件链在第一步即断并报错),该 app 的证据进 U16 复盘
  并且 拆分文件保留在分支待查,不并入部署件

场景: FZ-009 登记条件的优先级链
  测试: u16_t4_registration_precedence
  假设 三项条件(拆分文件即部署件 / 3 app 复现 / 126 亮键无暗)按序检查
  当 任意一项不满足
  那么 登记在最先不满足处停止并输出该项名,后续项不再评估
  并且 全部满足时输出三行 PASS 后才登记

## 排除范围

- 不含 M2/M3 的拆分(各自独立任务)。
