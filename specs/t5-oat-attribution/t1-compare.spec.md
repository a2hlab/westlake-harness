spec: task
name: Attribute T5 OAT key-value and checksum differences
inherits: project
---
## 意图
Audit the premise that the R155 reference contains missing bootclasspath-checksums metadata. Compare available T5 OAT headers, key-value stores and data/code sections and report whether differences are confined to metadata.
## 已定决策
- Pin all input hashes against the board reference manifest; parse bounded ELF/OAT structures, not strings grep.
- Produce machine-readable per-segment comparisons and source/file-offset citations. Never alter input binaries or add speculative metadata.
- If remote T5 bytes are unavailable, record the missing-input boundary and provide a runnable comparison command; do not fabricate a checksum attribution.
- Audit observable R155 build switches against native instruction evidence and source. Emit T3b environment settings and a separate T4 contract recommendation; unknown switches stay unknown.
## 边界
### 允许修改
- benchmark/2026-09-30-t5-oat-attribution/**
- specs/t5-oat-attribution/**
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### 禁止
- No board commands or edits to reference/T5 artifacts, shared remote source trees, prior contracts or runtime implementations.
## 验收标准
场景: 精确键值与分区证据
  测试: t5_oat_evidence
  假设 SHA-pinned ELF OAT 230 artifacts are available
  当 The analyzer extracts bounded header and key-value data
  那么 Every reported key and section has a byte offset and SHA provenance
  并且 The comparison separates header, metadata, read-only data and executable differences
场景: 错输入与缺证据拒绝
  测试: t5_oat_rejection
  假设 An input has an incorrect SHA or malformed offsets or a missing candidate
  当 The analyzer checks the input
  那么 Corrupt input is rejected and missing evidence never becomes an equal or successful verdict
场景: 编译开关与不可判定项
  测试: t5_art_flags
  假设 The SHA-pinned R155 libart and local r1 source are available
  当 The audit attributes build switches to exact instructions and source lines
  那么 Verified switches have binary evidence and recommended environment values
  并且 Unrecoverable build options remain unknown rather than inheriting an upstream default
## 排除范围
- L2 board validation, image rebuilding without proven need, or changing frozen runtime code.
