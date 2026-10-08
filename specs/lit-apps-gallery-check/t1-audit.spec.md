spec: task
name: "Mechanically reconcile lit gallery objects and captions"
inherits: project
---

## 意图

Audit selected screenshot ownership and signed-run membership, exact metadata fields, 129-key coverage, HTML counts and all PPT card name-purpose pairs without visual judgment.

## 已定决策

- Screenshot ownership requires matching directory, record key/package and exact signed pair/reference path.
- Compare metadata as exact strings and distinguish deduplicated package coverage from requested key coverage.
- Read PPT with python-pptx and pair card name/purpose by text-box geometry, not an unordered bag of words.

## 边界

### 允许修改
- benchmark/2026-10-08-lit-apps-gallery-check/**
- specs/lit-apps-gallery-check/**
- tools/spec-checks/tests/lit_apps_gallery_check.rs

## 验收标准

场景: Wrong objects and unsigned paths remain findings
  测试: lit_apps_gallery_auditor
  假设 A screenshot directory or record identity conflicts with its gallery key
  当 The ownership verifier runs
  那么 It emits a wrong-object finding rather than substituting another image

场景: Exact metadata and key coverage detect drift
  测试: lit_apps_gallery_auditor
  假设 A field changes or one duplicate-package key is omitted
  当 The metadata and coverage verifiers run
  那么 The changed field or missing key is recorded while distinct package counts remain separate

场景: Page card name and purpose stay paired
  测试: lit_apps_gallery_auditor
  假设 A PPT card has the right name but another card purpose
  当 Card pairs are compared with the gallery data
  那么 The swapped pair is rejected without interpreting screenshot pixels

## 排除范围

- Rendering or judging screenshots, editing reports, running on devices and declaring application functionality.
