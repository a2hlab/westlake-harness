spec: task
name: "Extract all thirteen exact-add class contracts"
inherits: project
---

## 意图

Provide descriptors superclass interfaces complete DEX method signatures verified source commits and key predictions for NSD8 and trampoline5 against exact U14 JARs.

## 已定决策

- Use checked nonempty dexdump output across all DEX files; refuse duplicate descriptors.
- Compare source bytes against pinned git blobs and retain original per-class diffs.
- Distinguish linking or lifecycle improvements from terminal fatal and screenshot outcomes.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-outer-review-packet/**
- specs/u15-outer-review-packet/**
- tools/spec-checks/tests/u15_outer_review_packet.rs
- README.md

## 验收标准

场景: Thirteen additions have complete extraction and source provenance
  测试: u15_outer_classes
  假设 Exact U14 and U15 stubs and runtime JARs are pinned
  当 Every added descriptor is extracted and compared
  那么 Eight NSD and five trampoline classes have parent interfaces method signatures and matching source blobs without extra additions

场景: Invalid class extraction refuses and predictions do not imply lit
  测试: u15_outer_classes
  假设 Empty or duplicate DEX output or unknown future content is supplied
  当 Class parsing and public report checks run
  那么 Empty or duplicate inputs refuse and predictions remain offline conditional without point-light claims

## 排除范围

- Approve exact additions or change service implementations.
