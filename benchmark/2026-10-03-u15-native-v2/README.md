# U15 native partial v2: Flutter ATrace joins the single batch

## Correction and composition

The previous partial had three objects and four payload paths. Outer07:30
delivered Flutter9b824; this **new immutable partial** adds its private owner,
without modifying the landed prior draft or rebuilding any donor.
`composition.json` binds the exact U14 common9b42/61bf589 content references,
four candidates and **five** changed payload paths:

| Object | Candidate | Target |
|---|---|---|
| runtime M3 | 94c31177 | root liboh_android_runtime.so |
| host Mindustry + Meet | 9e3ad72e | runtime appspawn-x |
| ANL Meet | b96a8991 | root + route libapp_native_loader.so, atomically |
| Flutter ATrace | 9b824502 | westlake_flutter/libandroid.so only |

The private `westlake_native/libandroid.so` remains unchanged. Donor two-build
objects and release inventories are hash-checked locally. Final compiled host
source is release63e2, not the builder's pre-patch input. Source snapshots,
original and portable hashes, upstream compiler/build recipes and persistent
tee logs are retained together. No build, VM probe or board action ran here.

The only staging product is this worktree's `.artifacts/native-only/native/`;
there is **no bundle.json**. BCP payload is still historical U14 inventory;
the separately pinned framework9e55+stubs94a9 plan lives in
`../2026-10-03-u15-bcp-v2/`. All 27 images and fresh paired receipt remain pending.
Common/61b transaction parameters are null; content references do not prove
promotion. Both board-local installer identities are preserved, not unified.

## Fresh Mac evidence, not production admission

`report-summary.json` binds each original stdout, portable stdout, argv and
exit code. Who-is discovery is retained, but comparisons use explicitly pinned
U14 content paths rather than a glob or a historical filename guess. U14 is the
authorized **content comparison** base; this does not assert it is currently
deployed. Future production replay still requires the actual signed per-board
transaction base.

- N1/N2 candidate raw **REJECT**: 99/105 unbound historical issues, errors0.
  Exactly204 identical previews and **0 new findings**; no apply or signature.
- Open counts Flutter7→7, runtime197→197, host8→8, ANL0→0; namespace and
  production-schema open deltas empty for all four objects. Raw DEFAULT-NS,
  MULTI-NS and namespace edges remain in the evidence.
- NEEDED unchanged for every object. Flutter adds exactly
  `ATrace_beginSection`, `ATrace_endSection`, `ATrace_isEnabled` under existing
  `FLUTTER_ANDROID_1`. Its three `atrace_*` imports are all exported by runtime94c3
  and use the existing `liboh_android_runtime.so` dependency, not a new open.
  Source masks `ATRACE_TAG_APP` rather than treating any enabled tag as app trace.
- ABI removed/drift0 and219 consumer breaks0. Only Flutter has3 added exports.
  Existing Flutter callsets0 changes; runtime has the one documented EGL
  converter/HiLog callset change; host/ANL callsets unchanged, **not** bodies.
- Production selected-readonly strings: runtime4drop/5add, host4drop/6add,
  ANL0drop/1add retain exit1; Flutter0drop/0add exits0. This tool does not count
  every dynstr/debug name, so0/0 does **not** mean no new exports. Dynsym evidence
  independently records the three exports and imports.
- Frozen-native-only exit0. No full bundle/images/RB/T4b/G1/G2/Mac+VM production
  PASS is claimed. Active registry copied for read-only comparison is unchanged.

`STRINGS-REVIEW.md` and `strings-review.json` provide **one unsigned table** for
the20 actual strings changes, exact object pairs, source lines, reasons, original
literal hashes and raw report references. Printable binary/address fragments
are explicitly flagged for outer binary review, not automatically allowed.
Flutter's zero selected-string delta is represented as an object-level row;
its independent export/import delta is not disguised as a strings approval.

## Predictions and handoff

Donor conditional first-wall targets: M3 three, Mindustry one, Meet one;
Flutter ATrace one (`fd-immich`), together with NSD94a9 for its preceding
VerifyError. Observed moves by this offline lane are **0**; raster/next walls
and t20 remain unknown. Donor prose about saber being lit is not used: outer
07:06 signed it alive-white, and screenshot is the only lighting criterion.

Tests require only public landing files, never `.artifacts`. Run
`python3 test_draft.py` and the two `u15_native_v2_*` Rust selectors; fresh
lifecycle and cold-copy evidence are in `evidence/`. `documentation.json`
contains incremental root Layout/DIGEST additions. `landing-paths.txt` excludes
binary payloads and active gate edits. Outer must review strings/calls and
future full-package bindings; this report is neither an approval nor a window.
