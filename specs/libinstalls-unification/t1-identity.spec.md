spec: task
name: "Resolve service lineage and actual binary validation delta"
inherits: project
---

## 意图

Explain the two deployed libinstalls versions using existing service identities, exact bytes, string/disassembly evidence and the frozen reviewed-payload source.

## 已定决策

- The proposed target must be the b79 source artifact51e1b525, not a live61b copy.
- WHOIS defaults to runtime-generation/app maps and therefore cannot prove installd is absent.
- Follow stripped CFI entry branches to actual validation bodies; validate supplemental unstripped symbols against exact deployed text sections.

## 边界

### 允许修改
- benchmark/2026-10-02-libinstalls-unification/**
- specs/libinstalls-unification/**
- tools/spec-checks/tests/libinstalls_unification.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Native identities are exact and behavioral claims remain bounded
  测试: libinstalls_identity
  假设 Pinned original and reviewed service ELFs and recorded board hashes
  当 The offline artifact audit runs
  那么 SHA and export identities match, raw strings remain unallowed, and CFI body evidence is derived from the deployed bytes

场景: The actual exception predicate is not broadened
  测试: libinstalls_payload_policy
  假设 The four reviewed bundle ABI filename and payload SHA tuples
  当 The candidate source and compiled table are examined
  那么 Only exact tuples have exceptional acceptance, default ELF and CRC ownership checks remain, and APK metadata hashes are not misrepresented as runtime predicates

## 排除范围

- No general claim that the whole binary changes only four lines or that all-function behavior is identical.
