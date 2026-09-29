spec: task
name: "#77 Seal native payload and X/Toutiao manifest capacity"
inherits: project
tags: [bms, offline, cx-bms]
---

## 意图

Find the exact installation predicates behind Seal ec=8519936 and X/Toutiao -2005, compare verified prior routes, and deliver offline-tested candidate patches with app impact evidence. User #77 supersedes the installer exclusion in B10; device validation remains separately assigned.

## 已定决策

- Pin APK hashes to the B4 records and inspect real ZIP payloads, not filenames alone.
- Reuse the existing real-work/repository 1 MiB manifest capacity when it fits measured JSON.
- Preserve native extraction path, length, CRC, ownership and mode checks; explicitly describe any data-payload exception candidate.
- Give source file/line references, before/after offline results, implementation provenance, and unresolved device conditions.

## 边界

### 允许修改
- benchmark/2026-09-29-install-walls/**
- specs/bms-install-walls/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No modification to APK inputs or read-only source trees.
- No board operation, deployment, complete runtime rebuild, or git commit/push.

## 验收标准

场景: 三个输入与已有错误证据吻合
  测试: b77_pinned_inputs_and_causes
  假设 Mac APK copies and B3/B4 logs are available
  当 The offline scanner verifies SHA-256 and original error predicates
  那么 All three input hashes match the original records
  并且 Each failure has a file and line reference and a concrete trigger

场景: 补丁保持提取校验并通过正反例
  测试: b77_candidate_patch_regressions
  假设 Candidate changes are applied to temporary source copies only
  当 Host checks exercise real Seal payloads and rejected malformed inputs
  那么 Seal packaged data receives an explicit bounded disposition
  并且 Invalid payloads and manifest output beyond the new capacity still fail

场景: 影响表与前人路线可复核
  测试: b77_impact_and_provenance
  假设 Other locally available APKs are scanned with the same predicates
  当 The report is generated
  那么 A machine-readable impact list distinguishes measured input failures from unverified installation success
  并且 Westlake and original BMS source provenance is recorded without claiming past staging was a BMS APK installation

## 排除范围

- On-board success, screenshots, foundation/installd restart, and deployment scheduling.
- Changes to app code, signatures or APK package contents.
