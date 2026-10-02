spec: task
name: "Publish resident owners before native namespace loads"
inherits: project
depends:
  - t1-baseline.spec.md
---

## 意图

Build the approved host-side namespace-sharing experiment without duplicating runtime owners or replacing r3 permissions.

## 已定决策

- Bridge and app owner publication precedes fresh loads; original private owner permissions merge into their single sealed edge.
- Ordinary compat from the same sealed parent merges into that same edge; verified default compat retains its separate original edge.
- Exact paths use sealed NOLOAD handles, aliases and missing owners reject, non-owner requests retain the old callback.
- Static may-path findings are compared individually with r3, not silently waived as runtime safety.

## 边界

### 允许修改
- benchmark/2026-10-02-n11h-host-owner/**
- specs/n11h-host-owner/**
- tools/spec-checks/tests/n11h_host_owner.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Original permissions survive once-only owner publication
  测试: n11h_namespace
  假设 The actual candidate callbacks and OH-style replacement inheritance semantics
  当 Ordinary, native-private and Flutter domains plus sealed/default compat choices replay
  那么 Both owner edges precede fresh loads, original paths and permissions survive, and no parent edge is inherited twice

场景: Protected paths do not create fresh owners
  测试: n11h_open
  假设 Two canonical owners, absent namespace or handles, aliases and non-owner requests
  当 The actual StockOpenNamespace callback executes
  那么 Only canonical owners return sealed NOLOAD handles, failure rejects without fallback, and non-owner routing and guards remain intact

场景: Final artifact audits retain all unapproved findings
  测试: n11h_artifact
  假设 Byte-reproduced r3, two identical candidates and explicit package checks
  当 Open-site, strings, ABI/calls/consumer and N1/N2 run offline
  那么 Inherit-repeat is zero, r3 after-open changes are enumerated, structural identity survives and unapproved findings remain blockers

## 排除范围

- No dynamic single-owner, white-window, t20 or screenshot acceptance.
- No self-approved exception or executable window.
