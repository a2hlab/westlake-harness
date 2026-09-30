spec: task
name: "Bind U6 candidates and rescan merged inputs"
inherits: project
---

## 意图

Collect exact candidate identities, enumerate their repaired APIs, rescan all DEX and native members of five merged APKs, and verify the three repaired input problems without touching source inputs.

## 已定决策

- Reuse U5 static rules, not the obsolete split flags; record fresh APK and library hashes.
- Verify repaired fd-seal and toutiao inventory and bind Subway to the merged APK rather than the intermediate base re-pin.
- Record T7c and J7b separately; receipt comparisons against B5 do not establish the J6 to J7b delta.

## 边界

### 允许修改
- benchmark/2026-10-01-u6-prospective/**
- specs/u6-prospective/**
- tools/spec-checks/tests/u6_prospective.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Fresh merged inputs replace obsolete input blockers
  测试: u6_input_identity
  假设 Five merged APKs and two repaired sidecar inventories are available
  当 Their pinned static facts are validated
  那么 All five APK identities change all DEX members are scanned native requirements survive and three old input categories clear only for exact repaired identities

场景: Candidate API claims bind actual artifacts
  测试: u6_candidate_identity
  假设 T7c image stubs and J7b artifacts have SHA-bound evidence
  当 The candidate manifest is checked
  那么 The manifest contains all 27 image files and two jar hashes and rejects a different T7d or native generation as an equivalent candidate

## 排除范围

- Input repairs, native fixes, building or deploying U6, treating pretest survival as UI review.

