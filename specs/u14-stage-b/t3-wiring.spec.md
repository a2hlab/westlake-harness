spec: task
name: "U14 Stage B recovery budget and native ticket freshness"
inherits: project
depends: t2-promotion
---

## 意图

Implement outer13:14 P1 and P2 wiring corrections. Finish signature waiting by lock-start20 minutes with10 minutes reserved for recovery and assert fresh candidate/baseline native tickets on both surfaces before transport.

## 已定决策

- Use stable pre-lock runner birthtime as a conservative lock lower bound; absent or invalid start time refuses waiting and selects restoration.
- At or after the20-minute boundary, even an existing valid signature is not passed to retention; always keep the finalizer.
- Read full gates/mac/executor and gates/vm/executor, require deployable receipts and exactly two correctly owned candidate/baseline tickets, and call production deployment_native_gate.assert_unchanged on each.
- Tests use temporary file-bound native inventories and trusted checker/registry fixtures with the real binding assertion; all actual transport is mocked and shipped plans remain disabled.

## 验收标准

场景: Boundary and fresh full tickets have deterministic known answers
  测试: u14_promotion_wiring
  假设 Synthetic timestamps and candidate/baseline native inventory bindings are supplied
  当 A signature arrives just before cutoff and all four tickets remain unchanged
  那么 The deadline leaves600 seconds recovery and each full ticket is asserted while no real transport runs

场景: Expired signature missing start or ticket drift refuses before transport
  测试: u14_promotion_wiring
  假设 The exact cutoff is reached or a registry checker sidecar payload owner or receipt binding changes
  当 Review finalization or pre-lock native admission executes
  那么 Expired signature cannot retain and changed or missing full native tickets reject before transport while restoration is selected

## 排除范围

- Enable promotion, alter current Stage A plans, run VM probes, touch gates or operate devices.

