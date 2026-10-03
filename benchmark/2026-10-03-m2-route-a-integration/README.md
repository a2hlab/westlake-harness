# M2 route-a integration draft — wiring, native deploy, static gates, first-board test, predicted-light

#90, offline, design-only. Pulls the four M2 route-a pieces together into a deployable plan **for a future U version**
(NOT U14/U15/U16): the Java provider (`benchmark/2026-10-03-m2-route-a-java`), the native backend
(`benchmark/2026-10-03-m2-route-a-native`, worker `8475da6f` / shim `ba3e0561`), the surface decision
(`benchmark/2026-10-03-m2-route-a-surface`, Option A = SurfaceView in the WebView). Nothing here is built or deployed;
it is the integration contract + gates + test plan the owner runs when M2 is scheduled.

## ① Wiring — JAR packaging + provider switch + fallback
**JAR.** All `org.westlake.webview.*` ship in **`oh-adapter-runtime.jar`** (the runtime JAR family that already carries
`adapter.activity.*` — `WebViewProviderFix`, `J10eWebView`, `B7BindFixes`), **not** `adapter-mainline-stubs.jar` (that
is the mainline-API stub jar). Split by compile classpath, same jar:
- framework-classpath (implement the deployed framework.jar's @hide `WebViewProvider`/`WebViewFactoryProvider`/
  `WebView.PrivateAccess`): `OhNWebProvider`, `OhNWebFactoryProvider`, `OhNWebSettings`.
- public-API: `OhNWebController`, `NWebBackend`, `NativeNWebBackend`, `MockNWebBackend`, `NWebCallbackSink`,
  `OhNWebProviderFix`, and the surface classes `NWebSurfaceLifecycle` (public-API) + `OhNWebSurfaceHost`
  (framework-classpath: `android.view.SurfaceView`).

**Provider switch (after `J10eWebView.install()`).** AOSP `WebViewFactory.getProvider()` returns the cached
`sProviderInstance` if set, else throws `UnsupportedOperationException` on route-A (no Chromium). The bind-fix sequence
already seeds it twice (no-op). Add one call last, gated on the engine:
```
WebViewProviderFix.install();                       // J8  type-zero stub
J10eWebView.install();                               // J10e/J10g enriched no-op
org.westlake.webview.OhNWebProviderFix.install();    // M2: re-seed sProviderInstance = OhNWebFactoryProvider (reflection)
```
`OhNWebProviderFix.install()` returns **false** (leaving J10e's no-op in place — getProvider still won't throw) when
the NWeb engine is not ready, so every non-WebView app and any board without the engine is unchanged.

**Engine-not-ready fallback (layered).** (a) native: the shim only loads the worker into `nweb_ns_legacy` when present;
(b) engine: `NativeNWebBackend.create()` returns handle 0 if `NWebHelper::InitAndRun` failed → `OhNWebProviderFix`
reports not-ready → J10e no-op stays (today's behaviour: WebView renders nothing but does not crash the activity);
(c) surface: `NWebSurfaceLifecycle` creates NWeb only in `surfaceCreated`, so a WebView that never lays out never calls
native. The readiness boolean is cc-t3's (A0) to supply; the Java side only consumes it.

## ② Native deploy — paths, loader, namespace
- **Deploy paths** (both next to the runtime libs): `/system/android/lib64/libwl_nweb_backend_shim.so` (shim) and
  `/system/android/lib64/libwl_nweb_backend.so` (worker).
- **Who System.loads.** The shim is added to the runtime's fixed-path native-lib hook **`B7BindFixes.loadLib`** — the
  A0-documented load point that already `System.load`s `/system/android/lib64/{libwestlake_jni_gapfill,
  liboh_tls_boundary,libwestlake_html_compat}.so` in every app's bind (A0 README §"existing load hooks"). Add
  `libwl_nweb_backend_shim.so` to that list (ideally gated — see below). `JNI_OnLoad` fires there (it is a
  `System.load`, in the app ns, with the JavaVM), which is the whole reason for the shim/worker split.
- **Namespace (no two copies).** shim → `JNI_OnLoad` dlns get-or-creates **`nweb_ns_legacy`** (PERMITIED_TARGET2,
  dynlink.c:4189; worker-dir lib_path; inherit `default`) and `dlopen_ns` the worker there; **`nweb_ns` is left to
  NWebHelper** (DIGEST 761). `open_site_scan` on the two .so (`benchmark/2026-10-03-m2-route-a-native/evidence/
  open-sites.txt`): the worker's only opens are **NOLOAD** probes of `liboh_adapter_bridge`/`liboh_android_runtime`
  (reuse, no new copy); NEEDED resolve from the inherited `default` ns — **no library appears twice**. The arkweb
  engine loads in OH's own `nweb_ns` at `NWebHelper::Init`.
- **Eager-vs-lazy (recommended gate).** Loading the arkweb closure in every process is heavy. Gate the shim load on
  "the app hosts a WebView" (e.g. only call the shim's register from `OhNWebProviderFix.install()`, which only runs
  when a WebView provider is actually needed), or defer the worker `dlopen_ns` to the first
  `NativeNWebBackend.create()`. The eager A0 load is fine for the bring-up window.

## ③ Static gates (the owner runs these before any deploy; this draft only states them)
- **`deployed_class_diff.py <candidate oh-adapter-runtime.jar> --deployed <the jar the board runs>`**: the rebuilt jar
  must **only ADD** the `org.westlake.webview.*` classes (pass each via `--allow-add Lorg/westlake/webview/…;`), with
  **zero drop / zero superclass-or-interface reshape** of any deployed class. Use `--deployed` (the exact board jar),
  never `--name` with a glob (T8 lesson: two copies in the generation). Expected: N adds, 0 drops, 0 reshapes.
- **`check_frozen.py`**: the integration adds classes + two new .so; it must touch **no** `knowledge/frozen/frozen.json`
  entry. The frozen installer FZ-001 (libapk_installer/libbms), the frozen runtime shims, etc. are untouched — M2 is
  additive (new classes, new libs, one seeder call, one loadLib entry). Expected: clean.
- **New native → `knowledge/gates/new-native-admissions.json` candidate rows** (suggestions only — this draft does NOT
  edit `knowledge/gates/`): `gates/new-native-admissions-candidate.json` holds the two proposed admission rows (shim +
  worker, with target path, sha256, the manifest sha of the gen they ship in, reason, evidence pointers). The outer
  reviews + admits them when M2 ships; until then they are candidates.

## ④ First on-board test plan (`test/first-board-test-plan.md`)
Gated on cc-t3's A0/surface validation window; before any corpus run:
1. **A0-style test APK** (one full-screen `android.view.WebView`, AndroidManifest like the A0 probe). Drive, in order,
   the **10 runtime-unverified** `NativeNWebBackend` methods (the vtable slots a0probe never exercised — see
   `benchmark/2026-10-03-m2-route-a-native/evidence/slot-verification-table.txt`): `nativeLoadUrl`, `nativeLoadData`,
   `nativePostUrl`, `nativeExecuteJavaScript`, `nativeReload`, `nativeStopLoading`, `nativeCanGoBack`, `nativeGoBack`,
   `nativeOnPause`, `nativeSetDomStorageEnabled`. Each logs `[M2-SLOTTEST] <method> enter/return` — a wrong vtable slot
   crashes at that line and localises immediately. **Pass:** all 10 log enter+return, no SIGSEGV, `RESULT PASS`.
2. **Wikipedia article.** Point the test WebView at `https://en.wikipedia.org/wiki/OpenHarmony` (or the local
   pagelib+template the m2-webview-surface scan assumes). **Pass criterion (hardcoded):** the t20 `snapshot_display`
   screenshot shows the **article body text** (heading "OpenHarmony" + at least one paragraph) rendered in the WebView
   region — not blank, not the error page. Screenshot is ground truth (AGENTS 判定); process-alive / `OnPageLoadEnd` in
   hilog are necessary-not-sufficient.
3. Only after 1+2 pass on one board: run the ⑤ predicted-light corpus subset.

## ⑤ Predicted-light keys (`predicted-light.csv`, from m2-webview-surface)
Of the 83 WebView-rendering keys (28 already lit via their native screen, 32 unmeasured co-* commercial), the not-lit
ones split by whether the WebView is the PRIMARY screen:
- **Predicted to light (PRIMARY WebView, direct M2 win) — 8:** `cv2-ca-vaults-randomlydie`, `cv2-com-degeder-yam`,
  `cv2-com-paultirk-yatoo`, `cv2-com-stoutner-privacybrowser-standard`, `cv2-dev-obfusk-jiten-webview`,
  `cv2-timur-webrtc-check`, `fd-mobile`, `fd-tutanota`. These are full-screen/hybrid WebView UIs whose t20 is the
  WebView — NWeb supplying the renderer should light them. (The 6 cv2 keys = cc-t3's m2-webview-roadmap set;
  jiten also carries its own M5 chooseServer dialog, DIGEST 743.)
- **Not predicted to light by M2 alone (SECONDARY WebView) — 15:** the WebView is behind a native/Flutter/RN/Unity wall
  (`burgerking`, `fd-AppManager`, `fd-fluffychat`, `fd-im-vector-app`, `fd-immich`, `fd-kitchenowl`, `fd-libre`,
  `fd-meet`, `fd-plus`, `fd-saber`, `localsend`, `mcdonalds`, `subwaysurfers`, `termux`, `toutiao`) — M2 only helps a
  sub-screen; their t20 is gated by the primary wall (e.g. the Flutter keys by the Impeller wall). M2 is a prerequisite,
  not the lighter.

**Predicted move: +8 lit** (the 8 PRIMARY-WebView keys), with confidence highest for the 6 cv2 roadmap keys. The
secondary keys gain a working WebView sub-surface but stay gated by their primary wall.

## Files
- `gates/new-native-admissions-candidate.json` — the 2 proposed admission rows (not applied).
- `test/first-board-test-plan.md` — the A0-style + Wikipedia plan with hardcoded criteria.
- `predicted-light.csv` — the per-key predicted-light table. `evidence/m2-webview-not-lit-targets.txt` — the source split.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline design draft; no board, no deploy, no push; does **not** edit `knowledge/gates/` or `knowledge/frozen/` (the
admission rows are candidates). For a future U version, not U14/U15/U16. The on-board confirmation (and the readiness
boolean, the exact `B7BindFixes.loadLib` edit, and the `oh-adapter-runtime.jar` rebuild) are the owner's when M2 is
scheduled; this is the contract they execute against.
