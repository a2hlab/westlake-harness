# U14 conditional U13 per-board transaction binding

## Correction and status

The earlier U14 packet compared artifacts against U13 but its diagnostic transaction still used T8. Furthermore, U13's own `reference/runtime.txt` describes the old T8 baseline, not the candidate U13 bytes. Copying that reference would silently bind a future U14 transaction to the wrong identity.

This packet takes the **planned U13 candidate identity** from the accepted U13 composition, verifies its complete expected map and fingerprints against each content bundle, and builds disabled metadata variants. **U13 promotion is not confirmed.** These references are conditional preparation, not a signed live-board baseline.

`native_abi v2` arrived from master `e90947270c`: two identical `f8619ad5` outputs replace only the `westlake_native/` slot. Root and Flutter ABI remain `d2053066`. The landed first U14 packet remains immutable. No image rebake, native build, VM command, registry application or device operation occurs here. Earlier pending and failed preparation attempts remain private, never selected as final evidence.

## Prepared variants

| Variant | Planned U13 transaction base | Prepared U14 bundle | Installer pair |
| --- | --- | --- | --- |
| 5ea/5cd common | `91272eaf` | `481055eb` | Both `2c9a5294` |
| 61b | `8861a11a` | `b4eb1abe` | Both `51e1b525` |

After the outer's findings approval, separate immutable **reviewed** metadata variants are **`9b42ddc6` (common) / `f5898447` (61b)**; `reviewed-composition.json` and `reviewed-transaction-plan.json` bind their full hashes. Their candidate artifacts and native manifest/inputs are identical to the raw variants above. Both remain disabled and conditional on actual U13 promotion.

Full hashes, source evidence, planned runtime/boot fingerprints and explicit promotion flags are in each variant's `composition.json`. The installer paths are `/system/lib64/libinstalls.z.so` and `/system/lib64/platformsdk/libinstalls.z.so`; `transaction-plan.json` proves baseline=expected and **zero installer operations**.

Both variants have native manifest `3460435a` and inputs `11001e6e`. The ABI slot change and exact source snapshot binding change native issue IDs; the two bundle-only per-board variants share those native identities. Fresh Mac native reports reproduce **159 approved-identical preview rows + 44 new N1 / 1 new N2**. All 45 pending findings match the earlier packet field-for-field except binding/approval metadata, with explicit old→new IDs; none is newly approved here. Native/static raw results remain **REJECT**, not PASS. `registry-delta.json` is unapplied. See each `results.json`, `pending-id-map.json` and `evidence/` for exact outputs.

The subsequent outer signature in `benchmark/2026-10-03-u14-review/outer-approval-findings.json` authorizes those 45 findings, four delta groups, five added classes, ICU admission and 159 rebindings. `registry-delta-signed.json` contains **204 signed rows**, plus 45 exact old→new ID mappings; it is **not applied** to master. `new-native-admissions-signed.json` binds the ICU shim to `3460435a`. Native gates with the local combined signed registry and static checks with the local signed admission table both **PASS** for the reviewed U13-based variants. This is not an active-master or production PASS. The outer must land these signed rows before replaying production gates.

Fresh slot ABI/calls checks against `7605812c` report **only `_ctype_` added, zero removed/drift/call changes and zero breaks across 219 consumers**. Against the planned U13 `d2053066`, 11 exports are added; the already-reported `__emutls_unregister_key` body change remains, with zero consumer breaks. `deployed_strings_diff` reports exit 1, **0 dropped / 1 added printable table projection** against v1; it is pending review, not silently allowed. Predictions retain **2 first-fatal targets** (McDonald's and Element past `_ctype_`, next unknown), **0 board-verified movement** and **0 Meet movement**.

The data-only `ctype_compat.c` is hashed in the source manifest but is not invented as a callable namespace profile: the scanner correctly rejects a profile with no function. Existing compiled Gecko/dlext profiles are rebound to v2; fresh binary open-site scans cover the linked ELF. The initial invalid profile reports are preserved privately, then corrected and rerun; no scanner rule was weakened.

`delta-review.json` retains the four pending changed open/namespace groups (plus the unchanged ICU checks). Bridge/host/Flutter delta hashes are unchanged. The ABI group's hash moves **`05ff6c8b`→`2127f19e`**, with the sole field difference `unknown:x1 clobbered by call at 0x3df0`→`0x3f30`. Disassembly and the empty v1/v2 ABI call diff support instruction-equivalent relocation; namespace API/literal deltas are unchanged. This is evidence for outer review, **not an automatic approval**.

The signed transfer explicitly records this data/layout consequence under the outer's v2 condition; no new open site, function, namespace literal or namespace API is allowed. The raw delta review remains available alongside the signed policy; no scanner diagnostic is removed.

## Exact image exception

Master `6f39eb23d6` approves draft `149dfe01` for the new nine-JAR input map (stubs `87cf65cc`), run1/run2 output maps and **only `[0x3e3b8,0x3e3c0)` in boot.art**. `image-approval-binding.json` records the signed file hash, full pair and actual masked byte comparison. The other 26 outputs must match exactly. Both bundles carry the exact outer approval file and binding metadata. The historical paired-build receipt remains byte-identical; its original invocation/status is not rewritten. This approval does not cover native findings, static deltas, JAR adds or the ICU admission.

## Parameterized finalization

Run from the lane worktree; paths below refer to persistent lane artifacts, not master-private `.artifacts`.

```bash
python3 benchmark/2026-10-03-u14-effective-rebind/finalize.py \
  --variant common \
  --transaction-base "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4" \
  --transaction-base-sha256 91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28 \
  --out benchmark/2026-10-03-u14-effective-rebind/.artifacts/common-new-attempt

python3 benchmark/2026-10-03-u14-effective-rebind/finalize.py \
  --variant 61b \
  --transaction-base "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-61b-effective-base/.artifacts/u13-61b-metadata" \
  --transaction-base-sha256 8861a11a843ac9c6278308b3c00dff4a4cfeaa08ca62e05125c7892d52d67262 \
  --out benchmark/2026-10-03-u14-effective-rebind/.artifacts/61b-new-attempt
```

`--abi`, `--abi-sha256`, `--abi-evidence` are an all-or-none combination for an arrived v2. Evidence must pin two identical persistent ELF outputs, successful build status, tee logs, source files, exact compiled scan-source mappings, toolchain identity and actual build commands. Only `westlake_native/libwestlake_native_abi.so` may change. Root/Flutter ABI aliases, all JARs, all 27 image members and the paired receipt remain byte-identical. Missing or mismatched donor evidence is rejected, never silently substituted. Output directories must be fresh; the first U14 packet is never overwritten.

For the selected v2, append these three flags to either finalization command:

```bash
--abi "$WORKSPACES/westlake-inputs/generations/u14-native-abi-v2/payload/android/lib64/westlake_native/libwestlake_native_abi.so" \
--abi-sha256 f8619ad5571c92cb3e9da3b8265ee41c17fa67db0a6aabeb9bfb89903e2a2239 \
--abi-evidence benchmark/2026-10-03-u14-effective-rebind/donor-evidence.json
```

After finalization, run `reports.py --variant common` and `reports.py --variant 61b`, `artifact_gates.py`, `slot_checks.py`, then `review_packet.py`. New manifest/inputs identities get fresh issue IDs and explicit old→new mappings; this code does not transfer pending outer approvals. The image bytes and historical paired receipt remain the first packet's exact objects. A future production replay additionally requires actual U13 promotion identity/signoff and outer approval; no activation or VM replay is provided here.

## Pre-promotion diagnostic replay

`finalize.py --baseline-mode diagnostic-t8` accepts only common **`190afedd`** or 61b **`c0adc4a9`** with explicit hashes. Disabled diagnostic bundles are **`5c099f09` / `4ff47436`**, in `.artifacts/common-diagnostic` / `.artifacts/61b-diagnostic`. Their native artifacts are the same U14 bytes; references and G1 comparison objects describe actual signed T8 instead of planned U13.

**Expected rejection, base not promoted:** T8 host `65cc3535`→U14 `341c1260` produces delta **`c818ed55`**, not approved U13 host `2a87118e`→U14 delta `f19b4a49`. Outer explicitly chose to keep this diagnostic refusal at 06:32, because U14's real transaction will use promoted U13. **No `c818ed55` exception is created.** Other T8/U13 increments remain visible in the raw diagnostic preview; the U13 policy is not silently used for different byte pairs. These diagnostic reports are not production acceptance.

The outer may run the following **after the current window**, substituting `vm` on Linux x86_64. Default invocation exits **78 before any probe**. The lane does not run it.

```bash
U14_PRODUCTION_REPLAY=outer-approved-after-window bash \
  "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/replay-production.sh" mac \
  "$WORKSPACES/westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle" \
  190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736 \
  "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/.artifacts/common-diagnostic"

U14_PRODUCTION_REPLAY=outer-approved-after-window bash \
  "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/replay-production.sh" mac \
  "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-61b-effective-base/.artifacts/t8-61b-base" \
  c0adc4a9147b0233f03bee75604b9e17509d10bca946032ef4ca9e7e0b061ff9 \
  "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/.artifacts/61b-diagnostic"
```

After actual U13 promotion, use BASE `91272eaf` with `.artifacts/common-reviewed`, or BASE `8861a11a` with `.artifacts/61b-reviewed`; their SHA parameters must match the reviewed composition. Do not pass a T8 base to a U13-bound package. Active native/admission registries and production gates are still the outer's responsibility; window authorization remains separate.

## Checks and handoff

Tests read only public JSON and pure validators, including wrong-variant rejection, installer identity/action rejection, unrelated artifact rejection and unapplied finding mappings. `landing-paths.txt` contains the code, reports, spec and Rust selectors; `.artifacts` is persistent but not landed. `documentation.json` provides root README/DIGEST increments for the outer lane.
