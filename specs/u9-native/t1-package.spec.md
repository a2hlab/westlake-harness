spec: task
name: "Prepare U9 N10b and invalid-icon installer candidate"
inherits: project
---
## Intent
Build the approved invalid-icon patch and combine it with N10b native, without incorporating the failed N11 owner candidate or authorizing a device rollout.
## Decisions
- Verify master e0adc3c7 source SHA and apply the supplied patch with zero fuzz; restore the active installer INTERNET/background permission projection verbatim before independently repeating the build.
- Record old-tool recipe baseline mismatch explicitly; compare patch-on against the pinned patch-off source build and U8 ELF interfaces.
- Declare both system installer aliases and preserve original installer rollback bytes; current appspawn-only executor does not restart foundation.
## Boundaries
### Allowed
- benchmark/2026-10-01-u9-native/**
- specs/u9-native/**
- tools/spec-checks/tests/u9_native.rs
### Forbidden
- No board commands, frozen-source changes, edits to approved evidence or rollout gate policy.
## Acceptance Criteria
Scenario: Pinned source and zero-fuzz patch
  Test: u9_native_inputs
  Given the exact master installer source and approved patch
  When the offline build applies the patch
  Then source and patch hashes match, intermediate bytes equal the approved proposed snapshot and final bytes preserve the active permission implementation
Scenario: Repeatable installer and preserved interfaces
  Test: u9_native_build
  Given the preserved OH 6.1 recipe and toolchain
  When patch-off, candidate and independent repeat finish
  Then candidate and repeat hashes match and NEEDED and exports remain compatible with U8
Scenario: Declared candidate without rollout authorization
  Test: u9_native_package
  Given N10b native and the new installer
  When the package is composed and checked offline
  Then all file hashes and frozen identities pass, N11 host/runtime are absent and service activation requirements plus any unapproved gates block rollout
