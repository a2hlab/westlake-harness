# Window 17 result (5cd, ENTRY=legacy, MODES='64 32'): fix ① + ② proven; mode 64 blocked on ANativeWindow_fromSurface

Board 5cd1e3dd, 16:58:33 LOCK → 175 s → UNLOCK; A0_EXPECT_FP=821de739cf81 gate passed; rollback clean
(bundle_entries=0, live_processes=0, leftover_dirs=0, param=0); runtime fingerprint unchanged (821de739cf81, 124 files);
0 uninstall residue. Entry (legacy d7219220) + worker (f72d6e49) bind-mount verified on-board.

## ① nativeSurfaceReady registered by the ENTRY — WORKS
```
[A0] entry JNI_OnLoad pid=22607 (runtime load point)
[A0] entry: nativeSurfaceReady registration thread started
[A0] entry reg: RegisterNatives(MainActivity.nativeSurfaceReady)=0 (app PathClassLoader path)
[A0-JAVA] surfaceCreated -> nativeSurfaceReady loc=0,126 size=1200x1794 (attempt 0)
[A0] entry nativeSurfaceReady fromSurface=0 ANW=0 content=0,126,1200,1794 WL_A0_SV_ANW=(not set)
```
RegisterNatives returned 0 and the entry's impl ran on the **first** surfaceCreated attempt (no UnsatisfiedLinkError, no
retry). The outer's correction was decisive: the app class MainActivity is reached via
`ActivityThread.currentApplication().getClassLoader().loadClass(...)` (app PathClassLoader), NOT a native-thread FindClass
(system CL). The registration thread polled until currentApplication() was non-null, then registered. **This is the
formal-backend registration mechanism, proven on-board.**

## ② mode-32 child bounds off the status bar — WORKS (ON SCREEN)
```
[A0] S5 child bounds offset from WL_A0_CONTENT_XY='0,126,1200,1794' -> (0,126) size 720x720 (content area)
[A0] S5 child node=… parent=… GetSurface=0x7f0d78c2b0 (bounds 0,126,720x720)
[nweb_impl.cc:1180] CreateNWeb NWebId: 1 successfully
[A0] S5 CreateNWeb -> 0x7f0d9f8138 ; S7 console: A0 JS ran ; S7 OnPageLoadEnd code=200
```
**t28 (window17-mode32-contentarea-t28.jpeg): status bar (05:00 / wifi / 85%) fully visible; the green #12ab34 page +
black 「中文 A0 探针」 sits BELOW it starting at y≈126.** Status bar no longer covered (window-16 was at 0,0). The entry
publishes the SurfaceView's getLocationInWindow rect as WL_A0_CONTENT_XY; the worker offsets the child by it. Criterion met.

## mode 64 — registration OK, but ANativeWindow_fromSurface unresolved in the entry ns
```
[A0] entry nativeSurfaceReady fromSurface=0 ANW=0 …           <- dlsym(RTLD_DEFAULT,"ANativeWindow_fromSurface")=0
[A0] S5 mode64: WL_A0_SV_ANW absent (SurfaceView not ready within timeout) -> FAIL
[A0] S5 surfaceview surface=0 ; S5 CreateNWeb -> 0 ; RESULT FAIL stage=S5
```
**t28 (window17-mode64-blank-t28.jpeg): blank white content area (no render).** The window-16 theory (app-ns can't open
the hook) was incomplete: `ANativeWindow_fromSurface` is not reachable via `dlsym(RTLD_DEFAULT)` in the **entry's**
namespace either (`fromSurface=0`). Registration and the Java hand-off are fine (the impl ran); the single remaining gap is
obtaining the native window from the Surface object.

### Window-18 fix (outer directive)
Stop using `ANativeWindow_fromSurface`. In the entry's nativeSurfaceReady, read `android.view.Surface.mNativeObject`
(a `long`) via JNI `GetLongField` — cc-wiki fd-plus established that in this runtime it is already an `OHNativeWindow*`
(re-verify against the runtime Surface source). Then OH_NativeWindow_GetSurfaceId → SurfaceUtils::GetSurface → NWeb,
skipping the oh_anw_get_oh unwrap. mNativeObject==0 → log + FAIL. Window 18: single mode 64 on 5cd.

## Verdict
- ① entry RegisterNatives via app PathClassLoader: **PASS** (RegisterNatives=0, impl ran attempt 0).
- ② mode-32 content-area bounds: **PASS** (screenshot: page below the status bar, bar visible).
- mode 64: **FAIL** at S5, root cause isolated to `ANativeWindow_fromSurface` symbol resolution (→ window 18).
