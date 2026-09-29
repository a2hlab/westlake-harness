spec: task
name: "Trace native AbilityStage completion independently of Java binding"
inherits: project
depends: [t1-offline]
---

## Intent
Deliver item 62: trace the receiver, thread, prerequisites and completion reply for AbilityStage and specified-ability handshakes. Compare the hash-pinned B5 jar, native libraries and historical HelloWorld/white-window logs; give source repair locations without deploying changes.

## Decisions
- Separate compiled source, B5 smali, native byte evidence and historical log layout fingerprints.
- Native registration addresses identify a matching layout, not a complete deployed file hash.
- Keep the independently observed Java bind failures separate from missing native completion replies.

## Boundaries
### Allowed Changes
- benchmark/2026-09-29-white-window/**
- specs/white-window/**
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- No board commands, source runtime edits, VM writes, commits or pushes.
- Do not infer an executed callback solely from a registration line or missing INFO message.

## Completion Criteria
Scenario: Pinned B5 and native control flows retain auditable evidence
  Test: ability_stage_offline
  Given the B5 jar with hash 250958dc and two distinct native bridge inputs
  When the offline extraction records smali methods and callback disassembly
  Then asynchronous binding and native reply versus no-reply paths have original line or address references

Scenario: Wrong generation cannot silently become deployed identity
  Test: ability_stage_offline
  Given HelloWorld and nine target PID streams from item 61
  When registered JNI addresses are compared to both native symbol layouts
  Then each observation retains its source line and candidate layout counts without asserting a deployed whole-file hash

Scenario: Java exceptions do not become fabricated native callback execution
  Test: ability_stage_offline
  Given seven failed bindings and two successful bindings before missing ability dispatch
  When the handoff summarizes causal confidence
  Then source and smali show no bind-success prerequisite for the native stage reply and unobserved live callback entry remains explicit
