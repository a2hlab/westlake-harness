spec: task
name: "Scan seven WebView apps and freeze provider-only impact"
inherits: project
---

## 意图

Find exact constructor, settings and content consumers, XML inflation and lifecycle witnesses, and publish startup versus later-page predictions for seven APKs.

## 已定决策

- Reuse hash-admitted 166-cohort input discovery and bounded inherited lifecycle graph from B10 without editing it.
- Include layout-inflated WebViews, subclass calls and Fragment callbacks; unknown dispatch remains explicit.
- Separate provider checkpoint, next-wall prediction and visual outcome; no-op rendering is not functional lit.
- Pin the J8 source mechanism and the actual U8 J9 candidate that carries it.

## 边界

### 允许修改
- benchmark/2026-10-01-webview-startup-prediction/**
- specs/webview-startup/**
- tools/spec-checks/tests/webview_startup.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Drift is rejected and all seven identities remain distinct
  测试: webview_startup_identity
  假设 Changed APK bytes or incomplete keys
  当 The collector admits inputs and the prediction replays
  那么 Drift is rejected and exactly seven pinned rows are published

场景: Inflation and callback gaps never become false later-page proofs
  测试: webview_startup_scope
  假设 Subclass calls XML inflation inherited startup roots and unresolved Fragment callbacks
  当 Startup scope classification runs
  那么 Startup witnesses differ from later page and unknown callback candidates

场景: Provider-only repair does not promise rendered content
  测试: webview_startup_replay
  假设 A type-zero provider and calls requiring concrete WebSettings
  当 Machine-readable predictions replay
  那么 Provider checkpoint possible pass remains distinct from settings null and functional UI unknown

## 排除范围

- U8 scoring until complete results and outer screenshot signoff exist.
- Runtime repairs, actual Chromium integration, dynamic execution proof and device writes.
