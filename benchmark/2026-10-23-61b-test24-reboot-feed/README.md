# T61: reboot first-use works; content operation does not pass

The initial 30-second WiFi observation was **connection pending**, not a drop. Subsequent read-only samples observed delayed association by 90 seconds. Starting from the first connected sample at 11:05:10 CST, additional samples at +108 and +180 seconds retained IPv4, RUNNING and a route. The original admission stop is preserved; the later phase used a fresh lock.

Phase B ran 11:08:35–11:12:49. One normal software reboot changed boot `f8406e45` to `85985a79-28f4-44b7-a8f2-75e11fd673ba`. System readiness was observed at uptime 39 seconds, and network availability at about 45 seconds, with no manual network reconnection or bootstrap/start command. One ordinary desktop-icon tap showed a blank screen at 30 seconds and a populated Toutiao feed at 120 seconds.

**Content operation failed in this boot.** Tapping an article was followed by gray screens and the child process exiting. No article body or successful return was captured. The cause was not investigated under the user's exclusion of random-crash work. This is not a full interaction seal, even though T59 had shown another article body and return in the preceding boot.

The outer independently viewed the four phase-B images and read both power-restoration receipts (30000ms / 10000ms). `outer-review.json` distinguishes accepted observations from the failed operation. Search-hint text does not prove fresh online data; content may be cached. Physical power cycling, physical human touch and all-115 current APK coverage remain unverified.

The original `results.json` includes phase-A fields at top level; its nested `phase_B` is the authoritative later boot and outcome. Settings screenshots and full raw command receipts remain in the persistent private root recorded in `outer-review.json`. No runtime or HAP was changed.
