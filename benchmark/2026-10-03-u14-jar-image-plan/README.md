# U14 JAR and image preparation — NOT BAKED

## Correction and evidence

The native payload underlay is not the effective BCP. The accepted **U13 content bundle91272eaf** supplies nine effective JARs after overlays; `prepare_inputs.py` resolves them with `generation_bundle.bcp_members` and checks every SHA against its actual paired receipt. This content base is not a claim that U13 has been promoted. The eventual transaction base must be supplied from each board's signed effective identity (including the61b installer variant), never hard-coded from this plan.

Two ready JAR donors are pinned and copied into persistent, private snapshots:

| Input | SHA256 | Role / source |
|---|---|---|
| oh-adapter-runtime | `0349eb834e66bc1bf142fd31f08aa0c8a0536534e3ec6b01b5dcc1d930b0a0d4` | Non-BCP runtime loader; cc-t3 `2c70182c73`; replaces bbc3 |
| adapter-mainline-stubs | `87cf65ccff4eda56183f98de2eb8e7740db6b7725e429c6799a570ae0b39e73a` | BCP segment7 of9; `166b005c5d`; replaces615b; adds ScanCallback and ScanFailed |

`plan.json` gives each effective source, full SHA, size, ordered target and snapshot. The other **eight BCP JARs match U13 and the U12 paired receipt exactly**. Runtime0349 is not a tenth BCP input and does not itself require baking. Its eventual framework overlay and native inventory alias must both change in the same final assembly; this changes manifest/input bindings even though it is non-BCP. `source-snapshots.json` separates original source SHA from path-portable evidence-copy SHA. The source snapshots are provenance evidence, not standalone replacements for the donor's pinned build closure.

## What must be baked

Generate the entire **9 segments × ART/OAT/VDEX =27 files**, then publish stubs plus all27 as one stopped-parent atomic group. `expected-images.{json,csv}` lists every target and U13 comparison SHA. All U14 output SHAs are null; no bake or changed-file count has been invented.

- **3 expected changed:** boot-adapter-mainline-stubs.art/.oat/.vdex.
- **16 may change:** all remaining ART/OAT members, from cross-segment layout, compilation and embedded command paths.
- **8 expected unchanged, must verify:** the other eight VDEX members, whose DEX inputs are unchanged.

This is a forecast, not an acceptance allow-list or a hard3–19 change bound. The U12 historical bake changed11/27 against T8; that number cannot be reused for U14. Any unexpected difference needs analysis and outer review. Even unchanged output files remain bound to the selected bake's exact input/output receipt.

## Machine and frozen identity

**Selected machine: hw248 (Linux x86_64).** U12's persisted receipt proves two successful bakes there with the following exact frozen FZ-005 tools. Current remote availability/hash/dependency checks are **pending**, not remotely probed. Nothing uses a2hlab, including probes, during the U13 window. No need to queue behind that VM if hw248's fresh checks pass; if they fail, stop and report rather than silently substitute a compiler or machine.

| Tool | Persistent hw248 path | Full SHA256 |
|---|---|---|
| dex2oat64 | `$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64` | `ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b` |
| frozen t5 driver | `$LAB_HOME/cc-wiki-t5/tool/t5_gen_image.sh` | `14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46` |

**Do not use the repository's current t5_gen_image.sh (`05252808…`) as that frozen driver.** It is not the same SHA. `inputs/FZ-005.json` snapshots the registry entry with portable paths; `inputs/source/2026-10-02-u12-jar-r2-bake/` preserves the historical recipe/tee/BUILD/receipt/comparison. A fresh remote run must also record OS, architecture, `ldd`, resolved host-library hashes, actual compiler argv and live logs. Historic tool hashes are not a fresh machine check.

## Deferred execution handoff — do not run now

Persistent local input root:
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-jar-image-plan/.artifacts/inputs/`.

After explicit outer approval, copy its `jars9/` to hw248 `$LAB_HOME/u14-bt-bake-0349-87cf-v1/jars9/`, and copy this report's `inputs/`, `dex2oat-tee.sh` and `planned-bake.sh` to the same root's `plan/`. Keep runtime0349 in a separate `runtime/` directory, never `jars9`. Preserve `reference-u13/arm64/` for comparison. Do not upload this private root to a2hlab during the window.

The future commands, on hw248 only, are:

```sh
ROOT="$HOME/u14-bt-bake-0349-87cf-v1"
chmod +x "$ROOT/plan/dex2oat-tee.sh"
U14_PLAN_EXECUTE=outer-approved-hw248-only bash "$ROOT/plan/planned-bake.sh" 1
U14_PLAN_EXECUTE=outer-approved-hw248-only bash "$ROOT/plan/planned-bake.sh" 2
```

Without the explicit opt-in the script exits78 before checking any machine or making a directory. This opt-in is not a window authorization. Both runs use exactly `$ROOT/work` and identical incoming paths; run1/run2 names are **archive destinations only**, never dex2oat work directories. Each run records new logs, refuses to overwrite its output/log, tees the full compiler stream live, retains compiler and tee exit codes separately and tees the whole session under `$ROOT/logs/`. Do not stitch a failed or interrupted log into a retry; allocate a newly reviewed root and restart both runs. Persist the final selected run, unselected run, all9 inputs, wrappers, frozen tools' identities/dependencies and logs to both hw248 and a versioned Mac generation directory before assembly.

The historical frozen driver's L1 exit6 is expected when its old-image VDEX comparison sees one changed stubs segment. **It is not PASS.** Its internal pipeline must not hide dex2oat failure: the wrapper's separately written compiler/tee status must be0/0. The deferred script merely archives a complete27-file result, never declares deployable. Exit6 additionally requires the reported8/9 VDEX pattern and independent fresh gates below; any other reason for6 is a stop.

## Paired receipt and acceptance after baking

`paired-receipt.template.json` deliberately says NOT_RUN and has27 null outputs. `validation.check_receipt` rejects it. After real execution:

1. SHA all9 **actual compiler incoming** JARs, compare byte-for-byte to staged snapshots in BCP order. The receipt input map must exactly equal the effective final bundle's nine inputs, not reference images or underlays. Record compiler argv and hash every used host dependency.
2. SHA all27 nonempty selected run1 images. The receipt output map must exactly equal the final `boot_group` image map. Bind the receipt JSON itself by SHA in `bundle.paired_build_receipt`; bind it to the selected run1's actual logs, not run2's logs.
3. Require actual compiler/tee rc0, frozen ae865/14b1 hashes, command, `toolchain_identity_sha256`, actual `build_log_sha256`, session-log SHA and durable source locations. Resolve/read/hash the logs again; a complete-looking JSON alone is not proof. Run production `u7_executor.receipt_check` against the composed bundle.
4. Compare both27 output sets. Byte equality is the default. U12's comparator only checks the historical backtrace interval `[0x3e3b8,0x3e3c0)` in boot.art; **its T7d registry entry binds older inputs, so it is not automatic U14 approval**. If U14 differs there, first locate the sentinel/object in the new image, prove unchanged bytes outside it and ask for exact new paired identities/approval. Any different offset, size or file is rejected pending investigation. Never mask the whole ART image.
5. Run fresh RB gate (OAT230/image108/concurrent-copying=false), T4b against unchanged deployed libart59e1 and a genuine new BUILD receipt binding the selected boot.oat SHA; do not reuse U12's old oat binding. Preserve original frozen environment evidence, only add real execution metadata.
6. Run G1/G2 against the **explicit signed effective transaction baseline** and its exact nine effective JARs. Declare only adapter-mainline-stubs as swapped. G1 must also verify the selected image against candidate87cf inputs; G2 must read the actual `String#hashCode` compiled body and compare to the known-good baseline. Empty probes/host failures mean unknown/reject, never borrowed PASS.
7. Fresh `deployed_class_diff --frozen` for runtime and stubs against that actual baseline, exact allow-add review, final frozen group review and FZ-005 identical-tool/image binding. Recompute manifest/inputs, N1/N2/static IDs and approval transfers only after actual outputs exist. Then fresh Mac/VM production dry-run; VM after the current window and outer-owned. No historical grant is a U14 grant.

Rollback is the **complete actual per-board prior image+stubs group and prior runtime JAR**, together with the composed native prior aliases. U13 is an assembly-content source until independently promoted;61b's51e1 installer pair remains board-local and unchanged.

## Native input slots, not a second native version

`native-slot-inputs.json` is the next input ledger; the historical bridge-only90de bundle and reports are immutable. It stages the accepted host341c double build into a persistent private snapshot, with the original A-prime **semantic** reproduction approval (`77dc6c6251`), not a false byte reproduction claim. The intended public library list excludes libz/androidio/javacore, preserving the existing private-zlib routing.

The remaining native releases arrived while preparing this plan. Full published SHA values were checked against the actual files before copying, not inferred from a short hash. All new slots still have `applied=false`: final single-version native composition waits for the new image outputs and fresh gates. Bridge7daa remains the already selected input. JAR0349/stubs87cf are ready inputs; their image slot is NOT_RUN.

| Filled native input slot | Full SHA256 | Scope |
|---|---|---|
| Flutter libandroid | `fff9be3190f1b1c99c3fd4559d258cbac131fb657d10b1fa7060f61c4002d5e5` | `$WORKSPACES/westlake-inputs/generations/u14-flutter-libandroid-v1/`; only westlake_flutter, never westlake_native/root libandroid |
| Gecko native_abi FINAL | `7605812cc5249534950bb0533baa3199b380daf6e763af12ed216c2c70649515` | `$WORKSPACES/westlake-inputs/generations/u14-native-abi-gecko-v2/`; only westlake_native; root/Flutter d205 unchanged; superseded8688 rejected |
| ICU libicuuc | `9b36b989dd10f29434cc60b6b7d1895878442d07f1d6b0674db9b1379420d93f` | `$WORKSPACES/westlake-inputs/generations/u14-icu-wall2-v1/`; existing libicuuc.so and libicuuc.z.so inventory aliases must stay identical |
| ICU new dependency | `4886bc5c2b4ef0486ecda6fa3248ace4af6a1c57ed7029b17cfd4868ad2c92af` | same ICU release; new libicu74compat.so needs explicit admission and closure/single-owner proof |

ICU was initially held because binaries had not been retained. After the donor recreated and persisted the exact accepted objects with logs, this lane staged those bytes only: **no local rebuild**. Component source/tee provenance remains at the published donor/master reports (`8b4769aeeb` / correction `8e0d415721`, `bf00e19466`); the input ledger includes full source and private snapshot paths. The Gecko fidelity comparison used by the donor is554b, whereas the effective U13 native_abi isd205: fresh input scans here explicitly compare to **d205**, not to the donor's reproduced comparison ELF. A donor gate is not a composed U14 gate.

`static-input-checks.json` retains fresh Mac read-only input checks. Host baseline2a871 versus341c has8 open sites/17 namespace edges in both; INHERIT-REPEAT=0, four syntactic INHERIT-AFTER-OPEN may-path findings in both (PCs move), DEFAULT-NS/MULTI-NS remain visible, not waived. Raw strings exit1 shows2 dropped build-source paths and4 adds (two replacement source paths, the intended six-soname string, and a printable readonly pointer fragment); this is **not** a zero-difference PASS or a newly approved allowance. Final composition must retain/review that raw evidence. Runtime/stubs `--frozen` raw exit1 each means exactly3/2 added descriptors, zero drop/reshape/frozen violations; exact allow-add binding remains part of final assembly, not silently broadened here.

Flutter/Gecko/ICU pairs also get fresh open-site and readonly-string scans against their exact U13 inventory bytes; raw flags and namespace findings remain in evidence. The newly added ICU shim has no deployed counterpart, so it is scanned as a new library and is not compared to a fabricated empty ELF. N1/N2, ABI/calls/consumer and production reports for the full U14 package are **not yet run**: no complete package exists before the reviewed image bake. All raw input changes remain review material, not implicit allowances.

Fresh input counts: Flutter0→7 sites (bridge/runtime NOLOAD only; platform EGL has two ordinary fallback opens), strings1 drop/22 adds; Gecko d205→7605 sites0→2, strings0 drop/7 adds; ICU1→1 site and strings0/0; new shim0 sites. None creates a new namespace API edge. The Flutter raw drop is a string-pool prefix on the existing OPENAT2 log; retain it for exact semantic review rather than pretending the raw tool returned0. FULL native approvals must still bind the finally composed manifest.

## Checks and limits

The cold-safe unit checks exercise input maps, exact image set, pending receipts, failure statuses, bounded exception review and native slot readiness. They do not run dex2oat, clang, SSH, OrbStack, HDC or a production executor. `landing-paths.txt` excludes private binaries, JARs and images. Tool output and preflight are archived under evidence. No builds, registry changes, production replay or board writes occurred.
