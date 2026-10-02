spec: task
name: "Single ctype data export and static validation"
inherits: project
---

## 意图

Provide the Android legacy classification pointer without changing existing compat functions or assuming namespace visibility proves relocation.

## 已定决策

- The table contains EOF plus256 unsigned-character classifications; the public data object is an eight-byte pointer.
- Pin the original source and compare all257 candidate bytes and consumer dereferences.
- Reuse exact reviewed b2 objects and compiler; stop if its baseline is not byte-identical.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-compat-ctype/**
- specs/u13-compat-ctype/**
- tools/spec-checks/tests/u13_compat_ctype.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Exact baseline and single public data addition
  测试: u13_compat_ctype_native
  假设 The admitted b2be657c baseline and authoritative table are pinned
  当 Two candidate builds and ABI calls plus219 consumer checks run
  那么 Both builds match and only _ctype_ is added with zero drift and breaks

场景: Complete table and pointer semantics
  测试: u13_compat_ctype_native
  假设 The app dereferences a LIBC-versioned legacy pointer
  当 EOF and all256 character entries are compared to original source
  那么 The pointer targets the exact257-byte table rather than masquerading as an array

## 排除范围

- Adding unrelated exports, changing McDonald routing or claiming screenshot success.
