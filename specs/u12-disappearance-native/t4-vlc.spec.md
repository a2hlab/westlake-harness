spec: task
name: "VLC bionic residue adapter"
inherits: project
depends: [t3-scope]
---

## 意图

Supply VLC's observed locale conversion and cleanup imports in one compat ELF while preserving the real OH thread cleanup stack.

## 已定决策

- Copy AOSP14 integer locale conversion semantics without pretending OH and Android cleanup structures are ABI-identical.
- Delegate cleanup execution to the existing OH cleanup stack through explicit translated records, not an explicit-pop-only TLS stub.
- First reproduce actual015aa; add only the four named APIs with the existing owner and rollback unchanged.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-vlc-bionic-residue/**
- tools/spec-checks/tests/u12_vlc_bionic_residue.rs

## 验收标准

场景: Single compat ELF preserves old exports and supplies translated cleanup operations
  测试: u12_vlc_bionic_residue
  假设 Exact015aa recipe, AOSP14 donor and actual OH cleanup disassembly
  当 Two builds, ABI/calls, static scans and portable cleanup behavior tests are checked
  那么 Only four exports are added, old exports/calls remain compatible and scope-dependent first-wall prediction stays conditional

## 排除范围

- Claiming native owner resolution, device thread execution or a lit screenshot from host test doubles.
