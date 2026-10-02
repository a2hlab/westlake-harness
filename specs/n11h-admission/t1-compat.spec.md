spec: task
name: "Expose compat timing and smoke interpretation"
inherits: project
---

## 意图

Evaluate preserving r3 lookup timing under once-only early inheritance, and provide a PID-scoped diagnostic readout without turning optional unavailability into smoke failure or success.

## 已定决策

- Replay the actual r3 and accepted N11h callbacks with compat becoming mapped during bootstrap; keep this explicitly a simulated loader counterexample, not a device measurement.
- Retain accepted bytes when zero-delta late lookup cannot select an earlier conditional whitelist without granting unverified permissions or repeating inheritance.
- Knowledge smoke entry is a readout rule, not an activation_smoke spec; the current mandatory U10 marker must not be inherited into a final N11h smoke unmodified.
- Require target PID; missing, mixed, malformed and declared skipped-branch observations do not become compat success.

## 边界

### 允许修改
- benchmark/2026-10-02-n11h-admission/**
- knowledge/smoke/n11h-compat-readout.json
- specs/n11h-admission/**
- tools/spec-checks/tests/n11h_admission.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Late-mapped compat exposes the lookup timing delta
  测试: n11h_admission_timing
  假设 The actual accepted callbacks and a fake loader that maps compat during bootstrap
  当 Ordinary early-resident, late-resident, absent and private branches replay
  那么 Late ordinary r3 verifies compat while N11h records unavailability nonfatally, and the private query-skipping difference is explicit

场景: Optional unavailability is not smoke failure or success
  测试: n11h_admission_smoke
  假设 Verified, unavailable, failed inherit, wrong PID, missing, mixed and malformed marker lines
  当 The offline readout classifies only the supplied target PID
  那么 It separates query observations from smoke and relocation verdicts, retains uncertainty, and never accepts an unavailable marker as success

## 排除范围

- No production smoke runner change, executable window, dynamic single-owner proof or screenshot signoff.
