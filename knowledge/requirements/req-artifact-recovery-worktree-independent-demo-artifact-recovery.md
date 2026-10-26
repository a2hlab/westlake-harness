---
kind: requirement
id: REQ-ARTIFACT-RECOVERY
title: Worktree independent demo artifact recovery
status: accepted
liveness: auto
tags: [artifacts, recovery, demo]
---
## Problem
Demo binaries and exact build inputs are dispersed across worktrees. Deleting a checkout must not delete the only usable or buildable copy.
## Requirements
- A fresh checkout plus an explicitly configured independent artifact store MUST recover the exact selected demo payload by full SHA256 without reading original worktrees.
- The manifest MUST record compatible runtime sets, rollback artifacts, source/recipe/log provenance and per-component rebuild gaps. Archived bytes MUST NOT imply clean-source rebuild or new device acceptance.
- Artifact publication MUST be immutable and verified before a release becomes available. Existing worktrees and devices MUST remain unchanged during recovery rehearsal.
- Remote copies and a clean destination recovery MUST be independently verified; local-only storage MUST NOT be described as another-machine recovery.
## Scenarios
Scenario: Recover without producer checkout
  Given a pinned release manifest and independently stored objects
  When the consumer restores to an empty directory without producer paths
  Then every required file matches its recorded bytes and rebuild gaps remain explicit
