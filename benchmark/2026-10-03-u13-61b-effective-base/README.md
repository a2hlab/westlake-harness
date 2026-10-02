# 61b effective T8 baseline: fix reference metadata, not the installation service

**The wrong assertion was in U13's `reference/runtime.txt`, not native output bytes.** Its two libinstalls lines asserted the common 5ea/5cd `2c9a5294` on61b, overriding native-baseline preparation. Native files/live_hashes/prerequisites contain neither service path. Copying an ELF into a native payload would not fix that reference and would introduce an unwanted service operation.

Outer explicitly approved the corrected **reference/binding-only** approach in the asynchronous reply. Original authorized `91272eaf` stays immutable; no board was accessed, no service/installer changed, no source rebuilt, no registry edited, no VM used, and no deployment occurred. This metadata variant needs outer fresh production replay and renewed authorization; its offline gates do not authorize a window.

## Identities

| Object | SHA256 |
|---|---|
| Original common effective T8 bundle | `190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736` |
| **61b effective baseline evidence variant** | `c0adc4a9147b0233f03bee75604b9e17509d10bca946032ef4ca9e7e0b061ff9` |
| Original authorized U13 | `91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28` |
| **61b U13 metadata-only candidate** | `8861a11a843ac9c6278308b3c00dff4a4cfeaa08ca62e05125c7892d52d67262` |
| Candidate native manifest, unchanged | `85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6` |
| Candidate native inputs, unchanged | `c40faa79d197f023dbe47a62ae186d5eb5671f9b8f4a448924098fdd5f02f185` |
| Source libinstalls, already signed on61b | `51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5` |

Persistent roots, under this lane's worktree:
- `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-61b-effective-base/.artifacts/t8-61b-base/`
- `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-61b-effective-base/.artifacts/u13-61b-metadata/`

## Source, not a new board pull

The exact source-built artifact is `$WORKSPACES/oh61-bms-kit-b79/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so`, 1,285,752 bytes; this run read and SHA-verified it locally. Earlier #79 validation and the installation reconciliation already establish its lineage: source patch `22de5ddb52212f3640a7214194472e30991e0c65`, validation `70fc62aa7e0369427f4ba22b1d370d2a58496eab`, final persistent archive SHA `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`. See `evidence/source-lineage.json` and master `benchmark/2026-10-02-libinstalls-unification/`; archive/source provenance is reused as already verified evidence, not claimed newly rebuilt or newly measured service mapping.

The two paths are `/system/lib64/libinstalls.z.so` and `/system/lib64/platformsdk/libinstalls.z.so`. `evidence/executor-refusal.json` captures the pre-apply refusal. Signed recovery and candidate maps both already specify51e1 on61b. Default `deployed_whois` covers historical runtime packages and app maps, not the installation-service owner; its absence of this service is not an absence claim. Both pinned copies are retained **only as baseline evidence**, outside native mounts/payload, with explicit hashes in the baseline bundle's `board_local_baseline` metadata. No new native admission, mount, prerequisite relaxation, search-path change or service upgrade is introduced.

## Exact metadata delta and critical experiment

`file-delta.json` hashes every original/variant file:
- Candidate changes only `bundle.json` and `reference/runtime.txt`: precisely two runtime assertion values change2c9a→51e1; static and image-reference baseline bindings target the61b variant, and metadata limits transaction scope to61b.
- The baseline evidence variant changes only its bundle/runtime-reference metadata and adds two SHA-bound evidence copies of51e1 under `native/board-local/...`. Its original native manifest and gate inputs remain byte-identical.
- All output artifacts, every native manifest/input, JAR, image and policy file remain unchanged. Original912 also retains its full SHA. The existing expected-per-board support file was already correct for61b and remains byte-identical; it was the shared executor reference that was wrong.

Fresh `executor.prepare` against the variant BASE produced **316 baseline / 319 candidate paths**, both dictionaries exactly equal to the independently signed61b maps. **Three additions, 40 changes, zero service actions**. Each service alias is51e1 in both baseline and expected, absent from additions/changes. Baseline runtime fingerprint is **`d6848fa2c989`,123 paths**, boot **`e3806b65a079`,36 paths**; candidate fingerprints remain the previously signed target predictions. See `critical-result.json` and `transaction-plan.json`. No identity selector was narrowed to make this pass.

## Fresh local gates and outer replay

Fresh Mac `reports.py` checks the original and variant against their respective baselines:
- Static **PASS/PASS**, every member comparison unchanged after substituting only the two package-root paths in diagnostics. Raw reports remain untouched and contain their own new bundle/base bindings.
- Original native identities remain active: baseline and candidate N1/N2 both **PASS**, no new finding, no exception transfer or new admission needed.
- File delta and signed full maps pass; production and VM status remain **pending**, not borrowed from the original190 replay.

Outer exact commands, after reviewing the new metadata identities:

```sh
bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-61b-effective-base/replay-production.sh" mac
bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-61b-effective-base/replay-production.sh" vm
```

The wrapper checks actual OS, source/evidence hashes and the signed316/319 maps before calling the real master executor with **`--dry-run --package .../u13-61b-metadata --baseline-native .../t8-61b-base/native`**. It records original command output and tool-bound production results in `.artifacts/raw/`, portable `evidence/`, and `gates/{mac,vm}.json`. It never locks a board or deploys. This lane does not invoke the VM branch during the ongoing window.

Executor/cx-t0 should use these variants only for61b after outer re-signs the metadata package. Keep5ea/5cd on their original common190 / authorized912 pair; do not unify installers under cover of this fix. Promotion/rollback maps preserve the existing51e1 service aliases. The custom metadata scope is documentation plus a wrapper check, not a substitute for executor authorization and board whitelist.

## Portable validation

`python3 benchmark/2026-10-03-u13-61b-effective-base/test_base.py` and Rust selector `u13_61b_effective_base` validate maps, two reference lines, disabled state, hashes and negative service-action/drift cases without private binaries. Landing cold checks run using only listed files. Tests do not claim G1/G2 or screenshot success; fresh outer production outputs must be reviewed before window authorization.
