# GetLongField JniAbort — it's `fid == null` (hardened), the uninitialized-cache double-copy disease

Offline, no board. The outer flagged that my earlier "obj == null" read used the DfxFaultLogger register dump (x0=0
at abort time, the tgkill chain) — not the GetLongField argument, so invalid. Re-determined statically from the ELF.
**Result: it is `fid == null`, not `obj == null`.** That reverses the N11h-r2 shelve: `fid == null` is exactly the
double-copy / uninitialized AssetManager-field-cache mechanism.

## Hardened determination (evidence/getlongfield-fid-null-disasm.txt)
Deployed route-a `libart.so` (build-id `8c2796fcedddaf77a3fa013801ebfc19643c1004`),
`art::JNI<false>::GetLongField` @ 0x56b41c. Entry has two null checks: `cbz x1(obj), 0x56ba68` and
`cbz x2(fid), 0x56ba88`. The two abort paths call `JavaVMExt::JniAbort(func, msg)`:
- **obj-null**: bl @ 0x56ba7c = GetLongField **+1632**, msg `'obj == null'`.
- **fid-null**: bl @ 0x56ba9c = GetLongField **+1664**, msg `'fid == null'`.

(strings decoded from .rodata: 0x22c67f=`GetLongField`, 0x226f0b=`obj == null`, 0x210aea=`fid == null`.)

The observed backtrace frame #06 for **all four** keys is `GetLongField+1664` (`+1632` count = 0) → the **fid-null**
path. So the `jfieldID` passed to `GetLongField` is NULL — the AssetManager `mObject` field id the app's
`AAssetManager_fromJava` reads is null.

## Mechanism — the double copy IS the cause (DIGEST 2026-10-01 fid==null corroborated)
`gAssetManagerOffsets` is a per-`.so`-copy BSS global in BOTH `liboh_android_runtime.so` and `libandroid.so`. The
`OH_AssetOffsets` init (in `liboh_android_runtime.so`) logs `AssetManager.mObject cached in runtime and libandroid NDK
owner` **once** per process — it fills the one copy that runs it. A Flutter/NativeActivity app runs in its own domain
(`westlake_flutter`/`westlake_native`) whose runtime+libandroid are loaded separately (the `candidate-stock-host.c`
flutter/native branch inherits runtime from `default`, a distinct copy). That copy's `gAssetManagerOffsets.mObject` was
never cached → `AAssetManager_fromJava` reads a null `mObject` jfieldID → `GetLongField(obj, null fid)` → `fid == null`
JniAbort → SIGABRT. This is the two-copy disease, not an app-level null object.

This also squares with the universality count (the outer's `double-copy-universality`): the bridge/runtime double copy
is benign for lit/white rendering (115/115 lit have it too), but the **AssetManager field-cache** half of the
double-copy specifically breaks the NDK-AssetManager apps — the only keys that call `AAssetManager_fromJava`.

## Predicted keys moved (if the fix lands)
- **Move (4, the fid==null terminal):** `cv2-org-linaro-glmark2`, `localsend`, `fd-fluffychat`, `fd-immich`.
- **Not moved (3, different wall):** `fd-im-vector-app`, `mindustry`, `fd-meet` — these are `main_threw` java exceptions
  (`GetLongField+1664` count 0), a separate investigation.

## Minimal fix — layer is NATIVE (liboh_android_runtime.so AssetManager cache), not JAR
Two candidates; pick by fewest variables after the confirmation below:
1. **Per-copy cache init (most targeted):** make the `OH_AssetOffsets` cache-init fill `gAssetManagerOffsets.mObject`
   in *every* runtime/libandroid copy (drop the once-guard / run it when each domain's copy loads). Touches only the
   cache-init in `liboh_android_runtime.so`; no namespace / JNI_OnLoad change. Fixes `fid==null` directly.
2. **Single owner for the app domain (the N11h direction, scoped):** the flutter/native branch shares the one
   initialized runtime/libandroid (sealed owner) instead of inheriting a fresh copy from `default`. Bigger (namespace
   change + the JNI_OnLoad-guard question from n11h-r2); its blast radius is the flutter/native branch only.

Option 1 is the smaller variable for *this* wall (only the cache init, no loader change). The DIGEST's prior note
preferred single-owner ("让各域拿到同一份 owner,不是逐份去填") — worth re-weighing now that the wall is scoped to the
AssetManager field cache of exactly the NDK-AssetManager apps.

## Confirmation still needed before building (honest gap)
The unlit flutter/native keys did not capture `maps-*.txt`, so the exact copy the app reads is inferred (DIGEST +
the once-init + fid==null), not shown base-by-base. To finalize the fix choice, one maps-capturing run of a flutter key
(libandroid + runtime bases in the flutter domain vs the cached copy), or a static read of the `OH_AssetOffsets`
once-guard to confirm it runs per-process-not-per-copy. Build + window belong to the cx-bms host/runtime lineage.

## Files
- `evidence/getlongfield-fid-null-disasm.txt` — the libart disasm proof (obj+1632 / fid+1664 / decoded messages).
- `evidence/cache-owner-and-keys.txt` — OH_AssetOffsets owner + the 4 fid==null vs 3 main_threw split.

---

## FIX (single file) + a/b/c answers — patch ready, build = cx-bms adapter chain

### (a) Which file executes AAssetManager_fromJava for the 4 keys — libandroid.so
Disassembly of the deployed `libandroid.so` AAssetManager_fromJava (6-instr stub): it loads
`gAssetManagerOffsets.mObject` from **libandroid's own** per-copy global and BR-tail-calls `env->GetLongField`
(so the backtrace shows the app's `native_getSceneInfo` → `GetLongField` with the converter frame tail-called away).
The process carries **3 libandroid.so copies**: `android/lib64/libandroid.so` (sha 9ccf64f8) and the
`westlake_flutter/` + `westlake_native/` domain copies (sha ee2fb82c, identical to each other, DIFFERENT build from
the main). `initialize_n10b_asset_offsets` dlopen's one libandroid copy and fills only its `gAssetManagerOffsets`; the
flutter/native domain copy the 7 NDK-AssetManager apps load is never filled → `mObject == null` → `fid == null`.

### (b) Source + build chain
Source: AOSP `frameworks/base/native/android/asset_manager.cpp` (`AAssetManager_fromJava`, line 61; `using namespace
android;`), frozen at hw248 `/opt/wl-src/adapter/third_party/aosp_raw/frameworks/base/native/android/asset_manager.cpp`
and mirrored in `westlake-inputs/aosp-14.0.0_r1-src/...` (both byte-identical at this function). Build chain = the
**cx-bms adapter** AOSP-lib build (`bms/src/adapter/build/build_aosp_lib.sh` +
`build/inner/apply_aosp_native_patches.sh`, which applies `aosp_patches/<path>/*.patch` via `git apply`, idempotent) on
the hw248 frozen toolchain / container — NOT `build_android_native.py` (libandroid.so is not in `native/libraries.json`).
So the patch ships as `aosp_patches/frameworks/base/native/android/asset_manager.cpp.patch`.

### The patch (patch/asset_manager.cpp.patch — `git apply --check` CLEAN against the frozen source)
Lazy-resolve `mObject` at the read site if the cache is null, then take the original path:
```c
if (gAssetManagerOffsets.mObject == nullptr) {
    jclass amClass = env->GetObjectClass(assetManager);
    if (amClass != nullptr) {
        gAssetManagerOffsets.mObject = env->GetFieldID(amClass, "mObject", "J");
        env->DeleteLocalRef(amClass);
    }
}
return (AAssetManager*) env->GetLongField(assetManager, gAssetManagerOffsets.mObject);
```
No loader / namespace / JNI_OnLoad change; fixes whichever libandroid copy is used, on first use.

### (c) No-op for the 115 lit keys — static proof
The whole change is inside `if (gAssetManagerOffsets.mObject == nullptr)`. For any copy where the cache is already
filled (`mObject != null`) the branch is skipped and control reaches the **unchanged** `return (AAssetManager*)
env->GetLongField(...)` — byte-for-byte the old path. The 115 lit keys either never call `AAssetManager_fromJava`
(only the NDK-AssetManager apps do) or hit it on a copy whose cache is filled → the guard is false → no behavior change.
On rebuild, `deployed_strings_diff libandroid.so` must show ONLY additions (the new block's code; it introduces the
reused literals "mObject"/"J" which already exist via initialize_n10b) and no drops → confirms the fid!=null path is
untouched.

### Build — needs the cx-bms libandroid recipe
I own the build per dispatch, but libandroid.so is built by the cx-bms adapter chain (two variants: main +
flutter/native), not a recipe I have end-to-end. Requesting the exact `build_aosp_lib.sh` invocation for libandroid
(both variants) from cx-bms on the board; then: apply the patch, two byte-identical builds of each libandroid variant,
tee the build log to a persistent location + record toolchain hash, `deployed_strings_diff` vs the deployed
9ccf64f8 / ee2fb82c (expect only the added block). **U12/U13: if ready + proof complete before cx-t0 finalizes U12 →
merge into U12; else U13, do not delay U12.**

---

## BUILD DONE + ACCEPTED (U13) — patched liboh_android_runtime.so aa149019

Built on the a2hlab OrbStack VM (x86_64 Linux; the frozen toolchain is x86_64 Linux and cannot run on the mac — this
is why the ECS was never needed, just a Linux host). Recipe = the `smoke-markers/build-runtime.py` family replayed as
`build/build-runtime-patched.py`: reuses the `.work/n4-registration-order` object set + frozen toolchain, recompiles
only changed sources. The patch was applied in place to `.work/b87-native/adapter/.../asset_manager.cpp` (backed up +
**restored**, restored sha e3e475f5 == original) and `asset_manager.o` deleted to force recompile.

- **Reproduction**: baseline variant = 216b68fb == the signed U8 baseline; the unpatched candidate = ac59dec0 == deployed.
- **Patched candidate = `aa149019`, repeat = `aa149019`** → byte-identical ×2 (deterministic). Persisted
  hw248:/home/alvin/u12-icu-cc-wiki-20261002/n11hr2-runtime-aa149019.so + build log.
- **Acceptance vs deployed `ac59dec0`** (`build/build-acceptance.txt`):
  - objects differing (of 69): **`asset_manager.o` only** (17fd7dc0 → e448f07a).
  - exports (`nm -D`): **IDENTICAL**; undefined: **IDENTICAL** (`/usr/bin/diff`).
  - `deployed_strings_diff`: **0 dropped, 0 added**.
  - `open_site_scan`: 198 == 198; after normalizing lib-name + address, **semantically identical** (no new/removed
    library-open site; the raw diff is only the filename prefix + address shift from the enlarged `.text`).

Net: `aa149019` differs from `ac59dec0` by exactly the asset_manager read-site lazy-init; ABI / exports / strings /
open-sites unchanged. **Ready for U13** as a single-file runtime replacement + rollback (runtime not in frozen.json).
Files: `patch/asset_manager.cpp.patch`, `build/{build-runtime-patched.py,runtime-build-receipt-N11HR2.json,build-acceptance.txt,build-candidate.log}`.
