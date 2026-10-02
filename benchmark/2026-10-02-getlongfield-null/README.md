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
