spec: task
name: Repair three host input gates without weakening identity checks
inherits: project
---
## 意图
Resolve Seal and Toutiao's already approved data payloads at host preflight and explicitly reconcile the current Subway Surfers input. Publish J3-based J4/N3 expectations separately from historical predictions.
## 已定决策
- Reuse native-data-exceptions.json approved bundle/ABI/name/APK SHA/payload SHA/size entries; data exceptions must also match an embedded original APK member.
- Retain invalid-ELF, symlink, inventory, hash, staging and installed-file checks for all other inputs.
- Pin any verified input revision explicitly in apps.json and record its old identity; do not rewrite historical freezes or claim old observations cover new bytes.
- Base J3 lighting only on the outer signature; distinguish first walls, secondary failures and unknown causal links.
## 边界
### 允许修改
- benchmark/2026-09-28-bms-route-deploy/batch/**
- benchmark/2026-09-30-input-recovery/**
- benchmark/2026-09-30-round1-plan/j3-feedback/**
- specs/bms-input-recovery/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### 禁止
- No device commands, writes to input APKs/metadata, changed runtime binaries, or historical freeze edits.
## 验收标准
场景: 已批准精确数据按原字节装配
  测试: bms_input_exception_roundtrip
  假设 Approved exact ZIP-data and ARM32 payload fixtures match the original APK
  当 The production FakeBoard collection path executes
  那么 Payloads are preserved verbatim and hashes are checked before click
场景: 错误身份与未批准数据仍拒绝
  测试: bms_input_exception_rejection
  假设 A payload SHA, APK SHA, package, approval status, size or archive membership differs
  当 Offline preflight validates the candidate
  那么 Input is rejected before any board command
场景: 当前输入及J3预测交接
  测试: bms_input_recovery_receipt
  假设 Three local app inputs and signed J3 runs are available
  当 The offline receipt is validated
  那么 Three inputs have verified hashes or an explicit unresolved reason
  并且 J4 and N3 each list expected unlocked apps without claiming on-device success
## 排除范围
- Installing packages, loading ARM32 binaries in ARM64, changing signatures, and signing off screenshots.
