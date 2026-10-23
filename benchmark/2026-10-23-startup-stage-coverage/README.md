# T95: prefix reaches WebView native loading; timing remains partial

The131072-byte/1583-line prefix has SHA `4eb388bf…` and begins with the exact21154-byte T93 prefix. This is application log content, not a failed transport. Outer performed collection; this lane only read the saved file.

**New ordinary stages.** `head.stdout:506` reports application-ready cache republish. Line1172 reports WebView support hold released before onCreate;1411 reports the feature published. Lines1419–1421 report `BEFORE scheduleTransaction`, `AFTER scheduleTransaction OK`, and MainActivity launch posted. These untimed checkpoints do not prove onCreate completion or a first rendered frame.

**Explicit timing.** PID6291/TID6311 method verification logs report288.259ms at17:22:03 (345),226.991ms at17:22:04 (432), and137.893ms at17:22:05 (435). These are individual reported durations, not a full startup interval or source-bound optimization. The last explicit wall-time anchor is17:22:07 at1183; later lines have no bound wall time. TOUCH21 `now` stays a raw counter with unknown unit/domain, preserving T94.

**Visible failures, without causal promotion.** Name resolution reports EAI_NONAME at370 and ENOENT at377. `sendto ... ENETUNREACH` appears at793/806 and later repetitions. `libsysoptimizer.so` reports missing `_ZNSt6__ndk18ios_baseD2Ev` at507/687. Plugin provider lookups report unknown authority at748/905. Later WebView scanning reports missing `webview-t.dm` at1561 and `classes3.dex` at1566/1572/1578. These messages neither establish fatal failure in this successful run nor identify its latency cause. No network addresses or user data are exported.

**Exact cutoff.** Line1582 begins native loading of `libwebviewchromium.so`;1583 is a partial SOURCE-NATIVE-LOADER line, cut in the library name at the128KiB boundary, without a final newline. Native-load completion and first-render completion remain **unknown**. The prefix cannot establish coverage through T92's first `content::Start` marker: no clock-bound end marker connects them.

No optimization candidate is justified. `results.json` retains safe excerpts, original line numbers, explicit time fields and raw counters. Reproduce without temporary files: `python3 benchmark/2026-10-23-startup-stage-coverage/extract_stages.py --output benchmark/2026-10-23-startup-stage-coverage/results.json`. No device, source, deployment, Git or `/tmp` operation was performed.
