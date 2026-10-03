spec: project
name: "Disabled U14 promotion preparation"
---

## 约束

- No board operations, locks, activation, gate-table edits or changes to current Stage A plans.
- U14 candidate common56974aa0 and61b afb44370; rollback remains armed U13 common2abe4a49 and61b0a31ad35.
- Candidate assertions/unique paths322/320; restored321/319. Never truncate new paths.
- Fresh outer Stage A and same-window Stage B approval, strict crypto health and signed copy ceilings are mandatory.
- Tool tests use synthetic records only; VM replay is lightweight and never reaches device transport.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-stage-b/**
- specs/u14-stage-b/**
- tools/spec-checks/tests/u14_stage_b.rs
- README.md

