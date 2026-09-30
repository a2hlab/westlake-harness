spec: task
name: "Prepare evidence-bound three-axis scorer"
inherits: project
depends: [t1-noise]
---

## 意图

Replay the U5 run directory as a structural sample and prepare independent U6 first-wall, checkpoint and t20 scoring using the unchanged frozen scorer.

## 已定决策

- Check indexed record hashes, first clicked attempt, APK and sidecars, runtime and boot file inventories, PID bindings, log hash and image hash.
- Noise-subtracted candidates require reviewed causal evidence; error occurrence alone is never an automatic wall.
- Missing, mismatched or flaky observations stay unknown; positive checkpoint execution is not inferred from absent errors or UI.
- Require explicit outer review tied to the prepared evidence digest before actual scoring.

## 边界

### 允许修改
- benchmark/2026-10-01-u6-scoring/**
- specs/u6-scoring/**
- tools/spec-checks/tests/u6_scoring.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Indexed run structure is checked fail closed
  测试: u6_scoring_intake
  假设 A first-attempt indexed run and tampered hash duplicate key retry and changed input variants
  当 Preparation parses records logs inventories and captures
  那么 Valid structure yields review evidence while integrity errors reject and input mismatch remains non-comparable

场景: Independent axes require their own reviewed evidence
  测试: u6_scoring_axes
  假设 Reviewed positive conflicting missing and flaky observations
  当 The immutable frozen scorer is called after review gates
  那么 First wall checkpoints and t20 remain independent and rehearsal or unsigned results cannot be scored as U6

## 排除范围

- Manufacturing U6 observations before the full run and outer screenshot review.
