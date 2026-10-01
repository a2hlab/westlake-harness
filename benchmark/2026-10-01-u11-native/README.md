# U11 native: ordered, owner-bound delivery

## What was wrong; rule established

The initial lock design assumed root `libandroid.so` was a rebuildable HWUI shim with no lock implementation. Actual U9 root SHA **9ccf64f8** is an obsolete runtime renamed to libandroid, with SONAME **liboh_android_runtime.so**, 268 exports and no lock pair. U9 maps also contain current runtime **ac59dec0**. Meanwhile the deployed private libandroid **ee2fb82c** already implements lock/post. Outer ACK(90) **21:46:12** replaced the original export-count gate and owner plan.

**Rule:** inspect the actual receiver ELF and maps before choosing a source owner. Replace root with a two-export shim, and resolve every other API through the unchanged current runtime dependency. Do not recreate the obsolete runtime or count private-file equality as loaded-owner identity.

## Cluster 1: CPU native-window lock

- Donor: `benchmark/2026-10-01-n10-native/flutter/libandroid_webview_shim.c:980` and `:1145`, SHA **c8772d05c5a815f1820809d6c1a6af265e51514c297d82bf427dd6a17b0e7f43**, source commit **bf07c8e4d612b8cd721ebee4ab3b1aadcf73019f**. `build_window_shim.py` checks the entire donor before extraction; no generic failure stub is substituted.
- Candidate: **8728134a9770ce32a5f95a44a3657a633941d6e6c8122ad083c18363b316c232**, two same-path builds byte-identical. SONAME `libandroid.so`; only `ANativeWindow_lock` and `ANativeWindow_unlockAndPost` exported. NEEDED: current `liboh_android_runtime.so`, `libsurface.z.so`, `libc.so`.
- Adaptations are explicit in `evidence/build-receipt.json`: normalize AdapterAnw through resident `oh_anw_get_oh`; CPU usage3 before dequeue; mutex-protected per-window state; full dirty expansion; corrected BufferHandle offsets; preserve successful MapWaitFence ownership and forbid positive-fence failure bypass; cancel on failed flush.
- Source tests execute the generated donor-derived code, not a separate behavioral replica. Eleven modes cover RGBA padded stride, owner/usage/request/handle failures, fence descriptor reuse, failed positive fence, fenceless map fallback, failed post, concurrent same-window and separate-window locks. Python 9 tests / Rust 3 selectors pass.

### Consumer and ABI evidence

`evidence/consumers.json`: **166** SHA-pinned base APKs plus matching split inventories, **178** archives, **606** ELF64 little-endian AArch64 members. Lock consumers: **21 keys / 26 DSOs**. All NEEDED-libandroid consumers: **37 keys / 171 DSOs**. Base-only scanning misses four split duplicates; do not use its earlier 22-DSO count.

The old 268-export set is **267/268** covered by `(shim exports union ac59 exports)`. The only missing symbol is `_ZN7_JNIEnv16CallObjectMethodEP8_jobjectP10_jmethodIDz`; all 606 native members have **zero UND imports** of it. Outer ACK(90) **22:37:41** approved this one weak-inline exception, conditional on zero owned-payload consumers. `scan_payload_consumers.py` scanned all **102 manifest-listed DSOs** of actual U10 manifest **3f5bee16** (including android descendants and system-side route providers); its one NEEDED-libandroid consumer, ZigZag libtuanjie, has **zero UND imports**. Conditional exception passes for this exact input; rerun on the final U11 package. Original `consumers.json` pending annotation is preserved as the pre-approval observation, not the current decision. Union-owner consumer breaks: **0**.

Canonical `abi_diff.py --calls` results are preserved without filtering:

| Comparison | Exit | Consumer breaks | Call differences | Meaning |
|---|---:|---:|---:|---|
| old root → unchanged ac59 runtime | 0 | 0 | 15 | Already-deployed runtime differs from obsolete owner; not a new runtime rebuild |
| old root → small shim alone | 1 | 816 | 1 | Flat individual-ELF comparison does not expand NEEDED; this is **not** a passed flat ABI gate |

The separate union report explains consumer resolution but does not erase these failures/differences. A missing unconsumed inline wrapper still requires explicit outer exception. Direct physical `.so` sidecar substitutions are outside this APK inventory scan.

### Remaining acceptance gates

1. Offline superset gate passes with the **one explicit conditional exception**, bound in `evidence/export-exception.json`. Final U11 payload must rerun its zero-UND condition; no other missing symbol is excused.
2. cx-t0 assembles the new root member into the actual U11 generation, rebinds manifest/plugin/alias identities and persists source/toolchain closure. `libsurface.z.so` link input SHA **8f1879f8** must be reconciled with the target provider and namespace route.
3. Final target maps must contain **no root9ccf64f8** and a unique current runtime owner. Resolve root shim's runtime, surface and libc edges to exact resident owners; no fresh second runtime via NEEDED. Offline dependency names and union exports do **not** prove this.
4. Full U11 screenshot sweep has zero regression, including the **8 lit lock consumers** in `evidence/curated-lock-consumers.csv`. fd-plus is a Java software Surface consumer, not one of the 21 native-import keys; its separate lock checkpoint is mandatory. Real posting and t20 own UI require signed screenshots.

This component is **offline verified / assembly pending**, not deploy-authorized. Donor stderr diagnostics are retained but are not an approved hilog activation marker. Pixel-capacity and all format validation are not claimed; no new YV12 geometry forwarding is added.

## Other ordered clusters

2. **libjnigraphics shared_sonames:** private provider551d943f only needs libc, but root member is absent, and unique already-loaded bridge-visible provider has not been proved. Do not add an eighth policy entry until that proof; U10 policy621caec4 remains unchanged.
3. **OpenSLES ABI conversion:** actual OH IID24 / eight-byte GetState is incompatible with Android IID16 / four-byte state. Structural upstream reference is not firmware identity. A failed-engine stub or raw vtable cast is prohibited; no audio candidate is included here.
4. **native-soname (new assignment):** inspect why already-shared libz is absent from the effective app namespace, plus Chessclock media_jni manifest routing. The existing missing-library handoff identified absent U8 alias and actual registered MediaPlayer owner; do not replace it with mediandk or a generic media stub. New U9/U10 input inspection follows separately.

## Reproduce

```sh
DIR=benchmark/2026-10-01-u11-native
python3 "$DIR/build_window_shim.py" --workspaces "$WORKSPACES" --out "$DIR/.artifacts/window-r2"
PATH="$LLVM_BIN:$PATH" python3 "$DIR/scan_window_consumers.py" \
  --workspaces "$WORKSPACES" --build-dir "$DIR/.artifacts/window-r2" --out "$DIR/.artifacts/replay"
python3 "$DIR/test_window_shim.py" -v
python3 "$DIR/window_gate.py"
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u11_native
```

Receipt pins compiler, linker, startup objects, builtins/unwind, libc and fence declaration header. The fence declaration is from the local SDK, **not** proof of target implementation behavior. Large compiled/extracted artifacts stay in `.artifacts/` outside git; source and input identities are retained. `landing-paths.txt` is a source/evidence handoff, not authorization to publish an unfinished combined U11 package. The lifecycle first run against repository root skipped all selectors (there is no root Cargo package); the corrected `--code tools/spec-checks` run verifies all three actual selectors. Both attempts are reported honestly in validation.
