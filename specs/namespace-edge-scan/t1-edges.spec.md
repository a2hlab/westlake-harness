spec: task
name: "Expose namespace edges and detect repeated inheritance"
inherits: project
---

## 意图

Prevent namespace-inheritance regressions before a device window using deployed-byte static known answers.

## 已定决策

- Add namespace API edges to text and JSON without changing existing open-site records.
- Match namespace handles by literal names when available and scoped expressions otherwise.
- Use direct function control-flow reachability, not numeric PC ordering, for inherit-after-open findings.
- Expand inherit child parameters by one direct caller; do not claim whole-program resolution.

## 边界

### 允许修改
- scripts/lab/open_site_scan.py
- scripts/lab/tests/test_open_site_scan.py
- tools/spec-checks/tests/namespace_edge_scan.rs
- specs/namespace-edge-scan/**
- benchmark/2026-10-02-namespace-edge-scan/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Legacy open-site answers remain intact
  测试: namespace_edges_legacy
  假设 The original seven synthetic and deployed known-answer tests
  当 The extended scanner runs unchanged legacy cases
  那么 All seven cases pass without weakening their assertions

场景: Namespace APIs and spill reloads are exposed
  测试: namespace_edges_listing
  假设 U9 deployed host and the pinned67753f77 comparison build
  当 Namespace init/create/get/inherit/set and paired stack loads are scanned
  那么 U9 known PCs and literal names are listed and the mixed-register spill is a stack slot

场景: Repeated inheritance follows one direct caller
  测试: namespace_edges_repeat
  假设 Deployed U10 r2 host71901abc and accepted r3 host65cc3535
  当 Named namespaces and caller child arguments are normalized
  那么 r2 reports repeated inheritance across two functions while r3 does not

场景: After-open requires a reachable path
  测试: namespace_edges_flow
  假设 Conditional and unconditional branches plus U9 inherit PCs0xccd8 and0xccf0
  当 Namespace-matched opens are compared to later inheritance
  那么 Reachable positive controls report and unreachable numeric-order controls retain fields without findings

## 排除范围

- No device ownership, unique-provider, screenshot or deployment acceptance.
- No recursive or indirect-call namespace inference.
