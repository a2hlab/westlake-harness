# Fix (proposal) — chessclock: media_jni owner alias, one manifest row + the reviewed loader/policy mechanism

Owner to integrate: cx-bms (libnativeloader lineage). cc-wiki delivers the exact edit; NOT landed to bms/src here
(outside land.py prefixes). Verdict: **ALIVE**. Layer: **native / config** (libnativeloader policy + loader).

## The one manifest row (data) — add to native_bridge_policy.v1.json `system_libraries`
```json
    { "soname": "liboh_adapter_bridge.so", "path": "/system/android/lib64/liboh_adapter_bridge.so" },
+   { "soname": "libmedia_jni.so",        "path": "/system/android/lib64/liboh_android_runtime.so" }
```
This is the alias tuple: the framework JNI SONAME `libmedia_jni.so` resolves to the already-resident runtime
`liboh_android_runtime.so`, which already hosts the android_media_MediaPlayer JNI methods (49/49 registered,
native_init=1, native_setup=1 — native-missing-libraries).

## The reviewed mechanism to carry over (already authored in benchmark/2026-10-01-native-missing-libraries/patches.json)
1. `native-loader-oh/src/system_loader.cpp`: for `library->soname == "libmedia_jni.so"`, open with
   `RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD` (resident-only: the runtime is already mapped; do not load a second copy),
   log `[U9-MEDIA-OWNER] request=libmedia_jni.so owner=<resolved> handle=<p> resident-only=1`.
2. `native-loader-oh/tests/verify_bridge_policy.py`: permit EXACTLY the one tuple
   `(soname="libmedia_jni.so", path="/system/android/lib64/liboh_android_runtime.so")`; every other SONAME/path
   mismatch keeps its rejection (the checker change is one alias tuple, not a general relaxation).
3. Rebuild **libnativeloader.so** (every same-generation payload/route copy), with the usual native_predeploy N1/N2 +
   two-build byte-identical + deployed_strings_diff acceptance.

## Prediction (move + evidence)
- **First fatal MOVES.** The current terminal is `J_invokeStaticMain_main_threw: ULE "system library is absent from
  the adapter manifest"` at `System.loadLibrary("media_jni")` inside `MediaPlayer.<clinit>` (hilog:43043), reached via
  `ChessClock.onCreate:153 -> setUpGame:744 -> initRingtone:243`. Once the alias resolves loadLibrary to the resident
  runtime (methods already registered + native_init stub returns), `MediaPlayer.<clinit>` completes, Ringtone/
  RingtoneManager proceed, and `ChessClock.onCreate` continues past line 153.
- **Next fatal / t20: UNKNOWN.** media_jni is a registered STUB, not a real decoder; a chess clock only needs
  the Ringtone <clinit> to not throw, so UI is plausible but not asserted here (screenshots are ground truth).
- Scope: only this one app pattern; the tuple is exact, no other SONAME changes, no root alias, no default fallback.
