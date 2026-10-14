spec: task
name: "Verified source atlas publication"
inherits: project
depends: [t1-boat, t2-native, t3-jar]
---
## 意图
Integrate recovered actual source and recipes into the existing 315-row API atlas, fix stale FZ005 source status, keep prior capability evidence unchanged, and audit tracked links and remote default-branch publication.

## 已定决策
- Pin source, recipe, dependency and output hashes separately; preserve original failures and signed evidence.
- Actual execution receipts include argv, stdout, stderr and return code; never infer successful production from an inventory.

## 边界
### 允许修改
- README.md
- sources/api-implementations/README.md
- sources/api-implementations/boat-c9-jar/**
- sources/api-implementations/JAVA-033-theme/**
- benchmark/2026-10-14-api-source-delivery/**
- benchmark/2026-10-14-verified-source-closeout/**
- tools/spec-checks/tests/verified_source_publication.rs
### 禁止
- Do not modify boards, signed artifacts, frozen expectations, unrelated worker changes or publish credentials.

## 完成条件
场景: Deliver verified implementation source and recipe
  审核: human
  测试: verified_source_publication
  Given exact signed output identities and discovered source files
  When collecting and replaying the implementation in an independent directory
  Then tracked source and recipe hashes resolve and execution receipts record the actual output comparison

场景: Reject unsupported completion claim
  审核: human
  测试: verified_source_publication
  Given a missing dependency, differing output or absent original production log
  When auditing source delivery and reproduction claims
  Then the report preserves the failure and does not label historical exact production as proven
