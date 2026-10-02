spec: task
name: "M2 empty provider versus HTML compat"
inherits: project
---

## 意图

Identify the deployed WebView route for five white or black keys and the sole lit full-WebView control, and separate a renderer repair from the paused Html.fromHtml shim.

## 已定决策

- Keep unique app-PID Java stderr provider markers.
- Bind the effective runtime jar rather than the stale same-named native payload jar.
- Report zero unconditional first-fatal moves and a conditional five-key content-wall upper bound.

## 边界

### 允许修改
- benchmark/2026-10-02-white-m2-webview/**
- tools/spec-checks/tests/white_m2_webview.rs

## 验收标准

场景: All six keys use the same empty provider
  测试: white_m2_webview
  假设 Six app-PID timelines and signed screenshots bound to deployed runtime fingerprints
  当 Provider, HTML loading and renderer availability markers are compared
  那么 Six keys report no ASX_WEBVIEW_APK, the same proxy route and failed HTML compat loading while the control remains signed lit

场景: Renderer predictions cannot be confused with fatal-point or HTML fixes
  测试: white_m2_webview
  假设 Five living white or black windows and one lit native-control screen
  当 The renderer prerequisite and paused Html.fromHtml branch are evaluated
  那么 First-fatal movement and HTML-restoration movement remain zero and the renderer content-wall upper bound is conditional five

## 排除范围

- New runtime patches, renderer builds, board windows and changes to the signed verdicts.
