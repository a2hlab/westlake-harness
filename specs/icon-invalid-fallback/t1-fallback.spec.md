spec: task
name: "Route invalid selected non-PNG rasters to the existing template placeholder"
inherits: project
---

## 意图

Deliver a minimal apk_installer.cpp patch with host tests that routes malformed selected non-PNG image bytes to the existing typed template-placeholder branch and logs the selected member and header failure reason.

## 已定决策

- Keep PNG handling unchanged; accept canonical bounded WebP and JPEG headers without adding image decoder dependencies.
- A readable selected raster with invalid headers bypasses the legacy filename fallback and uses a distinct DECLARED_INVALID_RASTER classification.
- Read failures and parse failures retain the existing fail-closed behavior; XML composition paths remain unchanged.
- Ship a source-hash-bound patch and tests, not a rebuilt or deployed native library.

## 边界

### 允许修改
- benchmark/2026-10-01-icon-invalid-fallback/**
- specs/icon-invalid-fallback/**
- tools/spec-checks/tests/icon_invalid_fallback.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Malformed selected non-PNG bytes use the existing placeholder
  测试: icon_invalid_fallback_routing
  假设 A readable malformed selected raster and an available legacy raster
  当 The patched production selection branch executes
  那么 Legacy lookup is bypassed and the template placeholder is read with DECLARED_INVALID_RASTER and a log containing member and reason

场景: Healthy rasters preserve their original bytes
  测试: icon_invalid_fallback_headers
  假设 PNG WebP and JPEG headers plus truncated and inconsistent non-PNG containers
  当 The patched header checker executes
  那么 Healthy rasters are retained and malformed non-PNG containers return bounded failure reasons

场景: Existing read failures keep their previous boundary
  测试: icon_invalid_fallback_routing
  假设 Unreadable selected members XML fallback and a failing placeholder read
  当 Selection and placeholder routing run
  那么 Existing legacy and fail-closed outcomes remain and an unreadable placeholder never becomes a successful carrier

场景: Patch and real selected WebP cohort remain identity bound
  测试: icon_invalid_fallback_replay
  假设 The pinned installer source and the 25 selected WebP-family APK members
  当 The patch is applied to scratch and original selected bytes are replayed
  那么 The patch applies to the pinned source and 24 canonical headers remain accepted while Frequent Habits is classified invalid

## 排除范围

- Full decoder validation, repairing upstream image bytes, native build or device UI signoff.
