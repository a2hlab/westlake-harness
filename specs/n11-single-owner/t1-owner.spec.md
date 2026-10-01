spec: task
name: "N11 resident namespace owner candidate and short-window evidence"
inherits: project
---
## Intent
Replace independent bridge/runtime class-loader loads with the existing sealed owners. Extend N10b with a host callback and compat-owner activation log; reject missing owners instead of creating new instances. Produce a gated candidate and a reversible 61b window with ten repeated target observations.
## Decisions
- Preserve the provider 0509fe23 and its class-loader injection; the legacy child_main INPUT block is absent from the deployed ELF.
- Prove the U8 host and runtime baselines byte-identical and independently repeat both candidates.
- Strict missing-owner lookup never falls back to a fresh load; ordinary library requests retain their app namespace.
- Require explicit new manifest-bound exceptions before device deployment; preserve all raw attempts.
## Boundaries
### Allowed
- benchmark/2026-10-01-n11-single-owner/**
- specs/n11-single-owner/**
- tools/spec-checks/tests/n11_owner.rs
### Forbidden
- No edits to frozen source files, bridge/ART/provider/Java/images, approved older evidence or native gate policy.
## Acceptance Criteria
Scenario: Exact source and baseline identity
  Test: n11_identity
  Given U8 host/provider/runtime and their recorded production recipes
  When baseline and candidate recipes finish
  Then baseline host/runtime match U8, both candidates repeat byte-identically and frozen runtime objects plus provider remain unchanged
Scenario: Share only existing canonical owners
  Test: n11_owner
  Given an owner namespace and library-open callback
  When the canonical bridge/runtime names or paths are requested
  Then the host shares exactly the two library names and returns a resident sealed handle with RTLD_NOLOAD
Scenario: Refuse a missing owner without a fresh load
  Test: n11_owner
  Given absent owner namespace or absent resident owner
  When a bridge/runtime request is made
  Then the request returns null and never retries without RTLD_NOLOAD
Scenario: Reject foreign namespace and keep ordinary requests local
  Test: n11_owner
  Given unrelated paths, foreign namespace or RTLD_GLOBAL request
  When the host callback receives the request
  Then unrelated libraries retain the app namespace and foreign/global requests return null
Scenario: Production gates retain explicit approval requirements
  Test: n11_gates
  Given the exact candidate sidecar and no new manifest approval
  When offline N1/N2 and frozen checks run
  Then every finding is recorded for outer approval and no device I/O occurs
Scenario: Device owner and repeated UI acceptance
  Review: human
  Test: n11_device
  Given explicit outer gate approval and a locked 61b U8 baseline
  When detached board_run completes smoke and five wikipedia plus five fd-noice runs
  Then four owner libraries each have one load instance, both target logs have zero unknown sessionId, t20 screenshots are compared with baseline 3/6, and rollback restores U8 before unlock
