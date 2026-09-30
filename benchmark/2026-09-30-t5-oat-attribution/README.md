# T5 OAT attribution and R155 build switches

The prior diagnosis was wrong in two ways: the SHA-matched R155 **primary boot image never contained `bootclasspath-checksums` or `compilation-reason`**, and the delivered T5 files are **not** the earlier `31a3e81e`-checksum run. The supplied T5 `boot.oat` is SHA `08837079…`, checksum **`0424c4ee`**; it has the same eight keys, but **`concurrent-copying=true` versus R155 `false`**. All **9/9 `.text` sections differ**, including all eight secondary OAT files whose key-value regions are empty on both sides. Removing a metadata key cannot fix this set. [t5-comparison.json](t5-comparison.json), [residuals.csv](residuals.csv).

The required T3b build settings have stronger evidence than a KV inference: R155 `libart.so` **`59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f`** rejects a true read-barrier OAT flag and defaults to **CMS**, not r1's default CMC. [build-flags.csv](build-flags.csv) covers 16 observations: **11 verified, 1 source-derived, 4 unknown**. “Verified” refers to the stated observable value, not recovery of the exact original shell environment.

## Inputs and residuals

- Reference: workspace `westlake-generation-v3a-74d1d6d4-r8b/payload/android/framework/arm64/`; all **27/27** files match `westlake-harness/knowledge/toolchains/boot-image-inputs.sha256`. Reference primary OAT SHA: `25d92cf7df9c86ca4bbc81c1e2f44a5c6c64798506247239e07a30f651b9e78c`.
- Candidate: outer-loop copy `_hw248-t5/arm64/`; all **27/27** match `_hw248-t5/SHA256SUMS` (the manifest is in the parent directory). Primary OAT SHA: `08837079ac97bbec25a804fc1916e5973911b8dd58733a57f8e5f52d5c9da6c9`. [candidate-receipt.json](candidate-receipt.json).
- **L1: 9 equal / 18 different / 0 missing**. All nine VDEX files are identical, and the **13 embedded OatDexFile records** have identical dex locations and input checksums (framework has five dex files). Eight secondary OAT record bodies also match exactly after relocating their record positions. Primary records differ in three layout offsets, each by **−300 bytes**, consistent with its shorter metadata area after alignment.
- The primary KV size is **2259→1960**. Only `concurrent-copying` and `dex2oat-cmdline` values differ. The command has the same non-path options and dex-location values; its executable, image, oat and local input paths differ. **This delivered run has no `--compilation-reason` to remove.** The earlier `31a3e81e` artifact was not supplied and is not silently identified with this one.
- Primary `.text` length is **8,559,240→8,622,888 bytes (+63,648)**. Framework `.text` is **49,355,464→49,502,376 (+146,912)**; mainline stubs **17,420→17,708 (+288)**. The full nine-segment table gives independently aligned region offsets and differing-position counts. Counts include shifted code/layout; they are not counts of semantically changed instructions. No claim that read barriers explain every residual is made until a controlled T3b/T5b comparison exists.
- **Each set is internally paired correctly: 9/9 ART headers name the checksum of their own OAT.** A newly generated OAT checksum need not equal the old one just because both sets can be loadable. Do not edit checksum/KV bytes to manufacture identity. The inverse-Adler diagnostic removes the known final header append under r1's writer model; it is explicitly not a recomputation of the full stream checksum.

## Why the keys and checksums behave this way

Source is a clean local r1 tree at commit **`3c05e56adf5b268ec5b20bf8aec460815e45161c`**, `westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/art-r1/`. Every cited excerpt is archived with SHA and line numbers in [source-evidence.json](source-evidence.json); this is a mechanism reference, not a recovered d600 build receipt.

- `dex2oat/dex2oat.cc:1625–1661`: compilation reason is optional; a primary boot image writes bootclasspath only. Boot extensions and dependent app compilation write bootclasspath-checksums. Lines **1722–1724** pass the KV store only to the first OAT writer. This explains the actual 8-key primary / empty secondary stores without inventing a d600 patch.
- `dex2oat/dex2oat.cc:975` writes `gUseReadBarrier` into `concurrent-copying`. It is a compatibility value, not decorative build metadata. `runtime/gc/space/image_space.cc:3445–3451` rejects a mismatch. T1 patch 13 preserves this check and adds the `rb_mismatch` diagnostic.
- R155 itself confirms the check: `libart` **VA `0x461bb4`** calls `IsConcurrentCopying`; **`0x461bb8`** branches on true to the mismatch path. [libart-validate_oat.asm](libart-validate_oat.asm). The recorded reference image and native expectation agree on false. Actual T6 execution still belongs to cc-wiki.
- `dex2oat/linker/oat_writer.cc:116–129,2703–2712`: Adler32 accumulates body writes, then appends the complete header/KV with its checksum field zero. Header bytes alone do not determine it. Nine empty-secondary KV stores with different code directly refute “only the missing key caused L1 failure.”

## T3b environment and observation limits

Source [t3b.env.sh](t3b.env.sh) **before building** in the build owner's isolated workspace. It sets:

```sh
export ART_USE_READ_BARRIER=false
export ART_DEFAULT_GC_TYPE=CMS
export ART_USE_GENERATIONAL_CC=false
export ART_HEAP_POISONING=false
export ART_TEST_DEBUG_GC=false
```

Select release **dex2oat64 / libart.so**, preserve the old on-build for comparison, and rebuild the host tool **and its loaded dependencies** with the same settings. Merely exporting these variables while running the old executable does not recompile it. Recreate images using the unchanged nine input JARs and dex-locations first; keep the boot API changes in a later controlled input revision. Confirm generated `concurrent-copying=false`, nine VDEX matches, and internal ART/OAT pairing before T6. This audit does not build or deploy anything.

| Observable | R155 evidence | Consequence |
|---|---|---|
| Read barrier | KV false; native reject-true branch; `artReadBarrierSlow@0x810f60` is plain load/ret | Disable read barriers. Read-barrier type is inactive; original ignored BAKER/TABLELOOKUP environment text is unknowable. |
| Default GC | `XGcOption` constructor `0x76e5a4` loads 2; `0x76e5b8` stores it; empty parse independently agrees. Enum 2=CMS (`collector_type.h:26–40`) | Set CMS explicitly; **do not retain r1 default CMC**. This does not identify a running process's possible `-Xgc` override. |
| Generational CC default | Constructor zeros all boolean fields, including +6; `cmdline_types.h:540–544`, `runtime_globals.h:57–60` | Default false; runtime override is a separate question. |
| Heap poisoning | `IsNullOrMarkedHeapReference@0x68e368` passes the loaded reference directly to `IsMarked`; no negation. `object_reference.h:100–106,170–179` defines poisoning/decompression. Plain slow/root loads corroborate. | Set false. |
| Native debug build | `VMRuntime_vmLibrary@0x3db6bc` resolves `libart.so` at `0x21be56`, selected by `kIsDebugBuild`; GC verification defaults are zero | Release target/NDEBUG. OAT `debuggable=false` alone would not prove this. |
| TLAB, C++ interpreter, sanitizer/gap, optimization | No definitive original receipts/native predicates recovered. TLAB is source-derived from RB/GC; its original caller value was not independently extracted. | Keep **unknown** in the comparison. Do not label upstream defaults as recovered facts. |

`ART_READ_BARRIER_TYPE` is ignored when RB is disabled; r1 `build/art.go:59–84` does not provide a direct `ART_USE_TLAB` environment knob. The known RB-off/CMS combination derives no TLAB define in that build logic. `ART_TEST_DEBUG_GC=true` would override GC to SS, so the recipe explicitly disables it. Full flags and caveats: [build-flags.json](build-flags.json). Source-built flag values and original environment strings are separate claims.

## Re-run and handoff

From this worktree, with `WORKSPACES` set to the workspace parent:

```sh
python3 benchmark/2026-09-30-t5-oat-attribution/compare_oat.py \
  --reference "$WORKSPACES/westlake-generation-v3a-74d1d6d4-r8b/payload/android/framework/arm64" \
  --candidate "$WORKSPACES/_hw248-t5/arm64" \
  --manifest "$WORKSPACES/westlake-harness/knowledge/toolchains/boot-image-inputs.sha256" \
  --out /tmp/t5-comparison.json
python3 benchmark/2026-09-30-t5-oat-attribution/test_compare.py -v
agent-spec lifecycle specs/t5-oat-attribution/t1-compare.spec.md --code tools/spec-checks --layers lint,test
```

Parser exit 0 means comparison completed, **not L2 accepted**; missing candidate records unknown/exit 3, malformed input or wrong reference SHA exits 2. `capture_flags.py --libart … --llvm-bin … --out …` reproduces symbol-sized disassembly and byte evidence, refusing a different native SHA. [T4-RECOMMENDATION.md](T4-RECOMMENDATION.md) proposes extending the existing T4 gate without editing its approved contract or weakening its layout checks.

R2: local binary identity, KV/section differences, native flag observations and source mechanisms **verified**; unknown original flags remain explicit. T3b construction, T6 runtime loading and UI are **unverified by this lane**. New screenshots/alive counts are unknown; no board command or lock was used.

Validation: **9/9 task tests; 3/3 contract selectors; lint 100%; repository known-answer run 69 tests, 2 skipped, 0 failures; user-path gate 36 files, 0 violations**. `git diff --check` passed. Test evidence is retained beside this report.

Commit boundary: files staged locally, but `git commit` failed creating the shared worktree `index.lock` (`Operation not permitted`). No new commit or push; outer-loop commit required.
