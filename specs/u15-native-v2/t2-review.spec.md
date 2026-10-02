spec: task
name: "Review all U15 native deltas without approval"
inherits: project
depends: ["t1-compose.spec.md"]
---

## 意图

Record fresh open-site, namespace, strings, ABI/calls and consumer reports against pinned U14 content, N1/N2 previews and a single unsigned strings review table.

## 已定决策

- Keep all tool exit codes and original output hashes; unbound existing exceptions are preview only.
- Flutter adds exactly three ATrace exports and resolves its three direct imports through the existing runtime NEEDED edge.
- Strings review includes runtime, host, ANL and Flutter changes with source reasons; no allow row is applied by this lane.
- Static accessibility and modeled first-wall movement are not screenshot or production evidence.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-native-v2/**
- specs/u15-native-v2/**
- tools/spec-checks/tests/u15_native_v2.rs

## 验收标准

场景: Fresh reports and source-bound review preserve refusals
  测试: u15_native_v2_review
  假设 Four objects and 219 consumer identities are pinned locally
  当 Offline static reports and the strings table are checked
  那么 Raw refusals and per-object deltas are retained without applying exceptions

场景: Approval or historical production substitution is rejected
  测试: u15_native_v2_review
  假设 The complete new BCP pair and final transaction binding are still absent
  当 A report claims applied approvals or production execution
  那么 Validation rejects the claim while all active gate files remain unchanged

场景: Flutter ATrace uses the existing resident dependency
  测试: u15_native_v2_review
  假设 Flutter9b824 replaces only the private fff9 owner
  当 ABI dynamic symbols imports and NEEDED reports are compared
  那么 Exactly three ATrace exports are added and three runtime imports bind through the unchanged dependency list with no new open site

## 排除范围

- Execute production replay, approve any finding or write knowledge/gates.
