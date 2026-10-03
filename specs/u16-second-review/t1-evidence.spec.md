spec: task
name: "U16 image, native scope and class review packet"
inherits: project
---

## 意图

Prepare the second outer approval packet for one new boot.art pair, seventeen previously signed native scopes and eight exact DEX additions. Include all four externally executed G1/G2 results without claiming production or rollout approval.

## 已定决策

- Bind nine effective JARs, both new image hashes, changed byte offsets and the precise object-chain interval.
- Transfer scope only after identical selected ELF bytes and exact semantic finding fields, including source line and text, are proved.
- Extract superclass, interfaces and method descriptors from complete base/candidate DEX dumps; pin source commits and git blobs.
- Preserve raw Mac16:53 and VM17:05 records; no pending decision becomes an active exception.

## 边界

### 允许修改
- benchmark/2026-10-03-u16-second-review/**
- specs/u16-second-review/**
- tools/spec-checks/tests/u16_second_review.rs
- benchmark/2026-10-03-u16-final-assembly/receipts/outer-g1-g2-second-review.json
- benchmark/2026-10-03-u16-final-assembly/gates/darwin-20261003T165327.json
- benchmark/2026-10-03-u16-final-assembly/gates/linux-20261003T170534.json
- benchmark/2026-10-03-u16-final-assembly/evidence/common/darwin-20261003T165327/image.txt
- benchmark/2026-10-03-u16-final-assembly/evidence/61b/darwin-20261003T165327/image.txt
- benchmark/2026-10-03-u16-final-assembly/evidence/common/linux-20261003T170534/image.txt
- benchmark/2026-10-03-u16-final-assembly/evidence/61b/linux-20261003T170534/image.txt

## 验收标准

场景: Exact evidence packet remains unsigned
  测试: u16_second_review_evidence
  假设 The two new runs, seventeen scope rows and eight classes are complete
  当 Packet invariants are validated
  那么 All26 decisions remain pending and no execution or gate application is enabled

场景: Semantic drift is rejected rather than rebound
  测试: u16_second_review_evidence
  假设 One finding source line or text differs
  当 Scope transfer comparison runs
  那么 It rejects the transfer and records the differing field

场景: Image field exception is bounded to the new pair
  测试: u16_second_review_evidence
  假设 A changed byte falls outside the eight-byte first long element
  当 Image pair verification runs
  那么 It rejects without applying the U14 historical exception

场景: Cold checkout validates small persisted evidence
  测试: u16_second_review_evidence
  假设 No ignored artifacts or live remote tools are available
  当 Persisted packet tests run
  那么 Source snapshots and four original G1/G2 records validate locally

## 排除范围

- Applying exception tables, rebuilding images, remote execution, production admission or promotion.
