Status update: compiler build and boot extension were cancelled after the runtime-JAR subclass succeeded (board #80, 19:16). The estimate below is historical and was never started.

### Estimate: B11 / board #88 host dex2oat and connectivity image extension

#### Contract Summary
- **Scenarios**: 4 (3 happy + 1 exception), shared B11 contract; #88 owns offline compiler/image/package work, cc-wiki owns board acceptance.
- **Decisions**: 9 fixed choices in the rendered contract; #88 additionally requires the resident ART source lineage and an image-extension checksum check.
- **Boundaries**: 3 allowed paths, 3 forbidden rules. #88 explicitly forbids this lane from occupying a board.
- **Inherited constraints**: 6 rendered Must constraints.

#### Module Breakdown

| # | Module | Scenarios | Base Rounds | Risk | Effective | Notes |
|---|--------|-----------|-------------|------|-----------|-------|
| 1 | Match resident ART, compiler source and primary-image inputs | divergence/source | 6 | 1.5 | 9 | Existing reconstructed AOSP14 source is not proven identical to R155; oat version alone is insufficient. |
| 2 | Build host dex2oat/libart/libsigchain using existing recipe | divergence/source | 6 | 1.3 | 8 | Soong host build substrate and exact local patches are not yet verified. |
| 3 | Generate extension and verify parent checksum / class contents | divergence; welcome prerequisite | 5 | 1.3 | 7 | Handoff describes full nine-segment rebuild, while #88 asks for an extension. Must resolve from the actual compiler recipe. |
| 4 | Package v3b with SHA checks, rollback recipe and handoff | rollback; welcome prerequisite | 3 | 1.0 | 3 | No local 5ea write; final image use belongs to cc-wiki. |

#### Summary

- **Base rounds**: 20
- **Integration**: +3 rounds
- **Verification**: +2 rounds (lifecycle and artifact checks)
- **Risk-adjusted total**: 32 rounds
- **Estimated wallclock**: 100–180 minutes of active work if matching source and the host build substrate are available; allow 2–4 hours including compilation waits. This is conditional, not a delivery promise.
- First checkpoint: 20–30 minutes after #87 ACK to establish source/tool/image feasibility. If matching source is missing, report the exact missing inputs at that checkpoint rather than silently substituting reconstructed ART.

#### Risk Factors
1. v3a retains original R155 ART. Earlier B6 work demonstrated semantic differences in reconstructed ART; compiling a tool with the same oat230 number does not establish layout compatibility.
2. The handoff's `m ...` command assumes a complete configured host build tree; the locally recovered provider source subset may not provide that tree.
3. The new jar replaces classes already in an image. A supplemental image cannot be assumed to override existing image classes; compiler validation and the exact BCP/image boundary must settle this.
4. Hardware acceptance and any restart approval are outside this estimate and remain with cc-wiki/outer review.

#### Confidence
- LOW until the 20–30 minute input/compatibility checkpoint. Known recipes reduce implementation uncertainty but do not establish the missing source/build identities.
