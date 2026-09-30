# U5 feedback v1: static requirements and input blockers

## What was wrong

The frozen J6/N4 forecast omitted seven signature families on fourteen U5 keys. A package export inventory did not establish the actual consumer's namespace, and EGL/megazord checkpoints did not cover FlutterJNI/mozglue. Treating every missing signature as a successful crossing would also erase earlier masking failures. The original forecast and its **38 hit / 2 false positive / 26 unknown** score are unchanged.

This release adds **seven key-independent rules**, scans all **66 keys / 214 DEX members**, and catches **14/14 known missed keys** as conditional requirements. That is **training-set coverage, not prospective accuracy**. Twenty-nine keys match at least one new requirement; unused methods and optional load paths can match, so additional matches are not certified failures. First-wall order, field producer state, namespace resolution and t20 remain unknown. This is an additive B10 feedback module, not a replacement for all earlier B10 rules.

## Evidence and predictions

- `PREDICTIONS.csv` / `PREDICTIONS.json`: version **u5-feedback-v1**, one row per frozen key, separate `input_findings` and `app_wall_risks`.
- `static-facts.json`: actual local APK inventory/SHA, metadata SHA, sidecar header/SHA, DEX method/offset/entry SHA, ELF strong imports and DT_NEEDED, collector tool identity. No runtime logs are inputs to prediction generation.
- `RULES.md`: seven signatures, exact matching conditions, all affected keys, the fourteen expected keys' static witnesses and original U5 line numbers.
- `results.json`: separately joins predictions to the already reviewed U5 training evidence. This evaluator, not the predictor, reads observed outcomes.
- `SHA256.json`: binds the new facts, forecast, rules, scanner and parser dependencies. The old frozen CSV remains `bae8fd74ffdcba3aa5ea05688fcc0c516169f0b0cfcc29d46249c7352fc6a26d`.

Profile: U5 **westlake-generation-n4-order-216b68fb**, package SHA `7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe`. The private reload rule joins an actual FlutterJNI invocation with the package's `payload/android/lib64/westlake_flutter/libandroid.so` dependency on `liboh_android_runtime.so`. It does **not** prove that OH musl never searches inherit, that the file is absent, or that XPM errno 22 is inevitable. Rescan a different candidate; do not transfer this profile to N5/J7b.

## Input layer, not app walls

Five multi-APK directories: burgerking, subwaysurfers, firefox, mcdonalds, x. Two invalid AArch64 sidecar inputs: fd-seal (`libaria2c.zip.so`), toutiao (`libcvt.so`). One APK pin mismatch: subwaysurfers. These are **7 unique blocked keys / 8 category memberships**; subway has two categories. Under the current base-only installer, runtime repairs alone do not close these input blockers. Multiple APK files are a conservative input-set warning, not proof that every app must crash.

`apps.json` leaves noice/x pins null: the batch resolves metadata, so null is recorded as **unpinned**, not reported as drift. `fd-client` is a single APK with seven DEX members, not split. SHA drift checks compare a non-null apps.json pin to metadata and actual hashed bytes; even matching metadata cannot excuse a missing actual APK. No input is edited, silently dropped, merged or re-pinned. Firefox/McDonald's still retain their conditional native requirements while input-blocked; they are not counted as two additional runtime failures.

## Reproduce offline

Run from the repository root. `WORKSPACES` identifies the directory holding the harness and generation package. The collector defaults to `$HOME/a2hlab/app-inputs` and `$HOME/Library/Android/sdk/build-tools/37.0.0/dexdump`; both have explicit overrides.

```sh
SCAN=benchmark/2026-09-29-static-wall-prediction/scan_u5_feedback.py
OUT=benchmark/2026-10-01-u5-feedback-v1
python3 "$SCAN" collect \
  --apps "$WORKSPACES/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json" \
  --generation "$WORKSPACES/westlake-generation-n4-order-216b68fb" \
  --output /tmp/u5-feedback-recollect
python3 "$SCAN" predict --facts "$OUT/static-facts.json" --output /tmp/u5-feedback-replay
python3 "$OUT/test_feedback.py"
```

Do not overwrite the v1 evidence for a changed input or candidate. Use a new output directory/version. Prediction replay needs only committed static facts, not APKs, private lab paths, dexdump, a VM or devices. Collection checks all `classes*.dex`, preserves dexdump failures as unknown, and rejects partial ELF interpretation as proof of a strong import.

## Validation and landing

Four new Rust integration selectors call the Python rule, input, coverage and version tests; no existing selector is changed. Positive rules have wrong-owner/weak-symbol/changed-dependency controls. Tests distinguish mono multidex from split, null pins from drift, malformed/non-AArch64 sidecars, and failed dexdump from a clean scan. See `validation/` for independent exit codes of both required gates on fixed master `7fb4a24e2` plus only this delivery. Existing nine approved spec exceptions remain unchanged; gate pass does not mean all cargo tests passed.

Landing is additive: two new scanner files, this directory, `specs/u5-feedback/`, `tools/spec-checks/tests/u5_feedback.rs`, and the single new README/DIGEST lines. Prior dirty branch delivery files are already adopted; do not copy old exception registries or overwrite master documents with the stale branch versions. See `HANDOFF.md` for final counts and gate receipts.
