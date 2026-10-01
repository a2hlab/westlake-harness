spec: task
name: "Route eleven U8 deaths to source-backed repairs"
inherits: project
---

## 意图

Convert the eleven adopted termination chains into actionable J/native repair proposals. Preserve unknown SIGKILL senders and distinguish a preceding loader error from a proven exit cause.

## 已定决策

- Emit eleven unique JSON rows with layer, wall, repair, source coordinates and beneficiary counts.
- Pin selected AOSP source files against SHA256SUMS and deployed JNI owners against artifact_identity.
- Reject J-only Surface and global Boolean/Cursor defaults; require actual native buffer ownership and application/provider initialization.

## 边界

### 允许修改
- benchmark/2026-10-01-u8-death-clusters/no-fatal-fixplan*
- benchmark/2026-10-01-u8-death-clusters/no-fatal-fixplan-evidence/**
- benchmark/2026-10-01-u8-death-clusters/no-fatal-fixplan-tests/**
- specs/u8-no-fatal-fixplan/**
- tools/spec-checks/tests/u8_no_fatal_fixplan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Eleven keys have source backed repair routes
  测试: u8_fixplan_report
  假设 The signed termination audit and source evidence
  当 The repair JSON and Markdown are replayed
  那么 Eleven unique rows have explicit layers, source lines and beneficiary sets

场景: Source identity mismatch is rejected
  测试: u8_fixplan_sources
  假设 Pinned source snippets and deployed artifact identities
  当 Source hashes or coordinates are mutated
  那么 Validation rejects mismatches rather than attributing donors to deployed code

场景: Unproven causes and false J defaults are rejected
  测试: u8_fixplan_uncertainty
  假设 SIGKILL, loader errors and native lockCanvas evidence
  当 Repair routes and acceptance probes are checked
  那么 SIGKILL sender remains unknown, native ownership is preserved and no lit gain is asserted

## 排除范围

- Implementing the proposed J/native patches, opening windows or revising frozen U8 scoring.
