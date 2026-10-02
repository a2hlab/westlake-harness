spec: task
name: "U14 actual receipt and review evidence"
inherits: project
depends: [t1-compose]
---

## 意图

Keep actual gate rejection and missing bake evidence distinct from approved execution.

## 已定决策

- Retain raw native, open-site, strings and class-diff outputs without applying exceptions.
- Paired receipts require the actual nine input hashes, 27 output hashes, argv, tools, live logs and successful compiler/logging statuses.
- Validate the two remote guard amendments separately from the frozen compiler and driver.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-final-assembly/**
- specs/u14-final-assembly/**
- tools/spec-checks/tests/u14_final_assembly.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Raw rejection is retained
  测试: u14_final_evidence
  假设 Static scanners report new findings and string changes
  当 Evidence is summarized
  那么 Nonzero exits remain recorded and review rows are not approvals

场景: Incomplete or failed bake is rejected
  测试: u14_final_evidence
  假设 A receipt is missing actual argv, output members, tool hashes or successful live logging
  当 Receipt validation runs
  那么 It rejects without reusing historical U12 execution

场景: Actual complete receipt is accepted
  测试: u14_final_evidence
  假设 Two real output inventories and all actual execution evidence are present
  当 Their identity maps and amended wrapper hashes match
  那么 A verified paired receipt can be bound to the selected output group

## 排除范围

- Outer approvals, production VM replay and screenshot signoff.
