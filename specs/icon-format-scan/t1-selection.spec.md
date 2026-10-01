spec: task
name: "Resolve the exact manifest icon resource and classify its bytes"
inherits: project
---

## 意图

Reproduce ReadIconByManifest resource selection with the actual resolver source, including obfuscated paths, stable ties, sparse and offset16 entries, and classify selected bytes rather than unrelated APK members.

## 已定决策

- Read the application android:icon resource reference, never infer it from filenames or roundIcon.
- Compile the unchanged SHA-pinned resolver with a raw resources.arsc I/O shim; preserve stable first-candidate ties and XML penalty.
- Keep XML composition and later installer fallback outside the selected-file format label.
- Separate the WebP format family from RIFF-length/header validity; reversible UTF8-expanded bytes remain malformed, never repaired inputs.

## 边界

### 允许修改
- benchmark/2026-10-01-icon-format-scan/**
- specs/icon-format-scan/**
- tools/spec-checks/tests/icon_format_scan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Resource reference and file format use exact application evidence
  测试: icon_format_mapping
  假设 A manifest with distinct application and Activity icons and misleading filename extensions
  当 The application resource reference and selected bytes are read
  那么 Only application android:icon is selected and PNG WebP JPEG XML signatures determine format

场景: Resolver preserves obfuscated resource order and encodings
  测试: icon_format_selection
  假设 Dense sparse and offset16 resource variants including obfuscated WebP and XML
  当 The unchanged production resolver runs over exact resources.arsc bytes
  那么 Stable first raster wins equal scores and resource encoding variants resolve identically

场景: Input or source drift is refused
  测试: icon_format_mapping
  假设 An altered APK or resolver source hash
  当 Identity verification is requested
  那么 No changed artifact is scored as the pinned input

## 排除范围

- Fixing image decoding, APK resources or deployed installer behavior.
