spec: task
name: "Add ABI-limited GNU strerror and Android dlopen entries"
inherits: project
---

## 意图

Build the first U10 compat revision from verified historical inputs. Add GNU strerror buffer semantics and transparent Android loader dispatch while retaining the original abort implementation. The outer-approved partial scope explicitly leaves PPSSPP namespace loading unimplemented.

## 已定决策

- Snapshot and hash-check thirty compat input files and the adopted build receipt.
- Add only android_dlopen_ext and __gnu_strerror_r; android_set_abort_message already exists and remains unchanged.
- Dispatch to a real __loader_android_dlopen_ext backend when present; absent backend supports ordinary zero-extension flags only and rejects other flags.
- Require zero removed exports, signature drift, consumer breaks and common-function call differences; gate JSON fields, not merely abi_diff exit status.

## 边界

### 允许修改
- benchmark/2026-10-01-u10-native-shims/**
- specs/u10-native-shims/**
- tools/spec-checks/tests/u10_native_shims.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Source identity and ABI gates replay
  测试: u10_shim_evidence
  假设 Thirty pinned baseline sources and deployed aa7e77f943ab
  当 Baseline and candidate reports are checked
  那么 All source hashes match, only two expected exports are added and common calls and consumer breaks are zero

场景: GNU strerror and real abort preserve state
  测试: u10_shim_behavior
  假设 Host executable fixtures for GNU buffer return and abort message ownership
  当 Known, unknown, truncated and zero-length errors and repeated abort messages execute
  那么 Buffer pointer and errno are preserved and first abort message wins without duplicate state

场景: Missing loader backend fails closed
  测试: u10_shim_loader
  假设 No Android loader backend and the PPSSPP 0x200 and 0x210 extinfo calls
  当 android_dlopen_ext handles supported ordinary and unsupported namespace paths
  那么 Ordinary loading is real, unsupported flags fail explicitly without calling dlopen, and PPSSPP is not reported fixed

场景: Real backend retains caller and extinfo
  测试: u10_shim_loader
  假设 A supplied Android loader backend fixture
  当 The wrapper receives nonzero extension flags
  那么 The exact filename, flags, extinfo and original caller address reach that backend

## 排除范围

- Implementing Bionic namespace objects, new OH namespace policies, fixing PPSSPP namespace/force-load semantics, claiming Meet visibility or Mozilla SIGKILL cures.
