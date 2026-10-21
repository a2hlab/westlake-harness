# G18 — minimal GLES name visibility candidate

The deployed U13 loader's shared policy has7 names and omits `libGLESv2.so`; the accepted normal-UI log shows that dependency failing while loading `libyuanshen.so`. This candidate appends only that name to the JSON and matching header. It does not replace a GLES provider or establish that graphics/JNI will work. The earlier `__errno` error remains outside this change.

## Actual build and input chain

- Baseline: **b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7**, 773928 bytes; complete newly compiled/linked ELF SHA exactly equals the original U13 candidate1/2.
- Candidate: **878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23**, 774000 bytes.
- Exact main U13 candidate policy:10 source files;15 original raw command logs;4 tools;607 header inputs;2 reused link DSOs;both archived candidate libraries rehashed without drift. See `input-review.json`, `source-pins.json`, and preserved `upstream/policy-build-receipt.json`. The current BMS6-name header was not used.
- Native compiler is the pinned OHOS clang15.0.4, SHA6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1; ld.lld SHA489c6d6628a56c027eac4dceee87910f7ca28b0c5a0e5188c32cb0108c08a837. Tool version raw outputs are retained.
- Four original U13 candidate1 compile/link commands were replayed per variant, remapping source/output paths into this card. Existing source prefix mappings were retained, with `-fdebug-compilation-dir` set to the original recipe's working directory. This metadata normalization reproduced the whole baseline without relaxing its SHA gate. All8 native compile/link commands,2 policy checks and the frozen-source gate returned0. The frozen gate checked8 entries/30 objects,0 violations.
- Registry and system-loader object SHAs are identical between baseline and candidate. No system7, media_jni RTLD_NOLOAD, namespace implementation, errno or APK change was made. `shared-gles.patch` contains the only2 changed production files.

## Actual ELF and regression evidence

`inspect_elf.py` decodes ELF64/AArch64 symbol sizes, RELA pointers and string_view lengths: shared arrays are7 and8 entries in order; system array remains7. It checks actual disassembly calls from both `CreateClassLoaderNamespace` and `OpenNativeLibrary` into the policy-array consumer. This is compiled configuration consumption evidence, not a strings search. Dynamic-symbol ABI tuples and DT_NEEDED are equal. See `elf-review.json` and `elf-consumers.txt`.

Both baseline and candidate pass the unchanged native-loader host registry: **74 checks,0 failures each**. An additive test verifies the complete ordered policy reaches both explicit and implicit backend creation: **78 checks,0 failures each**. The original U13 media owner test and an extension covering all7 system entries pass on both variants; media_jni remains resident-only and a missing resident owner still fails. Duplicate, invalid-path and reserved-self SONAME controls each return the expected refusal1. Host backend tests are not real child mapping or device validation.

The first additive test compile failed because its CloseNativeLibrary call omitted the existing needs_native_bridge parameter. The original failed command/stderr and failing test/helper bytes remain under `.private/regression-01/`; `regression-first-failure.json` explains the corrected test-only call. No native candidate rebuild was needed. Both74 and78 check outputs remain intact.

## Storage and reproduction

All effective helpers are here: `prepare_inputs.py`, `build_candidate.py`, `inspect_elf.py`, `regress.py`, `package_evidence.py`, `archive_evidence.py`, and `check_receipt.py`. The old U13 build.py is preserved only as a source reference; its stage/main was not executed. Runtime stdout/stderr were redirected directly to persistent separate files before each subprocess started, with argv/cwd/start/end/rc and SHA receipts. `sanitization.json` binds public path-aliased copies to untouched private bytes; `raw-index.json` binds the persistent originals. Input header/link-library bytes and all15 old raw logs are also retained privately.

`$G18` is this card's repository directory. Private outputs use `$G18/.private`, within the writable isolated tree; no shared-source-tree build or private-HOME permission retry was used. The candidate is `$G18/.private/build-01/candidate/libnativeloader-candidate.so`. `archive-receipt.json` identifies the locally verified bundle; remote publication is pending outer handling, not claimed. SDK compiler/linker binaries remain external pinned inputs, identified by exact paths/hashes and version receipts; their binaries are not included in the bundle.

Replay in a fresh card staging copy using the pinned upstream inputs:

```sh
python3 prepare_inputs.py
python3 build_candidate.py --run build-01
python3 inspect_elf.py --build build-01 --out elf-01
python3 regress.py --out regression-02
python3 package_evidence.py
python3 check_receipt.py
```

Output directories are fresh-only. Checking the delivered receipt does not compile or contact a device. When private originals are present it rehashes every indexed byte and decodes the actual ELF again; absent private originals are reported explicitly and are never silently rebuilt. The Rust selector invokes only this checker.

## Deployment boundary

Predicted affected key: **genshin**, specifically the observed `libyuanshen.so` GLES dependency-name visibility blocker. No claim of first frame, playability or errno causality follows. Candidate remains **offline, not deployed**. Outer later reported child10946 maps at both system and route paths with baseline b8be but different inodes; bracket/dev/inode validation is independently in progress. This card does not infer a unique loaded entry from a system filename. Actual candidate child mapping and a separately reviewed bounded deployment remain outer gates. No device operation, G14/T38 refused step, shared Git write or push occurred here.

The fixed path-only list is `landing-paths.txt`; the outer loop lands it. No canonical board write was retried.

## Landing correction: historical test reference

The first outer land attempt discovered the archived `upstream/test_analysis.py` as an executable test and reported6 errors, including missing `host-build-receipt.json`; main was rolled back. This file tests the complete old U13 policy/host/evidence tree, including private-zlib/McDonalds changes, and was copied only to document the source of the reused owner test commands. It is not a G18 test and cannot run independently here.

Its original bytes are now retained as `upstream/u13-analysis-tests.reference.txt`, SHA160de163c73cbf3b76aec0618808008dee520d938738377dcb9c91055ada1b50. `source-pins.json` records the original path and reference-only purpose; staging reproduces this name, and the checker rejects reintroduction of the executable old name. Land discovery is unchanged. The actual G18 regressions, their74/78-check outputs,3 negative controls and the earlier CloseNativeLibrary test-adapter failure remain unchanged. No native rebuild was performed for this packaging correction.

`landing-failure-01.json` preserves the outer-reported failure without inventing unavailable raw logs. The original local archive is retained byte-for-byte as the pre-landing build-evidence bundle (its historical reference filename remains inside that archive); the corrected public source pins and listing describe the current delivery. Remote archive verification remains pending.
