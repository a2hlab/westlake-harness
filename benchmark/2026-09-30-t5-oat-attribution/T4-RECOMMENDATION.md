# Proposed T4 extension (for the contract owner)

Target: `specs/dex2oat-once/t4-layout-gate.spec.md`. This is a recommendation, **not an edit to the approved contract**. T4's existing system-class, Thread and header-layout checks remain required. Equal layouts did not cover the OAT read-barrier compatibility branch.

Add a separate build-switch gate before treating T4 as sufficient for T6. Preserve the hash identity of reference libart **59e1bb45…**, its primary boot OAT **25d92cf7…**, the new host dex2oat and all loaded host libraries, the target libart, and the newly generated primary image/OAT.

Proposed obligations:

1. Compare **effective read-barrier state** across generated OAT, runtime native predicate and reference OAT. R155 expects false at `ValidateOatFile@0x461bb8`. A false/true mismatch is a hard failure even if all mirror/Thread offsets agree.
2. Compare recovered compile defaults: **CMS enum 2**, generational CC default false, heap poisoning false, native release build. Inspect the new target binary with the same source-linked predicates; require its build log/Soong flags and the host tool's effective flags to agree. An environment variable printed before a build is not proof it reached the compiler.
3. Archive configuration: `ART_USE_READ_BARRIER`, `ART_READ_BARRIER_TYPE`, `ART_DEFAULT_GC_TYPE`, `ART_USE_GENERATIONAL_CC`, `ART_HEAP_POISONING`, `ART_TEST_DEBUG_GC`, derived `ART_USE_TLAB`, native NDEBUG/debug target, interpreter, sanitizer/stack-gap and optimization flags. An unrecovered reference value is **unknown**, not automatically equal; explain the boundary and obtain explicit review for relevant unknowns rather than filling a default.
4. Require all nine reference input JAR hashes, dex-locations, actual KV set, and ART/OAT checksum pairing. Do **not** demand invented primary bootclasspath-checksums/compilation-reason keys. Do not require a new checksum to equal the old checksum if the new image/OAT pair is coherent; byte identity remains L1 and board acceptance remains L2.
5. Negative controls: same layout + RB mismatch fails; runtime debug setting cannot be inferred from OAT debuggable; a helper symbol's presence cannot prove that collector/type is selected; unknown compiler settings cannot become pass. Candidate current T5 **08837079…** is the real mismatch fixture; reference versus itself is the known good static control.

Suggested new scenario (new selector implementation belongs to the T4 owner): `d4_build_switches_match_board`. Given hash-pinned native/image artifacts and build receipts, extract effective flags; require zero known mismatches; emit unknown fields for review. Keep L2 under its existing human/board acceptance and keep the current read-barrier-on T6 strictly a diagnostic experiment.

Evidence: `build-flags.json`, `libart-evidence.json`, `source-evidence.json`, `t5-comparison.json`. In particular, native `XGcOption` allocation at **0x76e5a4–0x76e5b8** and empty Parse branch **0x770e38–0x770e78** independently establish CMS, so setting only RB=false while retaining r1's default CMC is an incomplete reproduction recipe.
