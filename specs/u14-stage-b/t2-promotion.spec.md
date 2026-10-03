spec: task
name: "Port fresh-window U14 promotion dispatch and retention"
inherits: project
depends: ["t1-binding.spec.md"]
---

## 意图

Port U13 dispatcher, retention hook and bounded review waiter to U14 with explicit future Stage A selftest inputs and known-answer tests for rejection or retention.

## 已定决策

- Wrong bundle, any badtag and missing fresh outer signature reject; correct synthetic input passes.
- No decision or stale same-window proof always restores U13 rather than retaining U14.
- Outer13:14 revision: signature cutoff is at lock-start20 minutes, reserving at least10 minutes for full U13 restoration; all device callbacks are mocked in tests.

## 验收标准

场景: Wrong bundle badtag and absent fresh signature refuse
  测试: u14_promotion_known_answers
  假设 Synthetic decisions and schema2 selftest reports are supplied
  当 A wrong bundle one badtag or missing fresh signature is injected
  那么 Each refuses and rollback is selected without any live device operation

场景: Correct synthetic input retains only the exact candidate
  测试: u14_promotion_known_answers
  假设 Exact Stage A bindings and same-window smoke identity and outer decisions pass
  当 Mocked final admission and candidate verification succeed
  那么 The retention decision passes while actual plans remain execution_enabled false and no lock is taken

## 排除范围

- Enable Stage B, sign screenshots or claim VM PASS without a new actual replay.
