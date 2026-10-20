# One desktop tap to Toutiao, without the development host controls

Previously the host page exposed its Westlake title and keyboard input while Android started. On 5cd, the exact same-signature HAP update now removes those controls and a normal desktop icon tap automatically reaches the real Toutiao feed after a reboot. The retained T31 video runtime was not replaced.

The signed package changed only `ets/pages/Index.abc`; the other eight HAP members, original certificate chain and profile remain identical. Source, exact original-compiler replay, successful build/signing logs and the reproduction recipe are in [the source/build package](../2026-10-20-toutiao-launcher-page/README.md). Candidate `b18978b8…` replaces `df385638…`, via `bm install -r -p`, with no uninstall or data-clear operation.

[Results](results.json) bind the actual new boot, host/parent/child identities, WID29 and the physical/private runtime fingerprints. The bundle identity, token and five data-directory identities were preserved. This does not claim every mutable app-data byte was compared. [Actual screenshot facts](facts.txt) preserve unknown process-survival counters rather than inventing them.

[Early background](early-background.jpeg) has no development title/input; [first sampled feed](first-feed.jpeg) shows real content. [Video frame A](video-a.jpeg) and [frame B](video-b.jpeg) visibly progress within the selected clip. User-confirmed manual audible playback from T31 remains the audio evidence; no new hearing confirmation was requested. The app was returned to [the feed](final-feed.jpeg), power restored to10000/10000, debug parameter absence checked, and the exact holder released.

The actual [retain decision](retain-decision.json) was signed at516.190 seconds and [close](closed.json) at516.600 seconds. [Peer closure](peer-closure.json) independently checks the recorded references. The original T31 seal remains historical and unchanged; this entry records the new HAP and boot.

Cold start still has an empty-background wait. The early screenshots and later feed are discrete samples, not exact first-frame timing; this change does not claim faster startup. It also does not fix random exits or establish every video/codec.

The first readiness poll mistakenly compared a parameter response without trimming its trailing whitespace; the failed receipt is preserved. A corrected read confirmed the same new boot READY, without another reboot. A system Back key left the video showing; tapping the observed in-app back button returned to feed. These operational failures are not hidden.

Exact original and candidate HAPs, original compilation/signing logs, all eight actual screenshots and command receipts are retained in the persistent archive indexed by `archive.json`. The final operation helper is [window_ops.py](window_ops.py); its readiness whitespace fix and small UI actions were applied during the observed window. Never reuse a closed context. Future changes need a fresh identity/lock and an exact-HAP rollback plan. No device access is needed to build the source package.

Source and this evidence are local mainline records; remote Git publication is not claimed.
