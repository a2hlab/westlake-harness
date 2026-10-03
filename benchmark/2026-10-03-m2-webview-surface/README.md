# M2 WebView surface scan — which `android.webkit.*` methods route-a (WebViewProvider→NWeb) must implement

#90, offline, static, no board. M2 route-a backs `android.webkit.WebView` with OpenHarmony's NWeb
(cc-t3's `benchmark/2026-10-03-m2-webview-roadmap`). To scope it, this statically scans every corpus APK's
DEX for the `android.webkit.*` methods it **calls** and the `WebViewClient`/`WebChromeClient` callbacks it
**overrides**, orders Wikipedia's surface by the "open an article" path, and gives route-a a
"implement N methods → cover X keys" table. (`surface.csv` = per-key; `evidence/wikipedia-surface.txt` =
the ordered article path; `evidence/method-frequency.txt` + `evidence/coverage.txt` = the N→X tables;
`evidence/not-lit-targets.txt` = the M2 targets; `recipe/scan_webview_surface.py` = the reproducible scan.)

## Method — a pure-Python DEX method-ref parser (no apktool/baksmali)
For each APK (and `.xapk` inner base APK) I parse the DEX `method_ids` table directly: every method_id is a
`(class, name)` pair, and a method_id whose class is `Landroid/webkit/…;` is a **call into the WebView
framework** (loadUrl, evaluateJavascript, `WebSettings.setX`, `CookieManager.*`, `setWebViewClient`, …). The
curated WebView-callback names appearing as method_ids are the app's **overrides** (shouldInterceptRequest,
onPageFinished, …). This reads call/override references exactly, fast enough for all 200 APKs.

**Correctness guard:** `android.webkit.MimeTypeMap.*` and the static `WebView.findAddress`/`findAll` are
**utilities that never instantiate a WebView** — 76 keys call only those. Counting them would inflate
"uses WebView" to 161. The real signal is *renders a WebView* (constructs one / installs a client / loads
content), which gives **83** keys. The utilities are kept in a separate CSV column, not the surface.

## Headline counts
- **200** corpus APKs scanned (100 `corpus100.json` + 100 `corpus-v2`).
- **83** render a WebView; **76** call only `android.webkit` utilities (not a WebView); the rest none.
- U13 status of the 83: **28 lit · 23 not-lit · 32 unmeasured** (measured universe = u13-reference 166, 122 lit).

## Wikipedia — the article page IS a WebView (ordered by "open an article")
Wikipedia calls **59** `android.webkit` methods (57 render + 2 utility) and overrides **10** callbacks. Its
launcher/onboarding is native (so it is *lit* at t20 via M1), **but reading an article renders in a WebView** —
exactly what M2 is for. Ordered by the article-open path (full in `evidence/wikipedia-surface.txt`):
1. **Construct + configure:** `WebView.<init>`, `getSettings`, 10 `WebSettings` setters
   (`setJavaScriptEnabled`, `setAllowUniversalAccessFromFileURLs`, `setDefaultFontSize`, `setGeolocationEnabled`, …), `setLayerType`.
2. **Install clients:** `setWebViewClient` (+`WebViewClient.<init>`), `setWebChromeClient` (+`WebChromeClient.<init>`).
3. **JS bridge:** `addJavascriptInterface`, `removeJavascriptInterface` (the page↔app bridge for article JS).
4. **Load the article:** `loadUrl`, `loadDataWithBaseURL` (local HTML template + base URL for assets).
5. **During-load callbacks:** `shouldInterceptRequest` (serve bundled CSS/JS/pagelib offline),
   `shouldOverrideUrlLoading` (link handling), `onPageStarted`/`onPageFinished`, `onLoadResource`,
   `onReceivedHttpError`, `onProgressChanged`; with `WebResourceRequest.getUrl/getMethod/getRequestHeaders`
   and `WebResourceResponse.<init>/getStatusCode/getReasonPhrase`.
6. **Script the page:** `evaluateJavascript` (theme, lazy sections, lead image), `onConsoleMessage`,
   `onJsConfirm`/`JsResult`, `onCreateWindow`.
7. **Cookies/MIME:** `CookieManager.getInstance/setCookie`, `MimeTypeMap.*`.
8. **Interaction:** `onTouchEvent`/`onScrollChanged`/`getContentHeight`, `getHitTestResult` (link long-press),
   `findAllAsync`/`findNext`/`setFindListener`/`clearMatches` (in-article search), `canGoBack`/`goBack`, `onDraw`.

So for Wikipedia, first paint needs steps 1-5 (construct→configure→clients→load→`shouldInterceptRequest`);
`shouldInterceptRequest` + `loadDataWithBaseURL` are load-bearing because Wikipedia serves its page template
and pagelib assets locally.

## M2 route-a coverage table (`evidence/coverage.txt`, `evidence/method-frequency.txt`)
**Top-10 `android.webkit` render methods** (each needed by this many of the 83 WebView keys — lit/not-lit/unmeasured):

| # | method | #keys | lit | not-lit | unmeas |
|---|---|---|---|---|---|
| 1 | `WebViewClient.<init>` (app subclass) | 77 | 22 | 23 | 32 |
| 2 | `WebView.setWebViewClient` | 76 | 21 | 23 | 32 |
| 3 | `WebView.<init>` | 74 | 21 | 21 | 32 |
| 4 | `WebView.getSettings` | 74 | 19 | 23 | 32 |
| 5 | `WebView.loadUrl` | 72 | 17 | 23 | 32 |
| 6 | `WebSettings.setJavaScriptEnabled` | 70 | 17 | 21 | 32 |
| 7 | `WebResourceRequest.getUrl` | 65 | 12 | 21 | 32 |
| 8 | `WebSettings.setDomStorageEnabled` | 62 | 9 | 21 | 32 |
| 9 | `WebChromeClient.<init>` (app subclass) | 60 | 9 | 19 | 32 |
| 10 | `WebView.setWebChromeClient` | 59 | 8 | 19 | 32 |

- **Render-core = 12 methods → first paint for 74/83.** The 12 (above + `loadDataWithBaseURL`, `evaluateJavascript`,
  `addJavascriptInterface`) are the construct→settings→client→load→JS core; 74/83 keys construct a WebView AND
  call a load method. Implementing the core **plus each app's declared `WebViewClient`/`WebChromeClient`
  callbacks** (NWeb must drive them — `shouldInterceptRequest`, `onPageFinished`, `shouldOverrideUrlLoading`,
  `onProgressChanged`, …) gives first paint for essentially all 83.
- **Feature-complete is a long tail:** full coverage (every webkit method a key calls) reaches only
  **4/83 at top-24, 10/83 at top-80, 83/83 at ~617** — because apps each add rare features (find-in-page,
  file chooser, HTTP-auth, zoom, print, download, geolocation). So M2 should ship the render-core first
  (first paint for all), then fill per-app callbacks; "full coverage" is the wrong target.

## Which keys does M2 actually light? (`evidence/not-lit-targets.txt`)
Of the **23 not-lit** WebView keys, M2 directly lights the ones whose **primary screen is the WebView**:
- **8 PRIMARY-WebView (direct M2 wins):** the 6 cv2 web keys (`randomlydie`, `yam`, `yatoo`, `webrtc-check`,
  `jiten-webview`, `privacybrowser`) = cc-t3's roadmap set, **plus** `fd-tutanota` and `fd-mobile` (both
  `webview-hybrid`).
- **15 SECONDARY-WebView:** blocked by a native/upstream wall (Flutter EGL / Realm `_ctype_` / ICU / RN) —
  `fd-im-vector-app`, `fd-saber`, `fd-immich`, `fd-fluffychat`, `fd-kitchenowl`, `fd-libre`, `fd-meet`,
  `localsend`, `mcdonalds`, `burgerking`, `subwaysurfers`, `toutiao`, `fd-AppManager`, `fd-plus`, `termux`.
  Their t20 is gated by that wall; M2 only helps a sub-screen, so M2 alone will not light them.
- The **28 lit** WebView keys render their **native** main screen (WebView is a secondary tab/OAuth/help page) —
  **except that `wikipedia` is lit on its native onboarding but its article page needs M2** (the dispatch's point):
  M2 is what makes article *reading* work, even though the key already counts "lit".

## This round's rule
Scope a framework-backing effort by the **method-reference surface**, and separate the real embedders from
utility callers: 76 keys touch `android.webkit` only via `MimeTypeMap`/`findAddress` and need no WebView at
all. The actionable target is the **render-core (12 methods) + per-app callbacks**, not full API coverage —
the surface has a long per-app tail, so first paint (core) is cheap while feature-completeness is not. And a
key being "lit" doesn't mean it needs no WebView: Wikipedia is lit on its native shell but its content screen
is a WebView.

## Files
- `surface.csv` — per key: stack, package, u13_status, renders_webview, n methods, callbacks overridden,
  the full `android.webkit` render-method list, androidx.webkit, and util-only calls.
- `evidence/wikipedia-surface.txt` — Wikipedia's 59 methods ordered by the open-an-article path.
- `evidence/method-frequency.txt` — every render method ranked by #keys (lit/not-lit/unmeasured split).
- `evidence/coverage.txt` — full-surface (strict) vs render-core (first-paint) coverage, with the next tier.
- `evidence/not-lit-targets.txt` — the 23 not-lit WebView keys split PRIMARY (M2 wins) vs SECONDARY (upstream-blocked).
- `recipe/scan_webview_surface.py` — the reproducible DEX method-ref scanner (`WORKSPACES=… python3 …`).
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; static only; no board; no push. The surface is **call/override references** (what the app invokes),
not a trace — a referenced method may be on a cold path; conversely reflection-invoked webkit calls would be
missed (none seen; apps call WebView directly). "renders a WebView" is a static predicate (construct/load/
client), not a runtime render. lit/not-lit is the u13-reference signing (122 lit). The PRIMARY/SECONDARY
split uses the app stack + cc-t3's confirmed web-wrapper set; a SECONDARY key's own wall is named from the
first-fatal clusters, not re-measured here. Sources read read-only: the APKs (`westlake-inputs/{corpus100.json,
corpus-v2,apks}`), the u13-reference lit lists (`westlake-harness`), cc-t3's roadmap
(`benchmark/2026-10-03-m2-webview-roadmap`).
