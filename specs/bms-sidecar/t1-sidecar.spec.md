spec: task
name: "Install verified native sidecars before desktop launch"
inherits: project
---

## 意图

Preserve the original Firefox APK while assembling its 18 arm64 shared libraries after BMS installation and before desktop launch.

## 已定决策

- Reuse master batch collection and B7BindFixes existing APK-adjacent arm64 lookup.
- Validate and hash all sidecar files before any device operation. Verify the installed original APK and staged/readback library hashes before launch.
- Mark Firefox sidecars required in the input manifest. Missing or partial inputs stop the app; other APKs without sidecars preserve current behavior.
- No split dex/resource merge is claimed. On-device effect remains pending until evidence is collected.

## 边界

### 允许修改
- benchmark/2026-09-28-bms-route-deploy/batch/**
- benchmark/2026-09-30-firefox-sidecar-installer/**
- specs/bms-sidecar/**
- tools/spec-checks/**
- scripts/lab/run_facts.py
- .octos/KNOWLEDGE-DIGEST.md
- README.md

### 禁止
- No runtime generation changes, external source/input edits or installer deployment.

## 验收标准

场景: 装配与拒绝坏输入
  测试: bms_native_sidecars
  层级: integration
  替身: FakeBoard
  假设 Original APK and arm64 shared-library sidecars are supplied
  当 FakeBoard performs the production collection path
  那么 Libraries land beside the verified installed APK before desktop launch
  并且 Missing files, wrong ELF architecture and hash mismatches prevent launch
  并且 Original APK bytes and existing unrelated libraries are preserved

场景: 外环验证交接
  测试: bms_native_sidecar_receipt
  假设 Firefox input and r17a runtime evidence are available locally
  当 The offline handoff is emitted
  那么 All 18 libraries match the pinned input and split archive members
  并且 Screenshot and live-process counts remain unknown and board verification is assigned to the outer loop

## 排除范围

- Loading split resources/dex, fixing Firefox runtime behavior, and replacing installer or runtime libraries on devices.
