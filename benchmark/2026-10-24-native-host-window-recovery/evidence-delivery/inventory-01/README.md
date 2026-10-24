# T127: source/build delivery inventory (offline subset of t5)

**Required source/build material is present in the inspected persistent local roots: zero missing files and zero SHA mismatches.** This is an availability inventory, not a new build or a device result. Snapshot02 source-built **five translation units**, then linked them with reused baseline objects. It is **not a whole-bridge source rebuild**. The target is **3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819** (2,154,616 bytes); snapshot01 `158c1740…` is historical.

## Exact source → build → artifact index

| Unit | Source (SHA prefix) | Actual outer build receipts | Output (full SHA256) |
|---|---|---|---|
| wmc | `$SNAPSHOT02/candidate/oh_window_manager_client.cpp` (`418235c14fa0`) | `$SNAPSHOT02/wmc/argv.json`, `receipt.json`, `stdout`, `stderr` (rc0) | `$SNAPSHOT02/wmc/wmc.o` (`d2e550c14570e5823e66d86870ed674973311bb28f445f88d133a54b3796b46b`) |
| input | `$SNAPSHOT02/candidate/oh_input_bridge.cpp` (`5e814a7d8c51`) | `$SNAPSHOT02/input/argv.json`, `receipt.json`, `stdout`, `stderr` (rc0) | `$SNAPSHOT02/input/input.o` (`b6e7b7792b59a0623b349ed72997308011efe238170d8b2d6d28d19acc088ea5`) |
| stage | `$SNAPSHOT02/candidate/session_stage_adapter.cpp` (`9fdb24b064c3`) | `$SNAPSHOT02/stage/argv.json`, `receipt.json`, `stdout`, `stderr` (rc0) | `$SNAPSHOT02/stage/stage.o` (`89a530f3f42b4387d4994830b9476ae152cc92f9537c3dbcd62609197c45f50c`) |
| core | `$SNAPSHOT02/candidate/session_recovery.cpp` (`5cd59abf8a7e`) | `$SNAPSHOT02/core/argv.json`, `receipt.json`, `stdout`, `stderr` (rc0) | `$SNAPSHOT02/core/core.o` (`032f0987df213dcf86fa06a2d81c9b644a17cbaa816503746615c86dfb37cf57`) |
| reader-build | `$SNAPSHOT02/reader/host_window_record_reader.cpp` (`29eb5ba7519f`) | `$SNAPSHOT02/reader-build/argv.json`, `receipt.json`, `stdout`, `stderr` (rc0) | `$SNAPSHOT02/reader-build/reader.o` (`f2ec096821bc2482d9c7105cff24589b5b99a12229d836047343df03e40713ce`) |
| link-01 | `Five new objects + unchanged baseline link inputs` (`indexed in results.json`) | `$SNAPSHOT02/link-01/argv.json`, `receipt.json`, `stdout`, `stderr` (rc0) | `$SNAPSHOT02/link-01/liboh_adapter_bridge.so` (`3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819`) |

Each row's complete source/output SHA, sizes and all argv/receipt/stdout/stderr hashes are in [results.json](results.json). Five compile receipts and the Mac link receipt report rc0; the original streams exist and were hashed. The five compiles ran with the Linux compiler; the complete link used the Mac linker. This lane ran neither.

## Storage and reproducibility boundary

- **In the repository:** all13 candidate/accepted-reader source/license files match both snapshot02 source pins and actual main HEAD bytes. Review02 manifest SHA is `f156d990caff276ce456027098d23fa0e9558530adaaf26319c2e0af5a4b220c`. The common recipe, candidate-build-02 actual argv delta, source closure and build/raw indexes are available in main. The inspected main commit is recorded in results; the task reference was5970ec078c.
- **Local persistent private bytes:** all57 snapshot02 indexed files match their published SHA; five objects and the final library are at `$SNAPSHOT02`. Actual commands reference113 explicit link files (including the compiler driver), all available;103 unchanged staged inputs match baseline pins. All other explicit entries, including five candidate objects and the driver, have current hashes in the index; no full-source claim is made for reused objects.
- **Toolchain and dependencies:** Linux clang-15/lld and Mac clang++/ld.lld match the existing pins. The three copied Mac SDK dylibs have current hashes. All8042 fixed SDK manifest entries,792 restored system headers and452 Input/stage source-closure entries match their existing manifests. The five actual `.d` files resolve658 unique non-system dependency paths, all available with current SHA recorded. `-MMD` is not treated as a complete system-header inventory; SDK/system-header manifests are checked separately. These checks do not audit the entire host OS.
- **Archive fallback:** the existing local T18 archive is available at the exact location/hash in results. No archive was extracted, and no network or remote host was contacted. No required material is available *only* as an unverified remote listing in this inspected chain. Off-host replication of snapshot02 is **unknown**, not inferred from local index files.

The preparation tools list also mentions `llvm-readelf`, which was not copied into staged `mac-tools/`. It is not used by any of the six actual build commands and is not a build-material gap. This optional diagnostic difference is recorded separately rather than inflating missing items.

Aliases: `$SNAPSHOT02=$HOME/.local/share/westlake/native-host-recovery-build-20261024/snapshot-02`; `$STAGE=$WORKSPACES/westlake-harness-t4/benchmark/2026-10-24-wmc-build-preparation/staging-01/.private/staged-03`; `$MAIN=$WORKSPACES/westlake-harness`. Existing main references: `candidate-build-01/recipe.sanitized.json`, `candidate-build-02/{raw-index,recipe-delta}.json`, and `benchmark/2026-10-24-wmc-build-preparation/{tools,link-inputs,compile-dependencies}.json`, plus `staging-01` and `source-binding-02` indexes. Full paths and SHA are in results.

## Missing items and final state

No additional required source/build file gap was found in this bounded inventory. The already-known t3/t4 actual device receipt gap remains; this task did not revisit the board. **t5 final is pending**, its selector is not implemented, and no actual loading, feed, repair, API freeze, seal or remote publication is claimed. Runtime, API historical SHA, existing source, manifests and stopped objects were not modified. Public delivery is exactly the three paths in [landing-paths.txt](landing-paths.txt).
