# #48 warm refuse-list deployment: ACK(blocked), R2=partially

Single warm instance, preserved consent, no guardian, board61b06572 only. The new shim did not establish180s stability or readable articles: parent reports child16843 exited(1), last alive sample61.025s, first dead65.121s. A genuine feed with news titles appeared in `during-60.jpeg`, but the article attempt at(380,390) was rejected by the original-PID liveness check before any uinput was sent. No article screenshot or NewDetail lifecycle was obtained.

## Deployment

Source `~/a2hlab/tmp/warmrefuse48-out/libwebview_bionic_shim.so`, westlake98c0945. Deployed SHA06375dc1aaa924bc79622c2deedf4c2e80815ab5e3e8305d515d3cb6869c38df. Old85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a copied to `/data/local/tmp/operator45-crashes/warm48-original/libwebview_bionic_shim.so.<old-sha>` before replacement. File mode/label preserved; post-deploy and pre-spawn hashes verified. No native rebuild.

Remaining stable baseline, metasec1021a058, npth8b8d559c, bridge d4fae8e5, recorder ART78e34445 and runffb324e4 preserved. Anonymous JIT, no#50/AOT. Only shim changed. Shared stop marker retained. Observation target240s satisfies the latest >=180s instruction; one-shot kill timer248s, never restarts. Actual process exited before the target. Hard HDC timeout unchanged.

## Failure evidence to claude-3

* Refusal log: `libhotfix-opt.so`; the process repeatedly reports prior initialization failures for `com.bytedance.hotfix.runtime.load.EnsureInitialized` and `com.bytedance.platform.godzilla.sysopt.ThrowEarlierClassFailureHook`.
* `[UNCAUGHT] thread='platform-handler' java.lang.UnsatisfiedLinkError: dlopen failed`, stack through `System.loadLibrary` -> `com.bytedance.platform.godzilla.sysopt.MinFreeHeapOptNative.<clinit>` -> `X.3Fa.run` -> `PlatformHandlerThread$NoQuitHandlerThread.run`.
* Main throws `ExceptionInInitializerError` in `ScreenShotInitDelayTask.run`; cause NPE reading `Looper.mQueue` from null in `Handler.<init>`, via `X.4bt.<init>` / `X.4bs.<init>` / `X.4bs.<clinit>`. Then `launchActivityThread RETURNED ... _exit(1)`, confirmed by parent reap.
* These are concrete load/thread/init failures under the expanded candidate. Exact library ownership of MinFreeHeapOptNative and causal connection to the later null Looper still need static confirmation; do not guess turbo/tunnel/jato/reparo based on names. Feed content itself was not absent.
* No SIG11 banner or native snapshot in this short run, no observed npth-worker native crash. This does not prove180s absence. A work_thread SIGABRT banner is retained separately from the parent's final exit(1).

## Evidence limitations and gates

`maps60.maps` is empty: capture raced process death; HDC command success/`maps60=true` means attempted transfer, not a valid maps snapshot. No claim that all refused libraries were absent from mappings. The original metadata is retained unchanged; strict-review.json explicitly records maps_bytes0.

The upstream assert_heap_hook_refuse.sh printed PASS with a no-maps warning and missed the unhandled ULE because the exception line has no library name (class name only on following stack lines). Its documented survival/screenshot pairing is mandatory: our strict review is FAIL due to exit(1), <180s, empty maps and no body. Do not use its PASS as the combined acceptance result.

All evidence operations, component hashes, feed image, complete stderr/parent log and exact main failure stack retained. Cleanup executed after death; app/appspawn PID lists empty, MemAvailable5940708KiB. New shim remains installed with the app and guardian stopped. No further trial or unrequested narrowing of the17-library list was performed.
