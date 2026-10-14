spec: task
name: "Shared native validated source closure"
inherits: project
depends: []
---
## 意图
Recover the producing source, compile/link recipe and toolchain identities for signed bridge8ab and libandroid ADC; inspect FZ001-003 dependency closure. Execute bounded offline rebuild or exact replay and retain concrete unresolved historical bindings.

## 已定决策
- Pin source, recipe, dependency and output hashes separately; preserve original failures and signed evidence.
- Actual execution receipts include argv, stdout, stderr and return code; never infer successful production from an inventory.

## 边界
### 允许修改
- sources/api-implementations/shared-native-production/**
- benchmark/2026-10-14-verified-source-closeout/**
- tools/spec-checks/tests/verified_native_source.rs
### 禁止
- Do not modify boards, signed artifacts, frozen expectations, unrelated worker changes or publish credentials.

## 完成条件
场景: Deliver verified implementation source and recipe
  审核: human
  测试: verified_native_source
  Given exact signed output identities and discovered source files
  When collecting and replaying the implementation in an independent directory
  Then tracked source and recipe hashes resolve and execution receipts record the actual output comparison

场景: Reject unsupported completion claim
  审核: human
  测试: verified_native_source
  Given a missing dependency, differing output or absent original production log
  When auditing source delivery and reproduction claims
  Then the report preserves the failure and does not label historical exact production as proven
