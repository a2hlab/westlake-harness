spec: task
name: "Bounded content predictions and staged effort"
inherits: project
depends: [t1-evidence]
---

## 意图

Define real-content stages and measurable acceptance without promoting native controls or empty providers into browser success.

## 已定决策

- Count local asset content separately from remote navigation and WebRTC media functions.
- CanIWebView remains an already-lit negative control, not an extra newly lit key.
- Effort is a conditional round range; actual builds and device review are not performed here.

## 边界

### 允许修改
- benchmark/2026-10-03-webview-provider-plan/**
- specs/webview-provider-plan/**
- tools/spec-checks/tests/webview_provider_plan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Mere provider presence moves no content wall
  测试: webview_provider_plan_phases
  假设 Six keys share an empty WebView provider
  当 The prerequisite stage is scored
  那么 First-fatal and content movement are both zero

场景: Local and network stages do not double count
  测试: webview_provider_plan_phases
  假设 Four blank keys have local assets and one needs a remote page
  当 Conditional renderer predictions are emitted
  那么 Local stage targets four and network stage adds one with union five

场景: Native controls do not certify browser pixels
  测试: webview_provider_plan_phases
  假设 CanIWebView is already signed lit with blank browser content
  当 Predictions and acceptance are recorded
  那么 No extra lit gain is counted and visible DOM plus JavaScript remain required

## 排除范围

- Frozen deployment predictions or claims that camera, GPU services or t20 already work.
