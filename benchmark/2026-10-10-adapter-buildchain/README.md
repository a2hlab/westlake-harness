# Native build chain: runtime187 reproduced twice; adapter846/8ab BLOCKED

Previously wrong: “the repository only has an armv7 bridge script” was too broad. An older arm64 script exists in `real-work/src/adapter/sources/oh61-v7-b2133b5b/build/inner/compile_oh_adapter_bridge_arm64.sh`. Its existence is not proof that it produced either retained target. Likewise the Boat runtime run contains the desired adapter as a **link input**, not as its bridge build output. This report preserves that distinction.

No board was written during t2c. Before starting it, 61b was unlocked at 10:27:04; the parent was running but HW/ZZ children still failed seccomp. cc-t3 took over that independent recovery. No adapter, patched binary or frozen revision was produced by this task.

## Pinned target evidence

| Object | Full SHA256 | Bytes | Build ID | Defined dynamic symbols |
|---|---|---:|---|---:|
| U13 bridge | `84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a` | 2,271,208 | `e5e9bd8330f6ebe81e59cd1e93a862c8c6ad7115` | 2,357 |
| Boat PASS bridge | `8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e` | 2,274,648 | `827eb26b8bf3461ac6b047d09099f40947826cff` | 2,359 |

`target-identities.json` and `evidence/{u13,boat}-{dynamic,notes,sections,comment,symbols,translation-units}.txt` retain actual LLVM readbacks. Both have the same ordered **35 DT_NEEDED** entries, SONAME `liboh_adapter_bridge.so`, and **53 STT_FILE** witnesses (including CRT). These are binary metadata, not original source content hashes or the exact link command.

Local original bytes remain at `$WORKSPACES/vm-copies/bridge-84695d62/liboh_adapter_bridge.so` and `$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-09-demo-boatattack/spare-5cd/overlay/liboh_adapter_bridge.so`. Remote originals remain read-only at `hw248:/home/alvin/westlake-oh6.1-lab-state-20260930/vm-copies/bridge-84695d62/liboh_adapter_bridge.so` and `hw248:/opt/build-runs/boatattack-runtime-source-20260813T141442Z/private-aosp-lib64/liboh_adapter_bridge.so`. No large binary is committed.

## Search order and limits

`search-log.json` records Mac → OrbStack → hw248, followed by bounded cross-checks. Mac searches covered the named real-work, 00.Workspace, games-ad1ab0a7, vm-copies and westlake-inputs sources; filenames were also searched across workspaces. VM searches covered the westlake historical bridge directory and docs plus ws/source-closure roots. `rg` is absent in this VM: the first grep used absent old doc/var paths, then the corrected `docs`/historical search returned no matches. Raw outputs record these failures; they are not silently interpreted as an exhaustive absence claim.

Remote queries were limited to the named Boat/Fn02/frozen-v7 runs, `/home/alvin` archive names and depth 2–5 paths. This is **not** a whole-disk or all-tarball source search. No upstream download was attempted: the missing inputs are locally modified adapter source/patch/object/link provenance, not a known upstream tag. A stock download cannot supply them.

## What was recovered, and why it does not pass

1. The old arm64 recipe and wrapper are copied verbatim as non-executable historical text in `evidence/old-arm64-{recipe,wrapper}.txt`. It globs six JNI groups, adds `fn03_lifecycle_core.cpp`, and takes canonical package-manager sources **outside the frozen directory**. `partial-source-inventory.json` pins **469** current source/header witnesses. It is explicitly partial; this inventory is not a target-era source snapshot.
2. The old v7 source receipt names `bc878f4f80f2883173291b96adf1399fcf2e2020ab8dd9c17be77bea9a75543e`, size 2,523,696, build ID `59cfed9cc1f2cb1ef6e18b7639d02df9262ff08a`, not 846/8ab. See the prior `benchmark/2026-10-01-bridge-846-provenance/README.md` and `real-work/docs/discussions/2026-08-03-blank-screen-root-cause-window-protocol.md:86–105`.
3. Boat run `recover-old-bridge/build.env` targets `/opt/build-runs/fn02-abi-fix-20260730T1935Z/adapter`, with an unavailable `clangxx-fn02-degraded` wrapper. Its retained **raw** `build.log` says **62/62** source compiles and strict linking. The retained result is **089bebe7daf609bd190c15ee48f989b5a083e9c289a4c155ad16c116cfbb4a3d**, build ID `91945a5af7d105d3135190a4c144d2840d655b86`; **8ab remains a separate private-aosp-lib64 input**. No claim connects that log to the 8ab bytes. Original log/objects/output stay on hw248 in that run.
4. The other old Fn02 v7scb output is **216d15a3**, also not either target. Historical `/opt/10.Project/...` roots and `/opt/build-trees/adapter` are absent. Evidence: `hw248-old-builds.txt`, `hw248-boat-source-markers.txt`.

## Differences, not a substitute reconstruction

`historical-difference.json` compares the existing 089b build metadata to U13: **2,391** exports vs **2,357**; **271** U13 exports absent, **305** historical extras. It has **65 STT_FILE** witnesses vs **53**, lacks `fn03_lifecycle_core.cpp`, and adds 13 other TU names. DT_NEEDED order differs, including additional nativehelper/hwui/begetutil dependencies and different placement of libc/libc++. Exact compile argv, object order and target-era link flags remain **unknown**, not reconstructed from DT_NEEDED. This historical output is rejected, never patched or rebuilt here.

The target-to-target `abi_diff --calls` readback has **0 removed exports, 2 added, 0 signature drift**, and **2 common functions with changed named-call sets**: `AbilitySchedulerAdapter::ScheduleAbilityTransaction` and `oh_rs_get_child_surface_window`. Boat adds the UNITY-LANDSCAPE and initial/resize geometry strings. Evidence: `target-abi-calls.json/.txt`, `target-strings-diff.txt`. Call-set equality elsewhere does not prove instruction equality or identical semantics; the string tool also reports binary-noise strings, which are not treated as source evidence.

## Frozen local toolchain, actual probe

The cx-build image is `sha256:12ffb9324ca4df6427cbf6a6da0ac8ce575599291e933724275fce704520db63` (`a2hlab-build:24.04`). Actual container execution, tee'd into `frozen-container-probe.txt`, succeeds. `toolchain.json` pins clang **b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913**, LLD **8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4**, sysroot libc **ab5ad48a82295e6ec144aaac730bfa053e744e4903c01d51707ce0935385d905**, and cx-build's complete tool/sysroot inventory receipts. No shared VM/Docker service was restarted.

The two targets record clang 15.0.4 **llvm 99548401bd80576251755b185ab95945e5fe7884**; frozen b107's actual version is **feef13a36e78b7a2ff3e9e3f180a958f2782be1e**. Same major version is not exact toolchain provenance. This is a measured difference, not proof that it alone causes every byte difference. Original flags and contributing objects are missing; no options are invented to erase this difference.

## Rebuildability fence and registry

`knowledge/gates/rebuildable-artifacts.json` initially registers the three explicitly requested identities: adapter846, adapter8ab and runtime187. The two adapters remain conservatively **locked**, with provenance and named gaps; runtime187 is now **reproduced** from two independent clean output/object directories (see the final receipt below). This is not certification of every U13 member and does not alter existing deployment/freeze/admission gates. The missing runtime TU was actually recovered at `$WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp`, SHA **ba5a3fe23d4a72f0406427e38b51259cc7c8fd0d04a7c78237d9f6d3fccac210**; The 10:55 reassignment transfers its clean two-build reproduction to cx-t0, after 5ea recovery. Finding the TU is not a reproduction verdict.

Commands (offline):

```bash
python3 benchmark/2026-10-10-adapter-buildchain/test_rebuild_gate.py -v
python3 benchmark/2026-10-10-adapter-buildchain/rebuild_gate.py --preflight
python3 benchmark/2026-10-10-adapter-buildchain/rebuild_gate.py --require-reproduced
# When two actual cold-build outputs/logs exist, compare them; mismatches return rc=2:
python3 benchmark/2026-10-10-adapter-buildchain/rebuild_gate.py --compare TARGET R1 R2 --readelf LLVM_READELF --report diff.json
```

Both aggregate gates still return **rc=2** for the adapter gaps; the runtime-only `--require-reproduced` gate returns **rc=0 / PASS** with no errors; neither executes a build or creates an adapter. Table absence/parse failure, changed pins, reused clean directories and changed logs fail closed. Tests include actual target metadata and synthetic clean-build/comparator positive cases; **fixtures do not establish target reproduction**. The Rust selector `demo_baseline_adapter_buildchain` runs these support tests only and explicitly prints `OFFLINE_GUARDS_ONLY`. The earlier lifecycle returned rc=1 with six SKIP verdicts (no verifier coverage). At resume, master initially rejected the inherited project heading (`contract-resume.txt`); upstream subsequently fixed that parse problem. The final selector now requires actual paired reproduction receipts, so fixture-only PASS cannot falsely certify exact bridge builds. Support tests pass (12 + 2), but the real selector returns rc=101 and final lifecycle rc=1 / quality 1.0 / all six shared-selector scenarios FAIL (`lifecycle-final.json`). No spec was edited here.

Actual acceptance: search-order and missing-input stop are verified; exact source/patch/sysroot/link input pinning and two target-equal clean builds are **BLOCKED**. Difference reporting uses an existing historical artifact, not a new reconstruction. Final t2c verdict remains **blocked**. Resume only with the exact 846/8ab source/patch/object/link receipts and the target-era toolchain identity, or an explicit contract change. No marked replacement is emitted.

## Reassignment checkpoint (10:55)

5ea recovery is now first priority. The adapter investigation resumes afterwards, with a 14:30 cutoff; runtime187 reproduction is transferred to cx-t0. This checkpoint is not the final reproduction receipt.

## Final runtime187 reproduction (after 5ea recovery, before 14:30 cutoff)

The earlier `3a316fea` result was not proof of irrecoverable source drift: the retained
recipe already has the publication switch, and the original driver did not export it.
The TU was found locally, and U15's historical relink report independently records
`N3B_WITH_PUBLICATION=1` (that report used retained objects, so it was not a cold build).

`runtime-reproduction.json` and `runtime-comparison.json` record **R1 = R2 = deployed
18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae**, 3,194,328 bytes,
build ID `28672ee74c9a759dd3af5616d9800658ce43d858`. Both actual compiler/tee pipelines
returned **0**. Each run began with a non-existent output directory, generated AIDL
and input labels, compiled sqlite and all runtime sources, and rebuilt all four GL
and six Emboss objects. **71/71 linked objects** in each run equal the retained
historical objects; none was consumed from the old object cache. Original source
paths and flags are unchanged. Only output paths and the recovered publication
input selection change. No patched replacement or board write was made.

Reproduction preparation (requires the retained/archived author-path inputs and
pinned container; always use a new output directory):

```bash
REPRO_RUN="$WORKSPACES/westlake-inputs/generations/t2c-runtime-reproduction-20261010/next-cold-run"
python3 benchmark/2026-10-10-adapter-buildchain/prepare_runtime_cold.py --workspaces "$WORKSPACES" --out "$REPRO_RUN"
set -o pipefail
DOCKBUILD_MOUNTS="$WORKSPACES/westlake-harness-bms-deploy:$WORKSPACES/westlake-harness-t3"   "$WORKSPACES/westlake-inputs/tools/dockbuild.sh" run -n t2c-runtime-next --   bash "$REPRO_RUN/run.sh"   2>&1 | tee "$REPRO_RUN/build.log"
python3 benchmark/2026-10-10-adapter-buildchain/rebuild_gate.py   --artifact runtime-u13-18763dd4 --require-reproduced
```

`prepare_runtime_dependencies.py` runs separate dependency-only compiler invocations;
it does not substitute their results for the actual cold-build receipt.
`archive_runtime_inputs.py` preserves the 71 compiler dependency witnesses, complete
actual sysroot/libc++ header trees, source/generator inputs, tool/link inputs and
scripts. The **6,347-file** inventory and **465,446,236-byte** input tar are pinned in
`runtime-archive-receipt.json`; this is a dependency closure, not an entire upstream
checkout. Standard Ubuntu host libraries come from the pinned Docker image. Original
GL DWARF retains author-path spelling, so moving that path can change bytes.

The R1 preparer initially redirected object output but missed n4's one-line hash
receipt, briefly overwriting `egl-object.txt` with the new output path. Initial
tracked status showed that file clean; its exact original tracked bytes were
restored, and the source/object were never altered. Published preparation and R2
redirect both n2/n4 hash receipts to their new output directories; safety tests
verify this and reject reused directories.

Large archives, every original `.err`, compiler stdout/stderr, intermediate objects
and outputs remain outside Git. Their remote SHA readbacks and exact locations are
in `runtime-persistence.json`. The incomplete initial archive is explicitly
superseded; it is not used by the rebuildability row. Final diagnostic registry
scope is still only the three requested members, **not all 319 U13 paths**.

**Disposition:** runtime187 is verified and unlocked for source reproduction;
adapter846/8ab remain locked. The complete t2c exact-adapter criterion is blocked.
At the deadline there is no reason to emit an approximate adapter, guess flags,
change a frozen item, or use the historical 089b artifact as a replacement.
