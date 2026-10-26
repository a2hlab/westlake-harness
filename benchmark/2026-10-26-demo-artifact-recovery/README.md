# Worktree-independent demo artifact recovery

**10,513 files / 2,942,886,157 logical bytes / 8,576 unique SHA256 objects were recovered from an independent SSH server into a new directory.** All restored bytes, sizes and modes were independently checked with zero mismatches. The independently selected historical runtime set is **711/711**, with no missing member. See [results.json](results.json), [the immutable manifest](intake/manifest.json), and [the user runbook](../../knowledge/artifacts/README.md).

## What was wrong and the new rule

Having a `.so` in a worktree, an old build directory or a server path did not prove that someone else could recover the same demo. Same-named libraries could differ, build recipes referenced private paths, and verified binary recovery was easily confused with complete source reconstruction.

The new rule is: **publish immutable SHA-addressed objects and a versioned manifest; recover from the server with original local sources unavailable; state source-rebuild gaps separately.** Never delete a worktree merely because one demo release has been archived.

## Accepted release and evidence

- Release: `61b-t150-3291-intake-20261026-03`.
- Manifest SHA256: `362726c48e03589392bb0f3ab6e233b9a9f2fc18a2ed99d19544343a41b6295b`.
- Native candidate: `3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819`; rollback: `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4`.
- Signed host HAP: `b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`.
- Recovery tools and manifest were obtained from a **fresh GitHub clone**, commit `cedeabe93880ba43c1b798c63e442116813fde56`, outside the original workspaces.
- macOS `sandbox-exec` denied reads from all original workspaces, the original local CAS and the intake directory. Three explicit read probes returned `PermissionError` before recovery.
- Actual server download, complete verification and atomic restore succeeded in approximately **172 seconds**. No local fallback exists. All 10,513 restored files subsequently passed an independent SHA/size/mode check.
- A separate missing-object remote fixture failed with rsync rc23 and fetch rc1, even though the matching original object existed locally. No completed destination was created.
- After acceptance, the newly created remote store was moved to the repository's documented persistent artifact parent on hw248. All objects were reverified there; the candidate, rollback and signed HAP were fetched again from that final location into another empty cache and destination under the same isolation.

Raw transfer logs, command return codes, sandbox profile/probes, original receipts and the independent restored-file check remain private. [raw-index.json](raw-index.json) pins their bytes and remote audit locator. Private APKs, build logs and historical personal paths were not committed to this public repository.

## Build provenance and remaining gaps

[Intake README](intake/README.md) explains the independent inventory, source anchors, exact T59 `run.sh` recovery and input relocation. [build-status.json](intake/build-status.json) records each component's recovery and rebuild state.

The archived native build closure includes five compilation units, original successful compile/link logs, 8,042 SDK entries, 792 libcxx headers, 658 non-system dependencies, 452 indexed inputs, 113 explicit link inputs and seven pinned tool/runtime files. **103 reused link inputs comprise 46 `.o`, 56 `.so` and one `.a`**; these are not 103 newly rebuilt source units. Private path and symlink/materialization maps are themselves included in the release, so they survive deletion of the intake machine.

This task performed **zero new compilations and zero device writes**. The historical candidate can be recovered exactly; a relocated rebuild has not been executed here. Rebuilding every reused input, legacy runtime library, JAR/boot image and the complete HAP signing environment remains unproven. Third-party APK source is not supplied.

## Validation and scope

- 11 actual CLI store scenarios; 9 fetch boundary tests; 5 server publication tests; 4 intake checks, exercised through three Rust contract wrappers.
- Contract lint passes. The raw verifier run against the repository root could not discover the Rust test package and reported skipped scenarios; it is retained as a failed attempt. Lifecycle checks use the actual package under `tools/spec-checks`; all 11 bound scenarios pass (4 store, 3 intake, 4 remote recovery), with final status recorded in results and the private audit.
- Current-device-wide identity, reinstalling an entire blank board, a physical second Mac, automatic scheduled backups and a third independent offsite copy are **not** claimed.
- Original worktrees were kept. This release certifies the declared demo artifact subset, not the completeness of every experiment or source branch on the machine.

## Tools

`scripts/lab/artifact_store.py` ingests, verifies and restores manifest objects. It does not hardlink original source files, overwrite a release ID, or overwrite an existing restore directory.

`scripts/lab/artifact_publish.py` verifies local input, uploads to a private remote quarantine, checks final-store bytes and publishes the release manifest last. Existing corrupt objects are rejected, not silently overwritten.

`scripts/lab/artifact_fetch.py` starts with a new cache/destination, downloads only requested SHA objects, verifies them and restores. A failed transfer cannot be repaired invisibly from a source worktree.

No additional artifact-management service was installed. Existing SSH/rsync infrastructure carries private binary objects; Git mainline carries code, manifests, source/build references and explicit gaps.
