spec: task
name: "N10b U8 JNI initialization and real Emboss batch"
inherits: project
depends: [t2-child-owner]
---
## Intent
Combine route-owned child preload with the real EmbossMaskFilter implementation over signed U8. Add cc-wiki Typeface JavaVM initialization and the NDK AssetManager owner cache initialization without modifying FZ-003. Preserve U8 Java, images, bridge and ART bytes; deliver only an offline candidate and exact gate exception proposal for outer review.
## Decisions
- Reuse cc-t3 AOSP14 constructor and the existing OH m133 backing filter, after matching deployed Skia SHA caa86d58.
- Keep Emboss support in separate source files and register after the original HWUI and compat registrations.
- Prove runtime baseline 216b68fb byte-identical before building the extension; candidate and independent repeat must match.
- Preserve strict native gates and frozen APIs. Unapproved findings remain rejected and rollout stays disabled.
## Boundaries
### Allowed
- benchmark/2026-10-01-n10b-child/**
- specs/n10-native/**
- tools/spec-checks/tests/n10b_child.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- Device I/O, changes to U8 ART/bridge/Java/images or OH Skia, frozen source edits and gate-policy changes
## Acceptance Criteria
Scenario: Real Emboss and same-generation source identity
  Test: n10b_emboss
  Given the deployed U8 Skia and copied OH m133 implementations
  When the isolated filter and extended runtime are strictly linked
  Then the constructor strictly links to a real SkMaskFilter implementation and baseline/repeated build receipts match with frozen implementation objects unchanged
Scenario: Registration side effects belong to the native owners
  Test: n10b_registration_init
  Given the actual Typeface and separate AssetManager initialization sources
  When an instrumented JNI and DSO ABI exercises success and missing prerequisites
  Then HWUI VM initialization precedes delegated registration, both owner caches receive the real field ID, and missing VM, setter, field, DSO or cache fails without delegating unsafe work
Scenario: Batch identity and immutable Java/image group
  Test: n10b_batch
  Given signed U8 and reproducible child/runtime candidates
  When a new generation bundle is assembled
  Then only child and runtime aliases change, all Java/image identities remain U8 and rollback references bind U8
Scenario: No unauthorized rollout or borrowed exceptions
  Test: n10b_batch_gates
  Given the exact candidate source and namespace sidecars
  When production preflight is run without new approval
  Then unresolved native findings are rejected, the exception proposal binds this manifest and input SHA and no board I/O occurs
Scenario: Activation smoke refuses an inactive fix or mixed native owners
  Test: n10b_smoke_spec
  Given the exact N10b fingerprint, four native activation markers and owner/view checks
  When any marker, owner single-copy identity, child-view SHA, fingerprint or t20 control is missing or mismatched
  Then smoke rejects, complete synthetic evidence passes, and ZigZag stays launch-only
