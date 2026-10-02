# U13 three single-key walls, ordered easiest-first — static dead/alive + prediction + evidence

Offline, no board, board #90. Three single-key walls U13 can pick up, each judged statically (dead or alive) with a
first-fatal-move prediction + evidence BEFORE any change. Ordering by "easiest":

| # | key | verdict | wall | fix | layer | effort |
|---|---|---|---|---|---|---|
| 1 | cv2-com-chessclock-android | **ALIVE** | `media_jni` absent from adapter manifest | reviewed alias + **one manifest row** | native/config (libnativeloader) | smallest |
| 2 | mcdonalds | **ALIVE** | `librealmc.so` needs `libz.so`, invisible in app ns | reviewed private-zlib + **one whitelist line** | native namespace (per-package host route) | small |
| 3 | fd-plus | **ALIVE but BLOCKED → defer** | `Surface.nativeLockCanvas` returns 0 (runtime stub) | real software-canvas impl | runtime JNI **+ GraphicsJNI/Skia (blocked)** | not a one-.o this round |

Both #1 and #2 are "copy an already-reviewed mechanism + one line"; #3's premise (a one-.o runtime JNI) does not hold —
its stub is one .o, but a working impl needs Skia Canvas backing that the runtime has not wired and that libhwui's
un-reproducible source blocks. Full line-cited evidence in `evidence/walls.txt`; exact edits in `fix/`.

## 1. chessclock — media_jni owner alias (easiest, ALIVE)
**Wall** (`hilog:43043`): `UnsatisfiedLinkError: system library is absent from the adapter manifest` at
`System.loadLibrary("media_jni")` inside `MediaPlayer.<clinit>:620`, reached via
`ChessClock.onCreate:153 → setUpGame:744 → initRingtone:243 → RingtoneManager.getRingtone → Ringtone.createLocalMediaPlayer`.
The runtime `liboh_android_runtime.so` **already registers** the media_jni methods (49/49, native_init=1, native_setup=1 —
a registered stub, native-missing-libraries). Only the `loadLibrary` gate blocks `<clinit>`: `libmedia_jni.so` is not in
`native_bridge_policy.v1.json system_libraries` (today only libicu_jni / libjavacore / libopenjdk / liboh_adapter_bridge).

**Fix** (`fix/chessclock-media_jni.md`): add one alias row
`{ "soname": "libmedia_jni.so", "path": "/system/android/lib64/liboh_android_runtime.so" }`, plus the **already-reviewed**
mechanism from `benchmark/2026-10-01-native-missing-libraries/patches.json` — `system_loader.cpp` `RTLD_NOLOAD`
resident-only for that SONAME, `verify_bridge_policy.py` permits exactly that one alias tuple — then rebuild
libnativeloader.so. Layer: native/config. Owner: cx-bms.

**Prediction:** first fatal **moves** past `MediaPlayer.<clinit>` (loadLibrary resolves to the resident runtime whose
methods are already registered). Next fatal / t20 **unknown** (media_jni is a stub, not a decoder; a chess clock only
needs the Ringtone `<clinit>` not to throw).

## 2. mcdonalds — librealmc needs libz (next, ALIVE)
**Wall** (`hilog:30948`): `MUSL-LDSO: Error loading shared library libz.so (needed by …/com.mcdonalds.app/…/librealmc.so)`
→ `dlopen_ns` fails (`:30968` androidx.startup ULE) → DI graph never built → the observed `:31141` NPE
(`DataSourceHelper.getOrderingManagerHelper`, `SplashActivity.onCreate`) is the downstream consequence. Missing thing =
**libz.so visibility in com.mcdonalds.app's namespace** (a namespace/path gap, not a missing symbol).

**Fix** (`fix/mcdonalds-libz.md`): the private-zlib closure is **already in U12 final** (DIGEST 682
`private zlib50b9/ab082+host2a871`) — it prepends `/system/android/lib64/westlake_native` (holding the r109c `libz.so`
alias → `libshared_libz.z.so` provider) to the paths of whitelisted packages. Add **one package** to that whitelist
(`missing-library-route.h` MissingLibraryRoot, westlake_native branch `{im.vector.app, com.emn8.mobilem8.nativeapp.bk}`
→ add `"com.mcdonalds.app"`). Layer: native namespace, per-package. Owner: cx-bms.
**Not a root alias** — a root `libz.so` repeats the N7/ZigZag SIGABRT regression (DIGEST 459); the per-package host route
keeps it scoped.

**Prediction:** first fatal **moves** (librealmc resolves libz → dlopen_ns succeeds → androidx.startup → DI graph → the
NPE no longer fires). Next fatal / t20 **unknown** — **confirmation gap:** librealmc may have further unmet deps/symbols
beyond libz (BurgerKing's libmmkv only needed `crc32`, which the provider exports; librealmc's full import set is not in
the hilog). Read librealmc.so's DT_NEEDED + undefined before the window, or let the window show the next wall.

## 3. fd-plus — nativeLockCanvas (hardest, ALIVE but defer)
**Wall** (`:30255`): `IllegalStateException: Surface was not locked`. `Surface.lockCanvas` → runtime JNI
`S_nativeLockCanvas` (`android_graphics_compat_shim.cpp:236`) returns **0** — a stub ("Without a real surface buffer to
lock, lockCanvas can't return a real canvas"). The whole Surface JNI class is stubbed because OH has no Android Surface
equivalent (real rendering goes via BLASTBufferQueue/hwui, not the Surface JNI); `nativeLockCanvas` is the software-canvas
path fd-plus uses.

**Why the "one-.o" premise does not hold:** the stub *is* one .o, but a working `nativeLockCanvas` must (a) dequeue an
OH buffer + CPU-map + flush — reusable from `benchmark/2026-10-01-anativewindow-lock` + the existing OH window helpers —
AND (b) back the returned Java Canvas with a GraphicsJNI `SkBitmap` over the mapped pixels. The runtime has **not wired
GraphicsJNI** (`AndroidRuntime.cpp:1227` "GraphicsJNI prior init that we haven't wired"), and **libhwui** (the Skia
engine, be59260f) has **no reproducible frozen source** (DIGEST 610; cx-bms already deferred libhwui work). So (b) is
blocked on an un-reproducible Skia engine — not a single runtime .o this round.

**Verdict:** ALIVE in principle, **defer from the U13-easy batch.** Layer when unblocked: runtime JNI
(`android_graphics_compat_shim.cpp`) + the GraphicsJNI/Skia software-Canvas path, gated on recovering a reproducible
libhwui source (the DIGEST 610 prerequisite). Writing a half-impl that returns a Canvas the Skia side cannot honor would
be worse than the honest stub.

## Who produces the final artifact
- #1 libnativeloader.so + #2 host route: **cx-bms** lineage (loader/host). Both are "copy reviewed mechanism + one line".
- If #1/#2 touch the runtime assembly, coordinate with **cc-t3** (final U13 runtime 18763dd4) — but neither #1 nor #2 is
  a runtime change (#1 is libnativeloader + policy; #2 is the host route), so the runtime 18763dd4 is unaffected.

## This round's rule
"Easiest" means the fix mechanism is already reviewed and the per-key delta is one data line (chessclock manifest row,
mcdonalds package whitelist). Verify the premise before writing: fd-plus was dispatched as a one-.o runtime JNI, but the
evidence shows its Skia Canvas backing is absent and libhwui is un-reproducible — report that and defer rather than ship a
Canvas the engine can't honor. Every prediction is "first fatal moves; next fatal/t20 unknown", with the confirmation gap
named (librealmc's full deps).

## Files
- `evidence/walls.txt` — the three first-fatals with line cites + the reviewed-mechanism pointers + the fd-plus blocker.
- `fix/chessclock-media_jni.md` — the manifest row + the reviewed loader/policy mechanism + prediction.
- `fix/mcdonalds-libz.md` — the one-line package whitelist addition + why not a root alias + prediction + confirmation gap.
