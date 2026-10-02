spec: task
name: "PPSSPP dlext backend boundary"
inherits: project
depends: [t4-vlc]
---

## 意图

Audit PPSSPP's actual extension calls and distinguish the current relocation wall from an unimplemented real namespace/FD backend.

## 已定决策

- Existing exported android_dlopen_ext is not absent; actual app relocation still cannot see it.
- USE_NAMESPACE and USE_LIBRARY_FD cannot be replaced with ordinary dlopen.
- No new candidate is published without a verified Android-namespace-to-OH mapping and real FD-aware backend.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-ppsspp-dlext/**
- tools/spec-checks/tests/u12_ppsspp_dlext.rs

## 验收标准

场景: Actual namespace and library-FD flags remain faithfully refused without a backend
  测试: u12_ppsspp_dlext
  假设 Exact window5 app consumer, exported015aa wrapper and factory OH ELF
  当 Extension call sites and backend availability are checked
  那么 The current missing-symbol wall and future unsupported backend are separate and no false one-key movement is claimed

## 排除范围

- Source-unverified namespace casts, dropping extinfo flags and a device run.
