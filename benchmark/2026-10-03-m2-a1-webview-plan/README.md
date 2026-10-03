# M2 A1 — real android.webkit.WebView end-to-end (the step before Wikipedia)

#90, cc-t3 produces the window plan; cc-wiki produces the artifacts. A0 proved in-process ArkWeb renders on all three
route-a surface sources (mode 0/32/64; window 19 = the formal SurfaceView path ON SCREEN). A1 replaces the hand-written
NWeb probe with a **real `android.webkit.WebView`** in a test APK, backed by cc-wiki's route-a WebView provider, loading a
`data:` page first, then a Wikipedia article in a follow-up window. Judged by the t28 screenshot (WebView area shows the
page), per the "screenshots are ground truth" rule.

## What's established (why A1 is reachable)
- The formal surface path works on-board (window 19): `android.view.Surface.mNativeObject` → AdapterAnw (magic 'ANW1') →
  unwrap `oh` @+0xc0 → `OH_NativeWindow_GetSurfaceId` → `SurfaceUtils::GetSurface` → `CreateNWeb` → page painted.
- `oh-adapter-runtime.jar` is **non-BCP** (PathClassLoader/DexClassLoader), at
  `/system/android/framework/oh-adapter-runtime.jar` — single-file bind-mount overlayable, NO boot-image rebuild
  (static: OHEnvironment.java:127 "non-BCP … no boot-image rebuild"; adapter_bridge.cpp:248 "PathClassLoader, non-BCP";
  compile_oh_adapter_runtime.sh:5 "the NON-BCP, DexClassLoader-loadable jar"). This is the key enabler: the WebView
  provider classes (org.westlake.webview.* + OhNWebProviderFix) ship in this jar and can be overlaid per-window.

## Overlay manifest (bind-mount during the window, rollback after — same mechanism as run_a0.sh mount_probe)
| on-board target | source (cc-wiki artifact) | loader | overlay |
|---|---|---|---|
| `/system/android/framework/oh-adapter-runtime.jar` | oh-adapter-runtime.jar candidate (org.westlake.webview.* + OhNWebProviderFix) | PathClassLoader (non-BCP) | bind-mount single file |
| `/system/android/lib64/<shim>.so` | cc-wiki route-a WebView shim .so | B7BindFixes System.load | bind-mount (like libwestlake_html_compat.so) |
| `/data/local/tmp/<worker>.so` | cc-wiki route-a WebView worker .so | shim dlopen_ns | file send (like libwl_a0_nweb.so) |

Preconditions (gate before any write, per run_a0.sh): APK SHA pin, board connected + not held, A0_EXPECT_FP=821de739cf81
(U13) after-lock, no leftover install. Each overlay source SHA-pinned; on-board content verified == pin after mount.
The jar overlay must verify the target is the expected deployed jar first (`sha256sum` the existing
oh-adapter-runtime.jar, record it) so rollback restores exactly it — unlike the .so targets which are absent on a clean
board, the jar ALREADY EXISTS, so we bind-mount OVER it and umount to restore (never rm the real jar).

## Rollback (trap, before UNLOCK)
umount the 3 overlays (jar first: `umount <jar target>` restores the original deployed jar; then the 2 .so);
`rm -f` only the pushed sources under /data/local/tmp and /system/android/lib64 (the .so targets, which were absent
pre-window); uninstall the test APK + sandbox dirs (run_a0.sh rollback()); `param` reset. Then runtime-fingerprint ==
after-lock (unchanged) AND == 821de739cf81, else keep the lock. Confirm the jar target `sha256sum` == the original
recorded value after umount.

## Test APK (cc-t3 builds, like a0probe.apk)
`org.westlake.a1webview`: an Activity with a full-content `android.webkit.WebView`; `webView.loadData(...)` the #12ab34
data: page (same HTML as A0). Follow-up window: `loadUrl("https://<wikipedia article>")`. No hand-written NWeb — the
WebView goes through cc-wiki's provider. Deterministic build ×2, pinned.

## Criterion
t28 screenshot: the WebView area shows the page (#12ab34 + 中文 for the data: window; the article for the Wikipedia
window). Independent per-window verdict; screenshot is ground truth (RESULT counters not authoritative for the WebView path).

## Technical item ① — unwrap entry stability (NOT the +0xc0 raw offset in formal code)
Window 19 used a raw `+0xc0` read of AdapterAnw because the exported `oh_anw_get_oh` returned null (its `directPathLive`
gate, byte @0x149, is not satisfied for a plain SurfaceView AdapterAnw). The raw offset is fine for a probe but brittle for
the formal provider (depends on sizeof(ANativeWindow)=192 staying fixed). Options, in order of preference:
1. **cc-wiki adds a gate-free export to the bridge candidate**: `OHNativeWindow* oh_anw_unwrap(ANativeWindow* aosp)` =
   `as_adapter(aosp)` magic-check then `return a->oh;` (NO directPathLive gate). This is a 3-line addition to
   oh_anativewindow_shim.cpp, exported from liboh_adapter_bridge.so. Formal code calls it; no offsets. **Record a line for
   the next runtime U**: "runtime exports oh_anw_unwrap (gate-free AdapterAnw→oh)".
2. If the gate must stay: call the exported `oh_anw_configure_direct_path(aosp, session_id, generation, w, h)` (the
   SurfaceView path has the session_id, e.g. 1492 from oh_rs_get_child_surface_window) BEFORE `oh_anw_get_oh` — then the
   gate passes. More plumbing (needs session_id/generation threading).
3. Near-term A1 only: cc-wiki's SurfaceFromJava may read `oh` @+0xc0 after the magic check (same as the proven probe) as a
   stopgap, with a TODO to switch to oh_anw_unwrap. Acceptable for A1 bring-up, not for a frozen provider.
Recommendation: **option 1** (cc-wiki adds oh_anw_unwrap to the route-a candidate now; it owns the bridge). cc-t3's probe
keeps the +0xc0 read (probe-only).

## Technical item ② — NWeb size = SurfaceView actual w/h, Resize on surfaceChanged
The A0 probe hardcoded 720×720. The formal WebView must size NWeb to the SurfaceView's real pixels:
- `NWebCreateInfo::GetWidth/GetHeight` = the SurfaceView's width×height at create time (not 720). The window-19 content
  rect was 1200×1794; the WebView/SurfaceView actual size is the value to use.
- On `SurfaceHolder.Callback.surfaceChanged(holder, format, w, h)`, call `nweb->Resize(w, h)` so rotation/relayout
  reflow the page. (A0's surfaceChanged was a no-op.)
- cc-wiki's provider should thread the SurfaceView dimensions (getWidth/getHeight, and surfaceChanged's w,h) to CreateNWeb
  + Resize. The probe already hands (x,y,w,h) over JNI; A1 just consumes w,h for sizing instead of discarding them.

## Division of work
- cc-t3 (this lane): this plan; the A1 test APK (real WebView); the window script (overlay/rollback/gate, extending
  run_a0.sh); run the window + read screenshots.
- cc-wiki: the route-a WebView artifacts (oh-adapter-runtime.jar candidate with org.westlake.webview.* + OhNWebProviderFix;
  shim + worker .so); fix SurfaceFromJava's ANW1 unwrap (item ①) and NWeb sizing (item ②) in those artifacts; provide SHAs.

## Status
Plan only — awaiting cc-wiki's artifacts + SHAs before building the window script and APK. The jar-overlay static
precondition is confirmed (non-BCP). Board run is a future window (declare + 2-min + lock, A0_EXPECT_FP=821de739cf81).
