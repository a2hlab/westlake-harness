# Signal inventory

A stderr Fatal signal banner does not prove the app main process died. Classify the emitting thread/process and preserve missing backtraces. All saved #38 runs are listed, including rounds added after the outer review’s original 13.

| Run | stderr signal / thread | PC / LR mapping | Separate OH faultlog |
|---|---|---|---|
| cold-a1 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['7631', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| cold-a2 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['15358', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| cold-a4 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['13890', 'work_thread'] | pc=/system/lib/ld-musl-aarch64.so.1+0x96f1c; lr=/data/local/tmp/asx/lib/arm64-v8a/libnpth.so+0x13854 | ['11694', 'RenderThread', '0000000003e026f0', '/data/local/tmp/asx/webview-t-lib/libwebviewchromium.so'] Signal:SIGSEGV(SEGV_MAPERR)@000000000000000000  |
| cold-a5 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['25047', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| cold-a6 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['3165', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| cold-a7 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['9807', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| cpu-consent-2 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['23246', 'work_thread'] | pc=/system/lib/ld-musl-aarch64.so.1+0x96f1c; lr=unknown | not captured |
| cpu-detail-1 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['26689', 'work_thread'] | pc=/system/lib/ld-musl-aarch64.so.1+0x96f1c; lr=/data/local/tmp/asx/lib/arm64-v8a/libnpth.so+0x13854 | not captured |
| idle-a1 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['26626', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| timeline-1 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['12022', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| timeline-2 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['17790', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| trace-1 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['28460', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| visibility-1 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['10930', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| warm-b1 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['20793', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| warm-b10 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['14561', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| warm-b2 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['26939', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| warm-b3 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['31980', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| warm-b4 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['18581', 'work_thread'] | pc=unknown; lr=unknown | not captured |
| warm-b8 | Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) / ['29752', 'work_thread'] | pc=unknown; lr=unknown | not captured |

For cold-a4, the faultlog’s mappings resolve the SIGABRT banner’s PC to musl and LR to libnpth.so+0x13854. The preserved disassembly shows the preceding instruction calls syscall(240, getpid(), gettid(), signal, siginfo): this is signal re-delivery by the crash handler, **not proof that libnpth caused the original fault**. Registers x20/x21 both contain the work_thread ID (13890), distinct from the app PID 10823; this is evidence of a separate process context. The main app continues logging afterward. Other runs without same-run mappings are not assigned an invented cause or DSO.

The cold-a4 RenderThread SIGSEGV at NULL in libwebviewchromium.so+0x3e026f0 is an independently captured app-process fault. It must not be merged into the work_thread SIGABRT group. No new ICU cause is asserted from a signal banner alone.

Additional startup failures excluded from article timing: warm-b9 has an ART fatal No pending exception expected, with a pending NullPointerException invoking IWebViewUpdateService.waitForAndGetProvider() during CookieManager/WebView provider initialization (child.stderr). warm-b11 exits before the test; its saved tail includes WebView native loading but no captured fault stack, so the exit cause is unknown. These are not assigned to the work_thread SIGABRT or RenderThread groups.
