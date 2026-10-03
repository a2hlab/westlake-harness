# Window 17 build: nativeSurfaceReady registered by the ENTRY (not app-ns a0shim) + mode-32 content-area bounds

All artifacts x2 byte-identical (hw248, OH clang feef13a3). Pins updated in run_a0.sh + build_apk.py.

| artifact | sha256 | built by | note |
|---|---|---|---|
| worker `libwl_a0_nweb.so` | `f72d6e49…60354606` | build_win7_hw248.sh | mode-32 bounds now read WL_A0_CONTENT_XY |
| entry default `libwestlake_html_compat.so` | `86da801c…376bc4c5` | build_win7_hw248.sh | +JNI_OnLoad RegisterNatives |
| entry legacy `libwestlake_html_compat.legacy.so` | `d7219220…51b953e1` | build_win7_hw248.sh | same + nweb_ns_legacy |
| `liba0probe.so` (vestigial) | `44016cff…e9ed624f` | build_a0_hw248.sh | dead path; rebuilt only to match source |
| `liba0shim.so` | `5a2e7aaa…2a90a43c89` | build_a0_hw248.sh | nativeSurfaceReady REMOVED (moved to entry); nativeStart only |
| APK `a0probe.apk` | `4630b858…408c95b3` | build_apk.py (Mac, x2) | v4 |

## Fix ① — nativeSurfaceReady registered from the runtime entry (not the app-ns a0shim)

Window-16 root cause (outer): the APK's `a0shim` runs in the **app linker namespace**, where `ANativeWindow_fromSurface`
does not resolve to the bridge's hook (`[A0-SHIM] … ns wl_a0probe … open=0`), so `WL_A0_SV_ANW` was never set and the
worker timed out. The surface→ANativeWindow conversion must happen in the **runtime-adjacent** namespace where the entry
(B7BindFixes `System.load`) lives — the same load path the formal cc-wiki backend shim uses.

- **a0_entry.cpp** (`JNI_OnLoad`, which receives the `JavaVM*`): caches `g_jvm`, spawns a detached thread that
  `AttachCurrentThread` + retries `TryRegister` (~30 s) then detaches.
- **The classloader trap** (outer's correction, confirmed): a `FindClass` on a native-attached thread uses the **system**
  classloader, and `JNI_OnLoad`'s implicit env uses B7BindFixes's (framework) loader — neither can see the app class
  `org.westlake.a0probe.MainActivity`. `TryRegister` reaches the app `PathClassLoader` via
  `android.app.ActivityThread.currentApplication()` → `getClassLoader()` → `loadClass("org.westlake.a0probe.MainActivity")`,
  then `RegisterNatives`. `ActivityThread/Context/ClassLoader` are framework classes the system CL *can* `FindClass`.
- **Retry is required**: `currentApplication()` is null until the stock `handleBindApplication`/`makeApplication` has run
  (repo U11d: U11c installed before that returned → `currentApplication()` null → no-op). The thread polls every 250 ms.
- **The registered impl** `A0_nativeSurfaceReady(env, clazz, surface, x,y,w,h)` runs in the entry's namespace:
  `ANativeWindow_fromSurface` (dlsym) → `setenv WL_A0_SV_ANW` (mode 64); and `setenv WL_A0_CONTENT_XY="x,y,w,h"` (mode 32).
- **a0shim.c**: `nativeSurfaceReady` deleted (and its explicit `setenv` extern). Only `nativeStart` remains (vestigial
  liveness log; its `open=0` failure is the known baseline).
- **MainActivity.java**: `nativeSurfaceReady(Object,int,int,int,int)`; `surfaceCreated` passes
  `surfaceView.getLocationInWindow()` + size, and retries (20×150 ms) catching `UnsatisfiedLinkError`, logging
  `nativeSurfaceReady not yet registered by entry` / `STILL unregistered after retries`.
- **Static confirmation**: entry exports `T JNI_OnLoad`; its only undefined symbols are libc
  (`HiLogPrint, dlsym, pthread_create/detach, setenv, snprintf, fprintf, usleep, …`) — **no JNI symbols undefined**,
  because JNI calls go through the `JavaVM`/`JNIEnv` function tables. `--no-undefined` passed.
- **environ is shared across musl namespaces in-process** (single libc), so the entry's `setenv` is visible to the worker
  in `nweb_ns` via `getenv` — same mechanism the bridge uses for `WESTLAKE_NATIVE_WINDOW_PTR`.

### cc-wiki backend classloader (outer asked to confirm)
`nweb_backend.cpp` is in the cc-wiki worktree (not here), so I did not open it. Principle: its `NativeNWebBackend` is a
**runtime-JAR** class (oh-adapter-runtime.jar), loaded by the boot/runtime classloader, which the system CL *can* see — so
a plain `FindClass`/`JNI_OnLoad` registration works there with no `currentApplication()` dance. Only **app** classes
(like this probe's MainActivity) need the PathClassLoader route. cc-wiki should self-verify the exact loader it uses.

## Fix ② — mode-32 child bounds off the status bar

Window-16 mode-32 used `SetBounds(0,0,720,720)` under the bridge window node, covering the status bar. Now
`GetChildSurface` polls `WL_A0_CONTENT_XY` (published by the entry on `surfaceCreated` from the SurfaceView's
`getLocationInWindow` — the content-area top-left below the status bar), parses `x,y,w,h`, and offsets the child to
`SetBounds(x, y, 720, 720)`. Absent/parse-fail → fallback `0,0` with a clear log (mode 32 still renders, just at the top).
The RSSurfaceNodeConfig genstub, the 5 RS symbols, and the mode-0 RefBase slot are unchanged (worker RS UND = the same 5;
only env-poll + sscanf + SetBounds args added).

## Determinism / pins
- build_win7_hw248.sh now emits BOTH entry variants from one source (`-DWL_A0_LEGACY_NS` for the legacy filename), with
  `-I src/native/include` for jni.h; build_a0_hw248.sh gained `-DOHOS_PLATFORM` + `-l:librender_service_client.z.so` to
  match the worker (a0probe.cpp's mode-32 RSTransaction needs it).
- run_a0.sh: APK_SHA=4630b858, RT_WORKER_SHA=f72d6e49, RT_PROBE_SHA default=86da801c / legacy=d7219220.
- build_apk.py NATIVE: liba0probe=44016cff, liba0shim=5a2e7aaa.

## Window 17 ask
ENTRY=legacy, MODES='64 32'; A0_EXPECT_FP=821de739cf81; independent per-mode verdicts. Criterion = t28 shows the
`#12ab34` page **within the content area** (not covering the status bar). Expect `[A0] entry reg: RegisterNatives(…)=0`
then `[A0] entry nativeSurfaceReady … WL_A0_SV_ANW=0x…` for mode 64, and `child bounds offset from WL_A0_CONTENT_XY` for
mode 32.
