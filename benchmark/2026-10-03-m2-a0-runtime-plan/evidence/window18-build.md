# Window 18 build: mode 64 reads Surface.mNativeObject (OHNativeWindow*) instead of ANativeWindow_fromSurface

All x2 byte-identical (hw248, OH clang feef13a3). Only a0_entry.cpp + a0probe.cpp changed (a0shim.c/MainActivity.java
untouched → a0shim stays 5a2e7aaa).

| artifact | sha256 | change |
|---|---|---|
| worker `libwl_a0_nweb.so` | `2cdfc47a…bc0f60f9` | GetSurfaceViewSurface reads WL_A0_SV_OHWIN, uses it directly (no oh_anw_get_oh) |
| entry default `libwestlake_html_compat.so` | `2480e869…b17f7fa6` | nativeSurfaceReady reads Surface.mNativeObject via GetLongField |
| entry legacy `…legacy.so` | `4ee07bb3…c11716fc4` | same + nweb_ns_legacy |
| `liba0probe.so` (vestigial) | `610b0d57…9078ffa7` | rebuilt from a0probe.cpp (dead path) |
| `liba0shim.so` | `5a2e7aaa…2a90a43c89` | UNCHANGED |
| APK `a0probe.apk` | `850e0768…ed937b09` | v5 (new liba0probe) |

## The fix (outer directive, after window-17 fromSurface=0)
Window 17 proved mode-64 registration works but `dlsym(RTLD_DEFAULT,"ANativeWindow_fromSurface")=0` in the entry ns.
Replacement path, no NDK symbol:
- **Entry** `A0_nativeSurfaceReady`: `env->GetObjectClass(surface)` → `GetFieldID("mNativeObject","J")` →
  `GetLongField` → publish as `WL_A0_SV_OHWIN`. `mNativeObject==0` → log `(not set; mNativeObject=0 -> FAIL)`.
- **Worker** `GetSurfaceViewSurface`: poll `WL_A0_SV_OHWIN`, parse → `OHNativeWindow*` **directly** →
  `OH_NativeWindow_GetSurfaceId` → `SurfaceUtils::GetSurface`. The `oh_anw_get_oh` unwrap is gone (no AdapterAnw wrapper).

## Runtime-source re-verification (outer asked)
Confirmed against the landed cc-wiki finding `benchmark/2026-10-03-u17-fd-plus-surface/README.md:12-14`: the runtime's
Surface nativeObject **is** the `OHNativeWindow*` — `S_nativeGetFromBlastBufferQueue` returns `b->ohNativeWindow`, and the
runtime's own `ANativeWindow_fromSurface` casts `mNativeObject` straight to it. So `GetLongField(mNativeObject)` yields the
same pointer `ANativeWindow_fromSurface` would have, without needing the (unresolvable) symbol. (The cc-wiki fd-plus A2
lockCanvas treats `mNativeObject` as a bare `OHNativeWindow*` throughout — src/a2-lockcanvas.inc.cpp:100,160.)

## Static
Entry UND = libc only (no JNI symbols; GetObjectClass/GetFieldID/GetLongField go through the JNIEnv function table).
Worker RS imports unchanged (5 RS symbols). `--no-undefined` passed.

## Pins
run_a0.sh: APK_SHA=850e0768, RT_WORKER_SHA=2cdfc47a, RT_PROBE_SHA default=2480e869 / legacy=4ee07bb3.
build_apk.py NATIVE: liba0probe=610b0d57, liba0shim=5a2e7aaa.

## Window 18 ask
ENTRY=legacy, MODES='64' (single mode 64); A0_EXPECT_FP=821de739cf81. Expect
`[A0] entry nativeSurfaceReady Surface.mNativeObject=0x… WL_A0_SV_OHWIN=0x…`, then
`[A0] S5 mode64: OHNativeWindow=0x… GetSurfaceId rc=0 … GetSurface=0x…`, CreateNWeb non-null, and t28 = #12ab34 page on
the SurfaceView (content area).
