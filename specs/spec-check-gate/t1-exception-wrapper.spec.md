spec: task
name: "Run spec checks with explicit exceptions"
inherits: project
---

## 意图

Run the full Cargo spec-check suite and separate the seven approved exceptions from new regressions. Preserve raw test outcomes and warn when an exception passes so the outer loop can remove it.

## 已定决策

- Store exact selector names, categories, reasons, evidence paths and removal conditions in a versioned JSON registry.
- Run cargo test without selector filters; preserve stdout and stderr. Subtract only exact failed selectors in the registry.
- Return 1 for unexcepted failures, malformed registry/output, incomplete runs or infrastructure errors. A passed exception emits STALE and does not alone fail the gate; ignored or absent exceptions are not passes.
- Add independent Rust integration tests that call three Python fake-Cargo cases without modifying existing selectors.

## 边界

### 允许修改
- knowledge/gates/spec-check-exceptions.json
- scripts/lab/spec_checks.py
- scripts/lab/test_spec_checks.py
- tools/spec-checks/tests/spec_check_gate.rs
- specs/spec-check-gate/**
- .octos/OPS-RUNBOOK.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No existing selector edits, historical evidence edits, automatic registry rewrites, device access or pushes.

## 验收标准

场景: Approved failures remain visible
  测试: spec_gate_approved_failures
  假设 A fake Cargo run contains only approved failed selectors and passing controls
  当 The wrapper runs the complete suite with the registry
  那么 It returns 0 and reports the original failures as EXCEPTED rather than PASS
  并且 The seven registry entries contain exact selectors categories reasons evidence and removal conditions

场景: New failures and incomplete runs reject
  测试: spec_gate_new_failure
  假设 A fake Cargo run includes an unexcepted failure or invalid incomplete output
  当 The wrapper parses the run
  那么 It returns 1 and does not hide infrastructure errors or missing exceptions

场景: Passing exceptions become stale
  测试: spec_gate_stale_exception
  假设 A fake Cargo run explicitly passes an exception selector
  当 The wrapper evaluates the registry
  那么 It prints STALE and returns 0 when no other failure remains
  并且 It leaves the registry unchanged and never treats missing or ignored selectors as stale passes

## 排除范围

- Fixing the seven underlying failures or accepting device screenshots; changing default Cargo verdicts.
