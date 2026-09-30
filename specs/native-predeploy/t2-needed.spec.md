spec: task
name: "Gate private namespace dependency closure"
inherits: project
depends: [t1-initialization]
---

## 意图

Reject private namespace libraries whose transitive DT_NEEDED cannot resolve through that same domain's declared search and permitted paths before deployment.

## 已定决策

- Read candidate ELF dynamic sections with readelf and construct the deployment path view from sealed package mounts.
- Traverse dependencies in the originating namespace; neither global filename matches nor inherit edges satisfy closure.
- Require coverage for packaged private directories, retain unresolved effective paths as blockers, and preserve exact source/config/artifact identities.
- Replay the current package and retain the Flutter libandroid to liboh_android_runtime missing edge; hand the API and hook placement to cx-t0.

## 边界

### 允许修改
- scripts/lab/native_*.py
- benchmark/2026-10-01-native-predeploy-gates/**
- specs/native-predeploy/**
- tools/spec-checks/tests/native_predeploy.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md

### 禁止
- No inherit fallback, hardcoded package-specific verdict, frozen-evidence rewrite or device write.

## 验收标准

场景: Closure stays within one namespace
  测试: native_predeploy_needed
  假设 ELF dependency graphs include nested needs cycles and same-name libraries in other domains
  当 The gate resolves through declared search and permitted paths
  那么 Only same-domain resolutions pass and missing or inherited-only targets reject

场景: Current package exposes the real Flutter wall
  测试: native_predeploy_replay
  假设 SHA-bound readelf outputs and domain source evidence describe the current N4-order package
  当 The replay follows the Flutter private libandroid dependency
  那么 liboh_android_runtime is reported missing despite its presence outside that namespace

场景: Incomplete ELF or domain inputs never pass
  测试: native_predeploy_fail_closed
  假设 A package or configuration omits a private directory or has invalid ELF metadata
  当 The gate validates coverage and reader results
  那么 Missing coverage malformed input tool failure and escaping paths reject

## 排除范围

- Symbol-version resolution, general dynamic loader emulation, APK runtime domains not represented by build inputs, and deploy_generation edits owned by cx-t0.
