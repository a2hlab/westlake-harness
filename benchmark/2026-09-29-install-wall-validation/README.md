# BMS install-wall validation on 61b

The first two candidates were built from an incomplete mixture of OH output objects: identical exported symbols and DT_NEEDED did **not** preserve the APK routing behavior. The final candidate restores the existing APK routing objects/source, then applies the two reviewed #77 changes. Seal, Toutiao and X now return `install bundle successfully` and are queryable by `bm dump`; all three final screenshots show the OH desktop, not app content. Installation is verified; application rendering is not achieved.

## Final service pair and runtime

Only `61b0657200000000000000000324012c` was written for this validation. The reassignment from 5ea is recorded on board #79. Every system-library change was preceded by “将重启 61b”. The original four files remain in a separate, hash-verified backup directory.

| Component | Original SHA-256 | Final SHA-256 |
|---|---|---|
| libbms.z.so | f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105 | 2220df48c7bc5a64ca064879f80badc15b3a3ca140dc1d0067a7499f6a7e5e92 |
| libinstalls.z.so | 2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0 | 51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5 |

Both `/system/lib64` and `/system/lib64/platformsdk` copies were updated. Shell and foundation-root reads match the final hashes. During Seal installation, PID 9037 mapped libinstalls; both paths under `/proc/9037/root` matched `51e1b525…` (see `installs-live-r3.txt`). `foundation-maps-r3.txt` and `service-state.json` record the BMS verification.

The Android runtime remains the same v3a/r8b package: `westlake-generation-v3a-74d1d6d4-r8b`, package SHA `aef124075df8f5caaf9cdcf094d523ea7d806cfd1e2e4fbe3eedfc183c78f525`, bridge `84695d62…`, runtime JAR `d5000c4e…`. After each reboot, `scripts/lab/deploy_generation.sh` reapplied that package and verified its child mappings and hashes. The final boot is `2cded455-0114-4d1d-9c86-9395d4166a95`.

## Installation and launch evidence

The master-worktree `bms_batch.py` performed the preflight (16 MiB logs, private off, clock and screen timeout), original-APK reinstallation, sandbox preparation, desktop icon selection and launch. Each `evidence/<key>/record.json` contains the actual input SHA, preflight, bundle identity and captured-image records. `install.txt`, `bundle-summary.json` and the retained full `bundle.txt` prove installation separately from launch. `facts-apps.txt` is unmodified runner output: its per-app t5/t20 values are unknown because this diagnostic run sampled t3/final rather than named t5/t20 process files. The aggregate zero is **not** a claim of measured t5/t20 death.

| App | Install / query | Final image | Subsequent failure |
|---|---|---|---|
| Seal | success / queryable | OH desktop | libmmkv.so cannot resolve `__errno`; main later fails AppCompat theme check |
| Toutiao | success / queryable | OH desktop | libflipped.so cannot load `libstdc++.so`; MainActivity construction later fails Boolean.booleanValue NPE |
| X | success / queryable | OH desktop | background nativeSubscribeCommonEvent missing; main reports application object graph not defined |

The uncaught/main-thread exception text and line numbers are preserved in `evidence/*/fatal-excerpts.txt`. Native parse-manifest warnings are tolerated by the r8b Java fallback and are not mislabeled as the final fatal event. Runtime repairs for these later walls are outside #79.

All four approved raw native payload exceptions were read back from the installed directories with exact original hashes and sizes (`payload-readback.json`, `extracted-payloads.txt`): Seal's three ZIP payloads and Toutiao's packaged ARM32 `libcvt.so`. Extraction preserves bytes and does not make ARM32 code loadable by an ARM64 process. The exception predicate remains exact bundle + ABI + filename + SHA; CRC, length, destination, ownership and mode checks are retained.

Screens: `evidence/{fd-seal,toutiao,x}/{t3,final}.jpeg`; final images were inspected and show desktop icons. Outer-loop image review is the final lighting verdict. Control evidence and facts are reported in `results.json` and `facts-controls.txt`.

## Build provenance and reproduction

The two patches are copied from cx-bms #77 (`22de5ddb`/`e89d1af4`), with the outer-approved four-entry table in `native-data-exceptions.json`. Patch 0001 reuses the verified 1 MiB manifest capacity; patch 0002 retains the exact packaged data exceptions. Patches applied with fuzz zero. APK inputs, upstream source trees and the remote OH source tree were not modified.

The narrow build recipe comes from `01.OH61AOSP16/real-work` at `be16148da9ae7bb89c62e81e144ed0bceb5c4669`, `.agents/skills/build-oh-component-hw248`, and its frozen BMS seed. The shared tree `/opt/build-trees/oh610_lts_source` was copied read-only into the private `oh61-bms-kit-b79`. Builds ran locally via dockbuild, using OH clang-15 SHA `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`. Exact link rules retain strict undefined-symbol checking, CFI and version maps. Only the post-link mini-debug packaging wrapper was omitted; the original LLVM strip still produced the deployed ELF.

The final ELF export sets and ordered DT_NEEDED lists match the original board pair (`abi-diff.json`). This is an ABI check, not proof of all-function equivalence. The shared input set differs from the older seed ledger at 78 entries (`seed-link-input-differences.json`); the report does not claim a two-line binary delta or reproduction of the original pair.

The full final kit, including source/header snapshots, original and patched source, frozen routing objects, compiler/linker inputs, build rules and final ELF files, is persisted at:

```
Mac: /Users/zhaoyue/orca/workspaces/oh61-bms-kit-b79-r3-final.tar.gz
hw248: /home/alvin/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz
SHA256: 61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6
```

Local and remote checksums match. Restore at the recorded kit path and run:

```sh
DOCKBUILD_MOUNTS=/Users/zhaoyue/orca/workspaces/oh61-bms-kit-b79 \
  /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/dockbuild.sh run -n b79-narrow -- \
  bash benchmark/2026-09-29-install-wall-validation/build_narrow.sh
```

`source-toolchain.json`, the source snapshots, Ninja rules and patch files provide the small reviewable ledger. The kit must preserve its OH compiler directory layout: symlinking the entire SDK bin directory caused clang to select the SDK libc++_shared rather than OH libc++ (`std::__h`). Host LLVM also needs its SDK libxml2 on LD_LIBRARY_PATH; `build_narrow.sh` records that setup.

## Failed rounds and corrected input rule

1. R1 `0448366c/43bcde50`: all three APKs failed with 9568269 before manifest/native validation. Missing verified stream-installer and ZIP objects prevented the existing APK route. A foundation-only restart also produced a black frame; the documented full reboot + same-v3a replay restored HelloWorld.
2. R2 `fcc900d6/51e1b525`: copied frozen `bundle_stream_installer_host_impl.o` (`89de1d5a…`) and `zip_file.o` (`2e2a6247…`); all three reached the next route predicate but failed with 9568265. Install-time logging showed `CheckFilePath` rejecting `.apk`. The old `bundle_util.o` IR lacked `.apk`, even though its adjacent source had the OH_ADAPTER_ANDROID branch.
3. R3 `2220df48/51e1b525`: compiled the existing, unmodified `bundle_util.cpp` and `bundle_installer.cpp` with the original OH Android flags. The new IR contains `.apk` (`apk-route-ir-excerpt.txt`). Only the two BMS paths changed in this round. All three installs passed; no runtime generation was rebuilt.

The stable rule is to carry the complete verified APK routing chain and check its compiled predicates, not infer source/object agreement from a shared directory or export identity.

## Validation and rollback

Known-answer tests: 69 run, 2 skipped, OK. Pinned-input and candidate positive/negative tests pass (40 native cases and 12 capacity cases). The inherited #77 lifecycle is **2 pass / 1 fail**: the impact/provenance test still requires exception status `draft`, while the outer loop explicitly approved it. The failure is preserved in `lifecycle.json`; neither the contract nor the assertion was edited to fabricate a pass. Thus host candidate validation is verified, lifecycle acceptance is partial, and lighting remains subject to images.

`swap_services.py` implements guarded replacement and exact rollback. It preserves the initial backups across candidate updates, records the desired baseline/candidate before writes, checks the board lock/boot and verifies shell/process-root SHA. On rollback, use its `rollback` action through the VM, reboot 61b (announce first), then `verify` and replay the same v3a package. The final candidate remains installed; rollback capability is prepared but no unnecessary final rollback was performed. Physical reboot recovery was exercised in all three rounds. Raw runs, commands and backups remain under `westlake-generation-state/61b0657200000000000000000324012c/` and `/data/local/tmp/b79-install-walls-0448366c-43bcde50/backup/`.
