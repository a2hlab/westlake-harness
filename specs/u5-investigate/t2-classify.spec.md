spec: task
name: "Classify evidence into five conservative candidate families"
inherits: project
depends: [t1-evidence]
---

## 意图

Publish per-app last logs, Java main-thread observations, caught exceptions and window/frame evidence. Separate five requested categories and propose evidence-bound scanner or runtime repair candidates.

## 已定决策

- Exception class linking, JNI registration and ability first-frame callbacks are not exception execution or buffer submission.
- Keep network, permission/dialog, window-without-frame, caught-exception and other buckets, including zero-evidence buckets.
- Candidate explanations are not proven causes or prospective prediction accuracy.

## 边界

### 允许修改
- benchmark/2026-10-01-u5-investigate/**
- specs/u5-investigate/**
- tools/spec-checks/tests/u5_investigate.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Five candidate categories require positive evidence
  测试: investigate_categories
  假设 Synthetic network dialog frame and caught-exception evidence
  当 Conservative candidate rules run
  那么 The five buckets are exercised while absent evidence stays other

场景: Foreign compositor class-link and callback markers cannot prove a frame
  测试: investigate_false_markers
  假设 Foreign render logs JNI registrations and first-frame lifecycle callbacks
  当 Rules are replayed against these negative controls and the selected real evidence
  那么 No lighting verdict or successful buffer submission is inferred from these markers

## 排除范围

- Runtime changes, forcibly filling every category, claiming causal proof from an alive process.
