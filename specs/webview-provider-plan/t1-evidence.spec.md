spec: task
name: "Provider donors and exact cache chain"
inherits: project
---

## 意图

Trace the available real renderer methods and the deployed fallback cache before proposing phased work.

## 已定决策

- Inspect effective runtime 5ae3 and boot framework 3e10, not stale same-name JARs.
- Preserve AOSP14 update-service process selection separately from newer Flags-based gap classification.
- Missing historical raw results remain missing rather than inheriting a PASS claim.

## 边界

### 允许修改
- benchmark/2026-10-03-webview-provider-plan/**
- specs/webview-provider-plan/**
- tools/spec-checks/tests/webview_provider_plan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Exact caches and process selection are preserved
  测试: webview_provider_plan_evidence
  假设 Cached fallback providers precede WebView construction
  当 Deployed DEX and local AOSP14 sources are collected
  那么 Both proxy seeders and the update-service multiprocess call are retained

场景: Available APK is not a deployed renderer
  测试: webview_provider_plan_evidence
  假设 A local provider APK and ELF exist outside the bundle
  当 Dependency and donor evidence is inventoried
  那么 APK hashes and NEEDED edges are pinned and namespace availability stays unproved

## 排除范围

- Provider installation, compilation and runtime probes.
