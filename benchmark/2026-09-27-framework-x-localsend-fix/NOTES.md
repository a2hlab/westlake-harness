# Framework merged fix: X telephony NPE + LocalSend Impeller (#48 horizontal, 5ea34a45 only)
date: 2026-09-27  (base a2hlab-framework-cab462ff; do NOT touch 61b0657200000000000000000324012c Toutiao)

Two framework-level walls, both R2-pinned by claude-2, fixed with 3 small source edits in ONE jar
(**adapter-runtime-bcp.jar** / BCP — confirmed: all 3 classes live there). Patch: framework-fix.patch.

## Fix 1 — X (Twitter) telephony NPE
Twitter registers a PhoneStateListener → `TelephonyManager.listen/listenWithEventList` resolves
ITelephonyRegistry from `ServiceManager.getService("telephony.registry")` = **null** →
`ITelephonyRegistry.Stub.asInterface(null)` = null → `null.listen()` NPE (`com.twitter.util.telephony.a.run`).
westlake's `OHServiceManager.lookupAdapter("telephony.registry")` fell through to the `default: return null`.
FIX (2 edits, reuse the existing LocalServiceBinders no-op-binder infra):
- `framework/core/java/OHServiceManager.java`: add `case "telephony.registry": return LocalServiceBinders.get(name);`
- `framework/core/java/LocalServiceBinders.java`: add `case "telephony.registry":` → `proxy(name,
  "com.android.internal.telephony.ITelephonyRegistry", (call,args)->DEFAULT)`. The `proxy()` helper
  loads the AIDL interface **by name at runtime** (`Class.forName`) and attaches a dynamic Proxy to a
  local Binder, so `Stub.asInterface` resolves it without a transaction and every method (listen/
  listenWithEventList/listenForSubscriber/…) answers the type default (void → no-op). Twitter's
  listener registers, gets no phone-state callbacks, and never NPEs. NO compile-time dep on
  ITelephonyRegistry (string-loaded), so it builds against the existing classpath.

## Fix 2 — LocalSend (Flutter) Impeller first-frame pc=0
Flutter's Impeller GLES ProcTable calls a NULL extension proc on the raster thread (slot #468 of the
.bss table at 0xaee000; OH's GLES driver returns NULL via eglGetProcAddress for an extension proc that
Impeller calls unconditionally — see benchmark/2026-09-27-localsend-impeller-re/). Force Skia GL
(defensive proc loader, tolerates missing ext procs) by injecting the Flutter opt-out meta-data:
- `framework/package-manager/java/ApplicationMetaDataReader.populate()`: before `info.metaData = result`,
  `if (!result.containsKey("io.flutter.embedding.android.EnableImpeller")) result.putBoolean(..., false);`.
  Global inject: only Flutter apps read the key (non-Flutter ignore it); an app that sets it explicitly
  is respected (containsKey guard). Flutter reads EnableImpeller=false → Skia GL → the ProcTable path
  that NULLs slot #468 is not taken → first frame renders.

## Build + deploy (claude-2 / build env) — I could not build from my session
All 3 classes compile into **adapter-runtime-bcp.jar** (BCP). The source build runs in the
`/home/dspfac/bridge-build` pipeline (compile_oh_adapter_runtime.sh → build_oh_adapter_runtime_slim.sh
→ build_aosp_fw.sh / gen_boot_image.sh), which is NOT accessible from my (zhaoyue) VM session, so I
deliver the authoritative source patch, not a built jar. Two build routes (claude-2 picks):
1. SOURCE rebuild in the bridge-build env: apply framework-fix.patch to the westlake tree (base
   22b9453 / framework-cab462ff), rebuild adapter-runtime-bcp.jar, regen the boot image (host dex2oat),
   stage into 5ea34a45. (Same pipeline the Layout-clamp deploy used.)
2. SURGICAL SMALI patch of the deployed adapter-runtime-bcp.jar (like the Layout-clamp CLAMP48 jar):
   baksmali → add the 2 switch cases + the metadata-inject → smali → repack → boot-image. I can produce
   the smali patch if given the exact deployed adapter-runtime-bcp.jar.
Then A/B on 5ea34a45: X reaches first screen past the telephony listen (no NPE); LocalSend shows a first
frame (Skia GL). Screenshots each. ONLY on 5ea34a45 — do not touch 61b06572 Toutiao delivery.

## Why these are safe / minimal
- Telephony: reuses the proven LocalServiceBinders no-op pattern (same as uimode/power/audio/…); no new
  compile deps; only affects apps that query telephony.registry (harmless no-op).
- Impeller: only Flutter apps read the meta-data; the containsKey guard respects an app's own setting;
  non-Flutter apps unaffected. Both changes are additive (new switch cases / one guarded putBoolean).
