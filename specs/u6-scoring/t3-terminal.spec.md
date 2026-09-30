spec: task
name: "Termination-first causal triage"
inherits: project
depends: [t2-score]
---

## 意图

Implement scripts/lab/first_fatal.py for an app run directory: identify target-process termination first, then trace its exception chain or crash-thread stack, never promote the earliest error to a fatal cause.

## 已定决策

- App PID comes from record, package launch binding and UID-matched process snapshots, never a compositor PID or timestamp column.
- Detect main_threw, FATAL EXCEPTION, invoked uncaught handler, System.exit, fatal signals and confirmed process disappearance. Signals 42, 35 and 4 are nonterminal diagnostics.
- Java roots follow Caused by or the same-TID immediately preceding exception block; signal roots use PID-bound cppcrash fault-thread frames.
- Noise only trims displayed context; terminal detection and causal chains retain raw evidence.
- Missing crash stack or ambiguous exception linkage remains unknown; output is causal evidence for review, not automatic UI or score.

## 边界

### 允许修改
- scripts/lab/first_fatal.py
- benchmark/2026-10-01-u6-scoring/**
- specs/u6-scoring/**
- tools/spec-checks/tests/u6_scoring.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Five known terminal causes replay from pinned excerpts
  测试: u6_scoring_first_fatal_answers
  假设 N5 LocalSend J6 reader T7c Wikipedia merged BurgerKing and McDonalds evidence
  当 Termination is selected before backward causal tracing
  那么 Causes identify ANativeWindow_getFormat getVibratorIds tagsoup ICCE libz.so and SplashActivity main_threw respectively

场景: Earlier warnings and diagnostic signals cannot become a fatal wall
  测试: u6_scoring_first_fatal_boundaries
  假设 Earlier SDK exceptions foreign PID crashes debug signals noise and missing terminal evidence
  当 Terminal-first triage runs with process and faultlog evidence
  那么 Signals 42 35 4 and caught SDK errors are not terminals while missing roots remain unknown and real terminal evidence is never suppressed

## 排除范围

- Diagnosing memory corruption or changing deployed runtime binaries.
