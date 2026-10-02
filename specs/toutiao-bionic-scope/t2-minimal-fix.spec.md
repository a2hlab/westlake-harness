spec: task
name: "Offline export and resident-scope candidate evidence"
inherits: project
depends: [t1-symbols]
---

## 意图

Provide the minimal source repair and static comparison against actual deployed bytes, keeping unresolved runtime behavior and owner admission pending.

## 已定决策

- Preserve the complete old compat export set and real implementations; add only missing errno and cmsg exports.
- An inheritance whitelist alone is not relocation search membership; inspect the pinned OH loader's local/global and direct-parent paths.
- Any resident promotion queries only the sealed owner using NOLOAD and never opens a new app/default copy.

## 边界

### 允许修改
- benchmark/2026-10-02-toutiao-bionic-scope/**
- tools/spec-checks/tests/toutiao_bionic_scope.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Candidate exports retain old owners and exact static deltas
  测试: toutiao_bionic_candidate
  假设 Pinned deployed bytes and the frozen build recipe
  当 Offline candidates are built and open-site and string diffs run
  那么 Existing exports remain and raw findings are retained without asserting dynamic consumer success

场景: Namespace source evidence does not authorize an extra owner or repeated edge
  测试: toutiao_bionic_namespace
  假设 The r3 host and namespace-aware OH6.1 loader source
  当 Permissions and relocation-search membership are compared
  那么 The proposed owner query is sealed NOLOAD only with no application-view query and no repeated inherit

## 排除范围

- No window approval or runtime proof from host mocks; deployed-string differences require explicit outer review.
