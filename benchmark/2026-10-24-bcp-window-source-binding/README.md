# Exact BCP window-class source binding

The `0757e594…` Java file is not proven to be the source of the current BCP JAR. The exact `ea5d8b27…` artifact is a historical CLAMP48 **smali-derived** JAR; its historical notes explicitly say the DEX was newer than the available Java source. No compilation or device operation was performed in this review.

## Exact artifacts and classes

- JAR SHA256: `ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e`, 202502 bytes.
- Local content-addressed copy: `$WORKSPACES/westlake-inputs/seal-artifacts-20261012/sha256/<JAR_SHA>`.
- Historical copy: `$WORKSPACES/westlake-harness-hollow48/benchmark/2026-09-26-operator-layout79fix-48/out/adapter-runtime-bcp.CLAMP48.jar`. Both copies were hashed and compared byte-for-byte: equal.
- Sole ZIP member `classes.dex`: SHA256 `c5bd7fd23b0ed5c8a6d2b8dce0bd387f899b6fd0b58f5423314c3e90983d35cf`, 498388 bytes.
- Actual descriptors: `Ladapter/window/SessionStageBridge;` (69 method definitions) and `Ladapter/window/WindowSessionAdapter;` (100). See [classes.json](classes.json).
- T106 records the exact JAR at `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/fw/adapter-runtime-bcp.jar`, physical inode396770/dev66352, UID/GID20011206, mode644. This is historical disk evidence, not fresh proof of the effective boot-image class winner.

[Source index](source-index.json) gives exact metadata/source/build paths, line numbers, complete hashes and sizes. `$MAIN` is the main checkout; `$WORKSPACES` is its parent workspace root; `$DELIVERY` is this directory.

## Method-body evidence

The exact DEX was locally disassembled using the pinned SDK `dexdump -d` (rc0). The raw output and failed optional baksmali invocation are indexed in [raw-index.json](raw-index.json). DEX modified UTF-8 caused the initial whole-output UTF-8 conversion to fail; decoding with replacement was only used to select the ASCII class/method excerpts. Original output bytes are retained.

[Exact method excerpts](dex-method-excerpts.txt):

- `SessionStageBridge.onNotifyDestroy()V`, code item `0x6b4cc`: if `mIWindow` is non-null, call `OhInsetsBridge.remove`; then log `NotifyDestroy` / `Android handles via Activity.onDestroy, not IWindow` through `logPartial`; return. The Java snapshot `SessionStageBridge.java:105–108` expresses this same local behavior. This is a bounded semantic comparison, **not** whole-class source identity or a reproduction.
- `WindowSessionAdapter.remove(IWindow)V`, code item `0x709bc`: removes bookkeeping/input state; if a session entry exists, calls `nativeDestroyOHSurface(id)` then `nativeDestroySession(id)` and logs destruction. These calls are not in `onNotifyDestroy`. Runtime invocation and native completion remain unproven here.
- The DEX includes `clampWidth48` / `clampHeight48`, and CLAMP48 notes locate their use in `relayoutLegacy`, not merely the `relayout` wrapper. The `source-build-host` Java snapshot does not contain these clamp helper names. It cannot reproduce this JAR unchanged.

No `NotifyDestroy` match in the reported child log proves only an absent observed marker. It does not prove the callback was not invoked, or that the separate remove path did not execute.

## Build chain and missing links

1. Historical `README.md` update / `out/CHANGE-NOTES.md` binds baseline JAR `5731db00562e3b814cfb4d4e32703c40c9e8726a022b28da155fd040fb59019a` to the exact CLAMP48 output. The full patched `WindowSessionAdapter.patched.smali` and 114-addition diff are present and hashed. This review did not reassemble them or claim an independent method-text match.
2. The historical recipe describes baksmali/smali2.5.2, API29 / DEX039 and ZIP replacement. Original smali assembly argv + stdout/stderr/rc and the complete baseline input tree were **not established** in this bounded check. The old generic BUILD first section's non-BCP/overlay advice is superseded by its later delivery notes: this artifact is BCP.
3. `westlake-harness-clamp48/.../evidence/build/{command.json,boot-image.log,tool-sha256.txt}` supplies a real later **dex2oat boot-image** command/log/tool record; the log ends with a completed dex2oat duration. It consumes the JAR; it does not prove how the JAR was compiled from Java or assembled from smali.
4. `source-build-host/java-source.lock.json` explicitly sets `complete_production_build_closure:false` and `historical_r84_r89_exact_artifact_binding:false`. It pins SessionStageBridge `0757e594b8f5d45cb3f52af511163bdb3e05192e98f005b9bb8c99731e876d79` and WindowSessionAdapter `3f15d1f89c5235dd9c8e97f18429f00ba131fa52591a0db67fdbb90c600d9f09` from `a2hlab/westlake@691433b967ba01365a382d30fbd820c1231c0811`.
5. Its `build-java.py` verifies source pins and invokes `manifest-tools/tools/build_westlake_java.py` with workspace/core/framework/core-extension inputs. The receipt scope explicitly excludes historical production DEX binding. This is an available candidate source-compilation route, not an exact ea5d reproduction recipe.

Minimal unresolved chain: original `5731…` Java/compiler/classpath-to-DEX receipt and sources; exact CLAMP48 assembler inputs/tool invocation/raw build receipt; current boot-image effective class binding. No substitute Java file is promoted to an exact source.

## Comparison tools

`dexdump -d` already supplied exact instructions, signatures and code offsets. A correctly launched existing baksmali CLI can normalize method bodies against the preserved smali; the attempted `java -jar baksmali-2.5.2.jar` failed because that JAR has no main manifest entry. That failure is retained; no comparison success is claimed. `deployed_class_diff.py` is suitable for class/super/interface structure only, not whole method equivalence. No REA, SSH, device access, source modification or rebuild occurred.
