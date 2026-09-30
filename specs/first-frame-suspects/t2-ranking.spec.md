spec: task
name: "Rank N9 suspects and replay lit negative controls"
inherits: project
depends: [t1-observations]
---

## 意图

Publish an auditable N9 target list with deterministic suspicion components, all U6 keys and T7d attempts, and independently reported lit negative controls.

## 已定决策

- Keep visual labels separate from log-only scores so lit controls cannot be forced to pass by their labels.
- Only reviewed blank and nonterminal runs enter targets; desktop unknown and incomplete records remain explicit exclusions.
- Report false positives and non-discriminating features instead of fitting thresholds to guarantee control success.

## 边界

### 允许修改
- benchmark/2026-10-01-first-frame-suspects/**
- scripts/lab/scan_first_frame.py
- specs/first-frame-suspects/**
- tools/spec-checks/tests/first_frame.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Rule score is independent of the screenshot label
  测试: first_frame_rule
  假设 Equivalent log observations with blank lit and unknown labels
  当 Scores and target eligibility are evaluated
  那么 Log-only scores stay identical while target membership separately requires reviewed blank nonterminal evidence

场景: Retained evidence reproduces targets and negative controls
  测试: first_frame_replay
  假设 Pinned compact U6 and T7d observations and capture review receipts
  当 Offline JSON and Markdown reports are reproduced
  那么 Every U6 key and T7d attempt is retained with explicit control false positives coverage gaps and evidence lines

## 排除范围

- Freezing U8, U7 scoring before outer signoff, counting diagnostic nudge images as lit or changing existing gates.
