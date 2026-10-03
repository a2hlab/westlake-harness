spec: task
name: "T3 fd-breezyweather: onStart/onResume 在 launch 事务内同步推进"
inherits: project
tags: [runtime, lifecycle, regression-guarded]
depends: []
---

## 意图

fd-breezyweather 死于 `lateinit property weatherView has not been initialized`(u16-unowned-diag 新簇 async-lifecycle-ordering):route-A 的 OH_LifecycleAdapter 把 FOREGROUND→RESUMED 作为 POSTED Looper 消息在 onCreate 返回后才派发,而 app 在 onCreate 里 post 的 runnable(b14)先跑,读到尚未被 onCreateView 赋值的 weatherView。AOSP 的 handleLaunchActivity 同步跑 onCreate→onStart→onResume,executePendingTransactions(→Fragment.onCreateView)先于 b14。本任务在 runtime JAR 的 lifecycle 适配里把 onStart/onResume(含 executePendingTransactions)放进 launch 事务内同步推进。

来源:benchmark/2026-10-03-u16-unowned-diag/results.json(fd-breezyweather;minimal_fix 已写同步推进)。

## 已定决策

- 改动在 U16 runtime JAR 的新文件里(新修新文件);不动 U15 已冻结的 lifecycle 相关文件。
- **带回退防护**:launch 事务内同步回调改变了所有 app 都走的时序——U16 窗口必须含全部 126 个参考亮键的回归观察(lit-regression 分片),任一亮键翻暗即回退本修。
- 预期收益:fd-breezyweather 首墙移走(预计移 1);weatherView 在 b14 前被赋值,app 进主界面。
- 观察点:fd-breezyweather 进 U16 键表 movers(来源=本任务/新簇);check_fix_observers 的 runtime JAR token/SHA 命中。

## 边界

### 允许修改
- benchmark/2026-10-03-u16-t3-lifecycle-sync/**
- runtime JAR 新增 lifecycle 同步推进文件
- tools/spec-checks/tests/u16_t3_lifecycle.rs

### 禁止
- 不改 onCreate 本身的派发时序
- 不动 OH 侧 AbilityLifecycle 语义(只改适配层的 Java 派发顺序)

## 验收标准

场景: onStart/onResume 同步推进
  测试: u16_t3_sync_dispatch
  假设 新 runtime JAR 的 lifecycle 适配类反编译(baksmali)
  当 读 launch 事务方法
  那么 onStart 与 onResume 调用位于 handleLaunch 等价路径内、executePendingTransactions 之后、返回之前
  并且 无新起 Handler post 包裹这两个回调

场景: breezyweather 首墙移动且无回归
  测试: u16_t3_moves_and_no_regression
  假设 U16 窗口跑 fd-breezyweather 1 次 + 全部 126 参考亮键各 1 次
  当 first_fatal.py 与 pair_sheet 汇总
  那么 fd-breezyweather 不再是 weatherView lateinit UninitializedPropertyAccessException
  并且 126 个亮键 auto=same 或外环逐张确认(审核: human)且无一翻暗

## 排除范围

- 不重写整个 lifecycle 状态机;只改 launch 事务内这一段时序。
