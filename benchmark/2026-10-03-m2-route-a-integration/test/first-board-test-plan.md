# M2 route-a — first on-board test plan (run after cc-t3's A0/surface validation window)

Screenshot is ground truth (AGENTS 判定); numbers from facts.txt. Do NOT run before the surface conclusion is
confirmed on board; if it changes, adjust NativeNWebBackend.SurfaceFromJava + OhNWebSurfaceHost first.

## Stage 1 — slot test APK (localise any wrong vtable slot)
APK: one full-screen android.view.WebView, AndroidManifest like the A0 probe (single Activity). The 10
runtime-unverified NativeNWebBackend methods (a0probe never called these NWeb virtuals; see
benchmark/2026-10-03-m2-route-a-native/evidence/slot-verification-table.txt) are driven in this order, each bracketed
by a log line so a wrong slot crashes exactly at the call:

  1. nativeLoadUrl(handle, "https://en.wikipedia.org/wiki/OpenHarmony", null)      -> NWeb::Load
  2. nativeSetDomStorageEnabled(handle, true)                                      -> GetPreference + PutDomStorageEnabled
  3. nativeExecuteJavaScript(handle, "document.title", 1)                          -> NWeb::ExecuteJavaScript
  4. nativeReload(handle)                                                          -> NWeb::Reload
  5. nativeStopLoading(handle)                                                     -> NWeb::Stop
  6. nativeCanGoBack(handle)                                                       -> NWeb::IsNavigatebackwardAllowed
  7. nativeGoBack(handle)                                                          -> NWeb::NavigateBack
  8. nativeLoadData(handle, "<h1>hi</h1>", "text/html", "utf-8")                   -> NWeb::LoadWithData
  9. nativePostUrl(handle, "https://httpbin.org/post", <bytes>)                    -> NWeb::PostUrl
 10. nativeOnPause(handle)                                                         -> NWeb::OnPause
Each wrapped by the Java side logging `[M2-SLOTTEST] <n> <method> enter` and `... return`.
PASS (hardcoded): all 10 print enter+return; no DfxSignalHandler signo(11); worker logs `[NWEB] ...` for each;
RESULT PASS. A SIGSEGV between an `enter` and its `return` = that method's vtable slot is wrong -> fix the slot.

## Stage 2 — Wikipedia article (the real M2 win)
Same APK (or the m2-webview-surface Wikipedia harness): load en.wikipedia.org/wiki/OpenHarmony (or the local
pagelib+template the surface scan assumes). Let it settle to t20.
PASS (hardcoded): the t20 snapshot_display screenshot shows the ARTICLE BODY in the WebView region -- the heading
"OpenHarmony" and at least one paragraph of body text, rendered (not blank, not the chromium-missing error page, not a
white/black rectangle). onPageFinished in hilog + process alive are necessary, NOT sufficient -- the screenshot decides.
Record facts.txt (alive t5/t20, screenshots_captured) verbatim in the ACK.

## Stage 3 — predicted-light corpus subset
Only after Stage 1+2 pass on one board. Run the 8 PRIMARY-WebView keys (predicted-light.csv, verdict=predicted-lit),
judge each by its t20 screenshot against predicted-light.csv's expected_t20. Then the 6 cv2 roadmap keys cross-check
with cc-t3's m2-webview-roadmap.

## Boundary
Board whitelist only; one on-board task at a time per board (AGENTS 板子纪律). No deploy of M2 outside the test
generation; this is a bring-up test, not a stage-A run.
