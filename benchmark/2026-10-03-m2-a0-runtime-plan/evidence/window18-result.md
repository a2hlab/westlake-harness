# Window 18 result (5cd, ENTRY=legacy, MODES='64'): mNativeObject read works; it is an ANW1 WRAPPER, not a bare OHNativeWindow

Board 5cd1e3dd, 17:10:56 LOCK → 106 s → UNLOCK; A0_EXPECT_FP gate passed; rollback clean (0/0/0), fingerprint unchanged
(821de739cf81). Entry (legacy 4ee07bb3) + worker (2cdfc47a) bind-mount verified.

## mNativeObject read — WORKS
```
[A0] entry reg: RegisterNatives(MainActivity.nativeSurfaceReady)=0 (app PathClassLoader path)
[A0] entry nativeSurfaceReady Surface.mNativeObject=0x7f11716c90 content=0,126,1200,1794 WL_A0_SV_OHWIN=0x7f11716c90
[A0] S5 mode64: OHNativeWindow=0x7f11716c90 GetSurfaceId rc=40001000 id=0 GetSurface=0
[A0] S5 CreateNWeb -> 0 ; RESULT FAIL stage=S5
```
The JNI GetLongField read of `android.view.Surface.mNativeObject` works (0x7f11716c90, non-zero). But
`OH_NativeWindow_GetSurfaceId` returns **rc=40001000** on it. t28 = blank (window18-mode64-blank-t28.jpeg).

## Root cause — mNativeObject is an AOSP ANW WRAPPER (magic ANW1), not OH's OHNativeWindow
The runtime's own shim logs (hilog-all) show the SurfaceView holder Surface's mNativeObject is a **wrapper**:
```
OH_AnwShim: oh_anw_wrap[probe]: oh=0x7F1172DA10 -> aosp_anw=0x7F11716C90 (magic=ANW1) uniqueId=0x341000008de (rc=0)
OH_WindowMgrClient: oh_rs_get_child_surface_window: session=1492 childKey=0x7f117fb240 child composed
                    uniqueId=0x341000008de anw=0x7F11716C90 (1200x1794)
OH_GfxShim: BBQ.update: SurfaceView 'SurfaceView[org.westlake.a0probe/…MainActiv' -> dedicated child surface anw=0x7F11716C90
OH_NWSeed: [BBQ.update-stamp] SET_BUFFER_GEOMETRY shim=0x7F11716C90 oh=0x7F1172DA10 1200x1920 rc=0
OH_GfxShim: S_nativeGetFromBlastBufferQueue(bbq=0x7f117fb240 sessionId=1492) -> ohNativeWindow=0x7F11716C90
```
So:
- `mNativeObject` = **aosp_anw wrapper** 0x7f11716c90 (magic=ANW1) — the runtime's own `android::(anonymous)::OHNativeWindow`
  (same NAME as OH's, different TYPE).
- The **real OH window** = `oh=0x7F1172DA10` (what `oh_anw_wrap` wrapped).
- The surface **uniqueId = 0x341000008de** is already known (both oh_anw_wrap and oh_rs_get_child_surface_window print it).

`OH_NativeWindow_GetSurfaceId(wrapper)` fails rc=40001000 because the wrapper is NOT an OH OHNativeWindow — it must be
unwrapped to `oh=0x7f1172da10` first (or the uniqueId taken from the wrapper struct) before GetSurfaceId/GetSurface.

The fd-plus "mNativeObject == bare OHNativeWindow" holds for the **BBQ.getSurface direct** case; the **SurfaceView** path
adds the ANW1 wrapper layer (oh_anw_wrap[probe] + oh_rs_get_child_surface_window). This refines the fd-plus understanding.

## Window-19 direction (outer)
Statically find (a) the `android::(anonymous)::OHNativeWindow` (magic ANW1) wrapper struct definition and (b) what
`[STAGE2-SURFACEVIEW] oh_rs_get_child_surface_window` stores into mNativeObject; extract the real OH window / sptr<Surface>
/ child node from the wrapper and feed NWeb. All field offsets by source + disassembly (double-checked). Then window 19.
Share the conclusion with cc-wiki (its SurfaceFromJava + fd-plus depend on this type).

## Verdict
- Window-18 mNativeObject read: **PASS** (mechanism works, 0x7f11716c90 obtained).
- mode 64 on screen: **FAIL** — mNativeObject is an ANW1 wrapper; GetSurfaceId needs the unwrapped oh (→ window 19).
- The fix (window 18) is correct as far as it goes; the remaining gap is unwrapping the ANW1 wrapper.
