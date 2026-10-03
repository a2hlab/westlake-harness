# Window 19 result (5cd, ENTRY=legacy, MODES='64'): FORMAL route-A SurfaceView path renders ON SCREEN

Board 5cd1e3dd, 17:24 LOCK → 118 s → UNLOCK; A0_EXPECT_FP gate passed; rollback clean; fingerprint unchanged
(821de739cf81). **mode 64 (cc-wiki Plan A, the formal route-a surface path) renders the ArkWeb page on the SurfaceView.**

## The full chain works
```
[A0] entry nativeSurfaceReady Surface.mNativeObject=0x7f11816c90 content=0,126,1200,1794 WL_A0_SV_OHWIN=0x7f11816c90
[A0] S5 mode64: AdapterAnw=0x7f11816c90 magic=ANW1 -> oh(+0xc0)=0x7f118138d0 ; oh_anw_get_oh=0 (gate may null it)
[A0] S5 mode64: OHNativeWindow=0x7f118138d0 GetSurfaceId rc=0 id=3577707759841 GetSurface=0x7f1156b010
[A0] S5 CreateNWeb -> 0x7f0b2fc278
[A0] S7 console: A0 JS ran ; S7 OnPageLoadEnd code=200
[A0] RESULT FAIL stage=S8 … console_js=1 load_end=1     (FAIL = no consumer frame counter on this path; judge by screenshot)
```
**t28 (window19-mode64-ONSCREEN-t28.jpeg): status bar visible (05:26 / wifi / 85%); the whole content area is #12ab34
green with black 「中文 A0 探针」** — the page painted on the SurfaceView. Criterion met.

## Why the direct offset-read was necessary (not oh_anw_get_oh)
`oh_anw_get_oh=0` in the log: the exported unwrap returned null because its **directPathLive gate** (byte @0x149, from the
window-19 disasm) is not satisfied for a SurfaceView AdapterAnw (never oh_anw_configure_direct_path'd). The direct,
magic-validated read of `oh` @+0xc0 bypasses the gate and yields the valid handle (GetSurfaceId rc=0). Had we used the
exported function, window 19 would have failed identically to window 18.

## The mode-64 formal path, resolved across three windows
1. W17: registration — `RegisterNatives` from the entry via the app PathClassLoader (currentApplication()). ✓
2. W18: obtain the native window — read `Surface.mNativeObject` (ANativeWindow_fromSurface was unresolvable). ✓ but it is
   an ANW1 wrapper.
3. W19: unwrap — `mNativeObject` is an AdapterAnw (magic 'ANW1'); real `oh` @+0xc0 → GetSurfaceId → GetSurface → NWeb. ✓

## Verdict
- mode 64 (formal route-a SurfaceView path): **PASS — ON SCREEN** (ground truth screenshot).
- All three route-a in-process ArkWeb surface sources now proven on 5cd: mode 0 (headless readback), mode 32 (own child
  node, content area), mode 64 (SurfaceView holder Surface = the formal backend path).

## For cc-wiki
SurfaceFromJava: `mNativeObject` is an AdapterAnw (ANW1); take `oh` at +0xc0 after the magic check, NOT the exported
oh_anw_get_oh (its directPathLive gate returns null for a plain SurfaceView child) — or call oh_anw_configure_direct_path
first. GetSurfaceId must be on the unwrapped oh.
