# U15 admission preparation, not a final package

## Correction and current evidence

The native partial's manifest **ce641979** and inputs **58eb84fc** are not the
future final hashes: BCP JAR replacement changes the native inventory, and the
new non-BCP runtime JAR/image receipt changes the bundle. Therefore copying
those204 issue IDs into the final package would repeat the earlier binding
mistake. This packet retains **old U14 → current partial → unknown final**
explicitly, and requires fresh final reports to generate the last column.

`registry-delta.preview.json` contains exactly204 current partial rows:
**N1=99, N2=105**, no duplicates. `old-partial-final-mapping.json` binds each
source ID, partial ID and both normalized semantic hashes; final IDs stay null.
The existing auto-identical classifier independently rechecked all204 against
active approved U14 rows, with zero new findings. Source report paths exist on
master; `source-receipts.json` records their original hashes and tool hashes.
No registry writes or new scanner run is represented by this preparation.

The exact strings approval (master **d8858dd1d1**) is snapshotted in
`evidence/outer-approval-strings.json`. It binds the20-row review hash
**b6b466d7** and keeps the condition that **host9e3a + ANL b96a root/route
aliases ship and roll back together**. It is not an image, JAR, new-native
admission or blanket finding approval. Any changed bytes need new review.

## Flutter admission decision

`flutter-admission-decision.json` gives **0 new-native admission rows** for
Flutter9b824 against the intended U14 content comparison: the exact target
`/system/android/lib64/westlake_flutter/libandroid.so` already exists as fff9.
`generation_static_checks.py:128` consults the new-native table only when the
effective baseline has **no target** (`deployed is None`). Replacing its bytes
and adding three exports is covered by the normal ELF gates, not a fictitious
new-library row. The existing native-domain libandroid alias is untouched.

This is not a claim that U14 has been promoted. Once the real per-board
transaction baseline is signed, re-evaluate its complete effective map. If
the Flutter target is absent there, stop and request an exact final-bound
admission. Likewise retained new libraries such as ICU74 must be evaluated
against that actual baseline; no old-manifest admission is blindly reusable.

## Paired receipt and single-version arrival

`paired-receipt.template.json` has two independent runs, each with exactly nine
pinned inputs (framework9e55 + NSD stubs94a9) and27 null outputs. Actual argv,
toolchain identity, hostlib inventory, log hashes and all return codes remain
null. Compiler ae865/driver14b1, identical work paths and independent persistent
tee logs are required. Driver rc6 records old reference-image mismatch only;
it does not approve the new output. Do not transfer any U14/T7d boot.art mask
without new exact input/output evidence and an outer decision.

`validation.check_actual_pair` is a **structural receipt checker**, not a
compiler/log-file attestor or byte-reproduction gate. Final receipt generation
must verify physical release SHA256SUMS, actual argv transcript, tool hashes,
both full27 groups and original tee/status files before using that structure.
The compact-JSON argv SHA is separate from the original argv-file raw SHA.

`assembly-arrival.json` freezes current native inputs and leaves both incoming
groups pending:
- Full27 paired BCP outputs, selected run and output hashes unknown.
- One U15 runtime JAR v1: trampoline delayed terminate, fd-api theme and
  ActivityManagerAdapter native declaration; candidate path/hash unknown.

Runtime JAR is **not BCP**, so its arrival does not change the nine-input bake.
During packet completion the builder's local release directory appeared with
27 members in each run. Read-only `evidence/incoming-local-observation.json`
records26/27 exact pairs and boot.art differences at0x3e3b9/0x3e3ba/0x3e3bb.
At observation time the producer's sealed SHA256SUMS was absent; no actual
paired receipt, selected output or image exception was issued by this lane.
These are physical file observations, not a reused nondeterminism approval.
The receipt template intentionally stays unfilled; runtime JAR remains pending.
After both are ready, compose one disabled U15 version, updating native BCP
underlays, effective framework overlays, all27 images, runtime JAR and paired
receipt together. Preserve common2c9a/61b51e1 installers; per-board transaction
BASE, expected identity, promotion and execution remain explicit unknowns.

For a completed disabled bundle and its freshly generated native report:

```sh
python3 rebind_preview.py --bundle "$FINAL_U15_BUNDLE" --report "$FRESH_NATIVE_REPORT"
```

This refuses a native-only partial, wrong effective nine-input BCP set, old
runtime JAR, wrong report binding, any new finding or changed normalized
semantics. It emits final-bound registry **previews**, an ID mapping and finding
excerpt; it never applies rows. Fresh full static/native/class/image and
production gates plus outer approval still precede any window. Do not obtain
final IDs by text-replacing manifest hashes in the current preview.

## Validation and landing

`python3 test_prep.py` and Rust selectors `u15_admission_bindings` /
`u15_admission_pair` exercise positive and failure paths with public cold
fixtures. Tests do not rely on `.artifacts`, external worktrees or live machines.
`active-inputs-unchanged.json` records before/after hashes of both active tables;
neither was written. Final bundle/manifest/inputs SHA remain null.
Only this packet/specs/selector are landing paths; `documentation.json` supplies
incremental Layout/DIGEST snippets for the outer. No knowledge/gates files,
binary payloads, production PASS or lighting claim are included.
