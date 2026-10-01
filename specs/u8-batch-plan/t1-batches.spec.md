spec: task
name: "Publish donor-qualified N10 and J8 cluster list"
inherits: project
---

## 意图

Assign the accepted twenty-two U7 death clusters and thirty-two unlit keys to N10, J8 or deferred work, with pinned donor locations, evidence and conditional first-wall movement.

## 已定决策

- N10 includes N8 candidates, the two-bridge repair and native singleton candidates; J8 routes Java candidates and payload restoration.
- Split white-B into B1 and B2 without duplicating app membership; preserve the original cluster identifier.
- Record bounded searches in Westlake, 00.Workspace and real-work, including missing donors and their limits.
- Distinguish a validated function, observed bundle wall movement, related source and no donor; none may imply an already-built N10 or J8 repair.
- Mark draft-v1 superseded by outer ACK95 at 08:21; no prediction CSV or expected-run is frozen here.

## 边界

### 允许修改
- benchmark/2026-10-01-u8-prospective/**
- specs/u8-batch-plan/**
- tools/spec-checks/tests/u8_batches.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Donor ledger preserves searched source identities
  测试: u8_batches_donors
  假设 Accepted source candidates and three pinned donor trees
  当 The offline ledger is checked
  那么 Every selected donor has path commit hash and excerpt and every tree has bounded search receipts

场景: Batch coverage keeps movement conditional
  测试: u8_batches_coverage
  假设 Twenty-two accepted clusters and thirty-two signed unlit keys
  当 N10 J8 and deferred cluster rows are built
  那么 Each key appears once and source absence secondary exceptions and unresolved exits cannot become verified first-wall repairs

场景: Batch report is reproducible but not frozen
  测试: u8_batches_replay
  假设 Pinned evidence and a superseded narrow draft
  当 JSON and Markdown are regenerated
  那么 Checked artifacts match and the active index forbids using the old CSV as the U8 freeze

## 排除范围

- Editing prior selectors, authorizing exception grants or inventing missing implementations to fill the batch.
