spec: task
name: "Pin actual Bionic exports and all166 native consumers"
inherits: project
---

## 意图

Correct the assumption that all three Toutiao symbols are exported, record exact dynamic symbol/version evidence and enumerate affected keys from pinned native members.

## 已定决策

- Use actual ELF symbol binding and section index, not a source map or nm without dynamic-only scope.
- Capture readelf -V for every affected member; count relocations separately from unique undefined imports.
- Examine OH6.1 namespace-aware dynlink-linux.c, not the adjacent generic dynlink.c.

## 边界

### 允许修改
- benchmark/2026-10-02-toutiao-bionic-scope/**
- specs/toutiao-bionic-scope/**
- tools/spec-checks/tests/toutiao_bionic_scope.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Real export binding is independent from source declarations
  测试: toutiao_bionic_identity
  假设 The pinned deployed compat and actual native consumers
  当 Symbols and version records are read from each ELF
  那么 Local or missing symbols are not counted as dynamic exports and consumer version requirements remain explicit

场景: All pinned APKs are accounted without treating unsupported members as clean
  测试: toutiao_bionic_consumers
  假设 The166 frozen APK keys and current sidecar metadata
  当 All native members are scanned for the requested undefined symbols
  那么 The report contains166 unique key identities and separates imports relocations sidecars and unsupported ABI

## 排除范围

- No assertion that a static consumer count equals unlocked apps or that version absence alone proves runtime failure.
