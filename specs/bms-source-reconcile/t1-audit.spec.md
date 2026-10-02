spec: task
name: "Reconcile 26 branch source residues"
inherits: project
---

## 意图

For each of 22 bms-deploy and four b4 branch residues, determine the actual U10.1T8 build source, with deployed-byte identity and object or source receipt evidence.

## 已定决策

- List all 26 branch entries and 23 unique paths, including three duplicate-version conflicts.
- Runtime selection follows the N10b smoke-marker object receipt and authenticated N2 sources.
- Source landing is a separate explicitly enumerated operation; report-only preflight cannot authorize unsupported bms/src copies.

## 边界

### 允许修改
- benchmark/2026-10-02-bms-source-reconcile/**
- tools/spec-checks/tests/bms_source_reconcile.rs

## 验收标准

场景: Branch residues receive explicit deployment decisions
  测试: bms_source_reconcile
  假设 A pinned master and two lane branch inventories with 26 entries
  当 Deployed hashes and build source/object receipts are reconciled
  那么 All 26 entries carry a decision and evidence, with no unknown row in the source landing list

场景: Same-name conflicts do not select the newest source by guess
  测试: bms_source_reconcile
  假设 Different hwui, app-native-loader and loader-test versions on two branches
  当 The deployed hwui provenance, N3 loader and existing policy source are checked
  那么 hwui and unmatched tests remain unlanded, the loader uses its authenticated N3 snapshot, and the master policy source is retained rather than the b4 fallback version

场景: Cached runtime objects and source landing remain independently auditable
  测试: bms_source_reconcile
  假设 N10b candidate and repeat object sets and exact source snapshot hashes
  当 The admitted source selection and build operation counters are checked
  那么 Selected runtime objects match the receipt and all selected snapshots match their hashes while build and device operation counts remain zero

## 排除范围

- Rebuilding any ELF, recreating unknown hwui or bridge provenance, deploying or replacing current generation bundles.
