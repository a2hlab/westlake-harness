spec: task
name: "Compare nine surviving apps with HelloWorld first frame"
inherits: project
---

## Intent
Extract process-scoped stage observations, lifecycle/render/error tails and the earliest unobserved comparable marker for the nine item 48 apps. Preserve missing inputs explicitly and deliver a partial report if VM reads are unavailable.

## Decisions
- Pin the HelloWorld log and item 48 PID metadata; arbitrary earlier runs cannot substitute for the assigned inputs.
- Ignore registration messages and stack frames as execution markers; retain them only as diagnostic context.
- Reports distinguish observed markers, unobserved markers and unavailable inputs; causal diagnosis remains a human analysis.

## Boundaries
### Allowed Changes
- benchmark/2026-09-29-white-window/**
- specs/white-window/**
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- No runtime code changes, device access, fabricated evidence or automatic LIT classification.

## Completion Criteria
Scenario: Known HelloWorld lifecycle and rendering sequence is reproduced
  Test: white_window_offline
  Given the hash-pinned successful HelloWorld log and PID 25183
  When the offline analyzer extracts stage evidence
  Then attach launch main-looper VSync surface EGL and first-frame markers retain original lines

Scenario: Other process registration and stack messages cannot prove execution
  Test: white_window_offline
  Given unrelated PID messages registration names and exception stack frames
  When the analyzer checks stage presence
  Then those messages cannot become target execution evidence

Scenario: Missing or wrong-identity input cannot become a stall diagnosis
  Test: white_window_offline
  Given nine expected app identities with unavailable or wrong-PID logs
  When a combined output report is generated
  Then unavailable inputs have no inferred first missing stage and identity failures are explicit
