# Exact U13 static/native admission review, not approval

## Correction first

The original U13 VLC pair reported diagnostic PC3758→3a58. McDonald's later single `_ctype_` data addition moves it again to **3b98**; the current disabled draft is therefore **manifestc60d0346**, not7615b424. An old issue ID or allowance must not be copied by changing its hash field.

These **three review cases use two different mechanisms**: the two source NOLOAD sites are N1 rows in `native-predeploy-exceptions`; the compat PC diagnostic is a generation static allowance for **both root and route aliases**. It is not a fictitious third N1 row. All approval fields are **null** and no active registry/package is edited. The additional ctype read-only-data string has its own pending review in `benchmark/2026-10-03-u13-compat-ctype/strings-review.json`.

## Case1: android_dlopen_ext diagnostic relocation

| Actual ELF | Function | Backend-call diagnostic PC | Ordinary tail fallback |
|---|---|---|---|
| deployed015aa3a6 |0x373c|0x3758|0x3774|
| reviewed VLCb2be657c |0x3a3c|0x3a58|0x3a74|
| compat-v2b8a87f6f |0x3b7c|0x3b98|0x3bb4|

All **33 instructions** match after resolving relocatable operands to exact import/string/relative-branch identities. `semantics.json` keeps every raw operand and resolved GOT/C-string address. It does **not** erase arbitrary immediates: register use, ENOTSUP95, all internal branch offsets, weak backend and stderr imports, `(null)` and the exact refusal format remain equal. The source `sources/android_dlopen_ext.c:20` and `:28` is byte-identical SHA7337a393. Raw disassemblies/relocations are in `evidence/dlext-{old,vlc,new}.txt` and `relocations-{old,vlc,new}.txt`.

The backend branch returns before the ordinary fallback. The fallback is entered by a branch skipping that call, so the backend call **cannot reach** the tail `dlopen` on the function CFG. The existing linear backward resolver nevertheless crosses the call and embeds its PC in `unknown:x1 clobbered ...`. Retain that raw finding; this package does not repair the scanner or certify the unresolved backend's behavior.

Pending exact static delta: `2cd13b3defeda8318d91d23d1ab8e63f77b0bb79e45bc5961f27fa67e864bd3d`, candidateb8a87f6f versus deployed015aa3a6. `static-policy.draft.json` binds both aliases, the pair/delta and an additional final-manifest field. **The production static tool does not enforce that extra manifest field itself**; the outer admission wrapper must bind the bundle/manifest separately.

## Case2: bridge resident query

- Old `sources/gfx-old.cpp:415`, new `sources/gfx-new.cpp:415`: `s_bridgeHandle = dlopen("liboh_adapter_bridge.so", RTLD_NOW | RTLD_NOLOAD);`.
- Actual oldruntimeac59 PC0x197f30 and newruntime18763 PC0x19810c both have flags **0x6=NOW|NOLOAD**.
- A miss logs and returns; there is no fresh/default fallback. This does **not** prove the required owner is resident/visible/correct at that moment.

## Case3: EGL resident query

- Old `sources/gfx-old.cpp:1327`, new `sources/gfx-new.cpp:1408`: `void* h = android::dlopen("libEGL.so", RTLD_NOW | RTLD_NOLOAD);`.
- Actual oldruntimeac59 PC0x197928 and newruntime18763 PC0x197a08 both have flags **0x6=NOW|NOLOAD**.
- A miss returns `EGL_NO_SURFACE`. `s_resolved` has already been settrue, so subsequent calls do **not** retry; no resident-availability or white-screen safety claim follows.

Both statements and sites preexist in the old source/ELF. The U12 N1 source profiles did not include full graphics compat; U13's added `u13-m1-compat-shim.cpp` profile exposes them. `lineage.json` lists old profiles, source SHAs and all four ELF sites; `evidence/source-lines.json` retains numbered miss-path contexts. Existing binary behavior is a reason for review, not grounds to silently suppress a newly covered finding.

## NOLOAD ground truth

Use the actual factory libcfd3c4701, not an untraceable source approximation. `evidence/noload-mode.txt` shows mode bit4 at0x85dc4 stored in the noload slot0x15e514; `evidence/noload-map-guard.txt` shows0x87130 loading it and0x87134 branching to0x8717c, bypassing the new header-map call at0x87140. This establishes no fresh mapping on that branch. It does not claim zero reference-count/relocation/bookkeeping effects. No source is represented as matching the factory linker build.

## Outer checklist

- [ ] Confirm the three complete normalized bodies/imports/strings, not just the PC delta.
- [ ] Confirm both exact aliases and final pair/delta plus bundle/manifest binding.
- [ ] Review bridge lookup's miss/owner/timing limits; approve or reject N1 issueb8e9f93b.
- [ ] Review EGL lookup's no-retry miss behavior; approve or reject N1 issuec839a571.
- [ ] Separately review the single ctype-table printable projection; do not silently reuse the original VLC strings PASS.
- [ ] Rebind the157 unchanged U12 N1/N2 entries only after final package identity is fixed.
- [ ] Run fresh Mac+VM production gates and obtain window authorization through the executor; none is supplied here.

Current bindings: native manifest **c60d03460f14ec5bdff2031d56792adcc2985f948a8a0cf5189d1fa9cee7575e**, inputs **f76c1af95ccea66e1637fee521ccda2e8ce41567ef4dc75f289361209b1eca51**, bundle **adf3705043472de8797a677d76c16b5976cb9c0be11364daa3bbd1b882b1698b**. `native-predeploy-exceptions.draft.json` has two registry-format rows with extant repository-relative evidence. `rebind.py` rejects stale reports, altered runtime/compat, unknown targets/deltas and nonexistent evidence, and recomputes IDs from exact identity. A future fresh identity still emits **unapproved** rows; it cannot transfer an approval.

No builds, device access, VM access, active registry writes or execution occurred for this review package. Tests use only landed source/evidence and no private `.artifacts`.
