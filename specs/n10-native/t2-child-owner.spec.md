spec: task
name: "N10b route-owned JNI owner preload"
inherits: project
depends: [t1-candidate]
---
## Intent
Replace only the U8 child to move bridge/runtime preload out of default namespace after N10 HelloWorld signal11 with duplicated ART.
## Decisions
- Read OH6.1 musl dlns creation, direct inheritance and resident lookup implementation before choosing the owner.
- After route-a provider has loaded, check resident ART with NOLOAD and preload bridge/runtime through that same sealed.child namespace before provider init.
- Keep all U8 native members, Java and image bytes unchanged except the child; retain failed N10 evidence separately.
- A new candidate does not inherit N10 approvals; production dry-run must refuse unresolved findings and rollout remains disabled pending review.
## Boundaries
### Allowed
- benchmark/2026-10-01-n10b-child/**
- specs/n10-native/t2-child-owner.spec.md
- tools/spec-checks/tests/n10b_child.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- Device I/O, changes to host/ANL/Bionic/provider/runtime/ART/bridge, original build inputs, frozen sources or gate policy
## Acceptance Criteria
Scenario: Route-owned preload order and safe refusal
  Test: n10b_owner
  Given the actual production loader function and an instrumented namespace ABI
  When the provider is opened and resident ART or a JNI owner is absent
  Then no default preload occurs, both owners use sealed.child only after route provider load, and missing prerequisites return failure
Scenario: Child-only reproducible candidate
  Test: n10b_identity
  Given the retained deployed child recipe and exact U8 composition
  When baseline and candidate are built and assembled
  Then baseline d240f8d2 matches, candidate repeats match, only one object and target change, and all 312 composed identities preserve U8 except child
Scenario: Strict gates remain authoritative
  Test: n10b_gates
  Given exact candidate-bound native sidecars and the signed U8 baseline
  When offline preflight runs
  Then frozen artifacts pass, unapproved findings remain rejected, and a manifest-bound exception proposal records exact counts without deployment authorization
