spec: task
name: "Lit application metadata and presentation recommendation"
inherits: project
---

## 意图

Produce apps.csv and apps.json for the 126 lit reference keys and three signed U14 window1 gains, with APK identity, localized names, categories and one Chinese purpose sentence per key.

## 已定决策

- The reference and signed gains define the exact key set, not record status or screenshot heuristics.
- Verify APK SHA and package against the selected run record, then use androguard to resolve application labels with Chinese resource priority.
- Prefer local F-Droid summary and description evidence for purpose text; explicitly mark uncertain fallback facts.
- Preserve CSV/JSON equivalence, portable paths and package deduplication without dropping requested rows.

## 边界

### 允许修改
- benchmark/2026-10-08-lit-apps-report/**
- specs/lit-apps-report/**
- tools/spec-checks/tests/lit_apps_report.rs

## 验收标准

场景: Signed scope and CSV JSON inventory are identical
  测试: lit_apps_report_inventory
  假设 The reference contains 126 lit keys and window1 signs three distinct gains
  当 The inventory is assembled
  那么 Both formats contain exactly the same 129 keys and count duplicate packages separately

场景: Verified APK identity and localized label provenance
  测试: lit_apps_report_inventory
  假设 Selected run records and local APK metadata are available
  当 Metadata is joined with each key
  那么 SHA and package conflicts reject and Chinese resource labels take priority with explicit fallback provenance

场景: Purpose claims stay evidence backed and offline
  测试: lit_apps_report_inventory
  假设 Local F-Droid evidence or an explicitly uncertain fallback accompanies every purpose sentence
  当 The report is validated
  那么 Every row has one Chinese purpose sentence category and cited evidence and missing support rejects

## 排除范围

- Choosing screenshots, designing a finished gallery or slides, asserting functional correctness, promotion and board operations.
