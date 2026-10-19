# t11-window-final-ready — first-fatal addendum

Confirmed first fatal: `[TT-EXECUTOR] REFUSE FOREGROUND_HOST_NOT_READY`, before real-spawn/host_spawn. Both wrapper checks precede exec; which check refused remains unknown. Not a Toutiao random exit. Later WID29 field8=-1 and lockscreen corroborate foreground loss without identifying the exact failing call.

Outer plan omitted the verified awake override. No setting was changed in this window; 10-second interference is outer-reported. A future temporary override must restore the captured prior value and retain the strict foreground gate.

Original packet/facts/failures/archive-01 unchanged. Combined landing uses `landing-v2-paths.txt`, pins `manifest-v2.json`/`SHA256SUMS-v2`. Archive-02: 1666 members, 607729 bytes, SHA 7202fe5d8de0488659ba6bbba52feead8f66fcf7496a82a6433e1bab0ac11f9a; local verified, remote pending. Use only archive-02 remote argv for outer upload.
