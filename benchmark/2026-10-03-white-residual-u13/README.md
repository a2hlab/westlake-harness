# White/black residual after U13 (9 keys): two mechanisms, both still unowned; U14 changes only jiten (M5 raises its own server dialog); M3's root is one RTLD_DEFAULT lookup in the runtime's EGLImpl that U13 left unchanged

#90, offline. No board was touched. Input: cluster C15 of `2026-10-03-u13-first-fatal-clusters` (49e6f805da), i.e. the
9 keys that are alive at t20 with a white/black window and no fatal line.

## What the data is

**None of the 9 ran in U13.** The window 1 and window 2 sign-offs (`window1-signoff`, `window2-signoff`) contain none
of them, and window 3 has none either.

So every row is the key's latest **U12** stage-A run (runtime jar 0482c9b1, U10.1T8 native).

| | |
|---|---|
| **Lit population** for the "does a lit key carry the same condition?" check (the double-copy lesson) | every U13 window-1/2 run of a key the outer signed lit in all its runs: **60 keys, 81 runs** |
| Extractor (`features.py`) | imports the tools that found each mechanism, not copies: `white-vs-lit/multiwin.py` (M1), `vrt.py` (M2, WebView ≥ half screen), the M3 marker (`GLSurfaceView: … IllegalArgumentException: Make sure`), `white-unexplained-4/evidence.py` (M4 no session, M5 dialog before main), `white-m6-finish-return/closes.py` (M6 top close dropped) |

## The separation table (`separation.py` → `separation.json`)

| condition | white residual (9) | lit U13 (60 keys / 81 runs) | separates? |
|---|---|---|---|
| **M2** full-screen WebView | **6** | **0 / 0** | **yes**. On U10.1T8, 1/117 lit (caniwebview: its own native controls are around the blank WebView). |
| **M3** GLSurfaceView EGL IAE | **3** | **0 / 0** | **yes**. No lit U13 key uses GLSurfaceView at all. On U10.1T8, 1/117 lit (shadereditor: GL view not its main UI). |
| M5 dialog before main window | 1 (jiten) | 5 / 5 (rpn, trickytripper, ruler, newpipe, opencamera) | **no**. Lit when the Activity on top has content (the M5 watchlist). |
| M1 / M4 / M6 | 0 | 0 | not present |
| SurfaceView ≥ half screen | 2 | 1 (opencamera) | weak |
| WebView proxy seeded (`B8-WEBVIEW`, J8/J10) | 9 | **60 / 81** | **no**. Every process has it, so it is not the white cause. |

**Every residual key carries exactly one separating condition.** M2 and M3 never co-occur.

## Per key (`features.json`, `evidence/`)

| key | U12 run | mechanism | U13 (18763dd4 runtime, M1 shim) | U14 | status |
|---|---|---|---|---|---|
| cv2-ca-vaults-randomlydie | 5cd w4 | M2 (CapacitorWebView full screen, local SPA) | 0 | 0 | **unowned** (plan only) |
| cv2-com-degeder-yam | 61b w4 | M2 (CapacitorWebView, local SPA) | 0 | 0 | **unowned** (plan only) |
| cv2-com-paultirk-yatoo | 5cd w4 | M2 (CapacitorWebView, virtual-HTTPS local SPA) | 0 | 0 | **unowned** (plan only) |
| cv2-timur-webrtc-check | 5ea w4 | M2, black (WebView, local index) | 0 | 0 | **unowned** (plan only) |
| fd-tutanota | 61b w3 | **M2 (new)**: WebView full screen; ships local `assets/tutanota/index.html` + 1562 JS. U10.1T8 reference = dead; on U12 it is alive and white (t20 checked). | 0 | 0 | **unowned**; not in the WebView plan's target list |
| **cv2-dev-obfusk-jiten-webview** | 5cd w4 | M2 **+ M5**: `MainActivity.onCreate` calls `chooseServer()` when no server is saved (always on a fresh install). That is an AppCompat AlertDialog with title, message, a pre-filled URL EditText and OK. Its window (session 896, androidType 2) **has its Surface** (`BBQ.getSurface` non-null) and sits at zOrder 102 under the white WebView Activity window (897, zOrder 103). | 0 | **bridge 7daa5435 M5 raises the dialog** | **U14-covered (picture)** |
| cv2-com-bytehamster-flowitgame | 61b w4 | M3 | 0 (EGL JNI unchanged, §M3) | 0 | **unowned** |
| fd-app (Unciv) | 5cd w4 | M3 (+ bg `MediaStore.scanFile` NSME, kept alive) | 0 | 0 | **unowned** |
| fd-shatteredpixeldungeon | 5cd w2 | M3 | 0 | 0 | **unowned** |

**Split.**

| | keys | members |
|---|---|---|
| U14-covered | 1 | jiten (picture change) |
| truly unowned | 8 | M2 ×5 (randomlydie, yam, yatoo, webrtc-check, tutanota); M3 ×3 (flowitgame, Unciv, SPD) |

## M3: the root is in the runtime's EGLImpl, and U13 did not touch it (`evidence/u13-runtime-egl-static.txt`)

**U13 left the EGL code alone.** U13 runtime 18763dd4 compared with ac59 (the control rebuild that equals ac59), with
`equiv.py`:
- 30 functions differ: BBQ_nativeUpdate/GetSurface, `sc_to_oh_native_window`, AAssetManager_fromJava, and sqlite
  layout noise;
- **no EGL function differs**; `jni_eglCreateWindowSurface` is equal after residual resolution.

**The lookup in `jni_eglCreateWindowSurface`:**
- `from_surface = dlsym(RTLD_DEFAULT, "ANativeWindow_fromSurface")`;
- it is cached once under a static guard;
- there is **no fallback**.

**What sits next to it.**
- The sibling `unwrap` resolver (`$_0`, `oh_anw_get_oh`) **does** fall back:
  `dlopen("liboh_adapter_bridge.so", RTLD_NOW|RTLD_NOLOAD)` + `dlsym`.
- The runtime itself **exports `ANativeWindow_fromSurface` (0x197388)**.

This matches `2026-10-02-white-m3-glsurfaceview`'s leading hypothesis:
- the failing GL thread never enters the converter (no `OH_NWFromSurface [STAGE0] ENTER` on that thread);
- the IAE branch is the null-converter branch;
- a cached null never retries.

## Minimal fixes and predictions

**M3 (3 keys), runtime, one function.**
- **Change.** In the EGLImpl `oh_window_from_surface` lookup, bind `from_surface` to the runtime's own
  `ANativeWindow_fromSurface` (a direct reference; the symbol is in the same image) instead of the RTLD_DEFAULT-only
  lookup. Do not retry a blind RTLD_DEFAULT. Add one HiLog line at the conversion: GL TID, converter address, Java
  Surface / `mNativeObject`, result.
- **Where.** It goes in the runtime `oh_egl_impl.cpp`, as a single-function change on the U13 runtime source that
  already rebuilds ac59 / 18763dd4.
- **Prediction.**
  - **The IAE disappears for flowitgame, Unciv, SPD (medium, conditional)**. The condition: the null came from the
    lookup and not from a null Surface jobject. The HiLog line tells the two apart.
  - Lit: flowitgame medium (no other native libs), SPD medium, Unciv low–medium (it also has the bg NSME).
  - 0 for every other key: no lit key uses EGLImpl window surfaces, and hwui's EGL path is separate.
- **Runtime behaviour, so a minimal key experiment rather than more analysis.** flowitgame alone, ≤ 10 min, on a
  free board.
  - **Pass:** the GL TID enters the converter, a non-null AdapterAnw equals the SurfaceView child,
    `eglCreateWindowSurface` succeeds, and there is no IAE.
  - **Fail with a null jobject:** the fix belongs in the Java→JNI Surface handoff instead.

**M2 (5 unowned keys).**
- **No small fix.** Every process has only the empty proxy provider. `2026-10-03-webview-provider-plan` is the owner of
  the route, at plan stage with no build. Its phase 1 is a fresh-process Chromium with local software content.
- **First-fatal move:** 0 for all.
- **Content targets of that plan's phase 1:** randomlydie, yam, yatoo, webrtc-check, plus **fd-tutanota**, which the
  plan does not list yet (local `index.html` + JS).

**jiten (U14).**
- Bridge M5 puts its own "choose server" dialog on top. **Predicted t20: its own native dialog (medium-high; the dialog
  has its Surface on U12 already)**, with the blank WebView behind it.
- By the M5 watchlist rule this is own UI, so a signer should not read it as a fallback.
- Its content still needs M2 phase 2 (remote HTTPS).

## What was wrong before

- C15 was listed as one "unowned residual" because first-fatal clustering cannot split it. With the window-level
  features it is two mechanisms (M2 6, M3 3), each absent from all 60 lit U13 keys. One key (jiten) also carries M5,
  which U14 changes.
- fd-tutanota was a "dead" reference key. On U12 it is alive with a full-screen WebView: M2, not a death.

## Rules this round sets

- **Before calling a condition the cause of white, count it in the latest lit runs.** The WebView proxy marker is in 9/9
  white keys and in 81/81 lit runs, so it is not the cause.
- **When a static cache resolves a symbol through RTLD_DEFAULT only, check whether the same library defines it.** Here
  it does (0x197388). The sibling resolver in the same file already has the NOLOAD fallback the first one lacks.

## Files

- `features.py` → `features.json`; `separation.py` → `separation.json`.
- `evidence/jiten-dialog.txt`: hilog sessions, zOrder, BBQ surfaces; dexdump of `onCreate` / `chooseServer`.
- `evidence/u13-runtime-egl-static.txt`: equiv summary, the from_surface lookup, the unwrap fallback, the runtime export.
- `results.json`.
