# #46 max_map_count mitigation experiment

Only board5ea34a45, ability38-v7/out-sp20 base. Four patches retained byte-for-byte
(wv46 ecc7b12c, mc46 d4fae8e5, npth8b8d559c, four-name target run.sh e166b07c).
No rebuild or system-partition write. The requested nonpersistent sysctl was
changed from65530 to1048576 before launching; overcommit remained1. This tests
an environment mitigation, not a repair of renderer growth or crypto routing.

The sampler reads uptime, maps line count, VmRSS/VmSwap, meminfo, cgroup and
process stat every10s. Raw samples and CSV are preserved; no hiperf is used.
Article input/screenshot timestamps use the same board uptime clock.

Pre-session attempts (not article successes):
- maps46-warm1 child4722: main resumed, Handler(null Looper) NPE then exited(1); no article was opened.
  Highest sampled maps6209, RSS904728KiB. Warm profile preserved afterward.
- maps46-fresh1 child7595: consent physically accepted; before an article opened,
  SIGSEGV in ChromiumNet0 tid7815, faultlog stack top musl __libc_malloc_impl,
  then libsscronet frames. Highest sampled maps5339, RSS767528KiB. Not a
  Chrome_InProcRe SIGTRAP and nowhere near either VMA ceiling. The complete
  cppcrash report is retained; no inference about allocator root cause.
- maps46-fresh2: fresh retry with previous app-data/data/webview-t-data renamed
  into runtime/profile-backups/maps46-fresh2. Results pending.

The first timed touch in fresh2 (`video1`,380,548) hit during a feed layout
change. No detail Activity ENTRY followed; its screenshots stayed in the feed.
This is a missed article opening, not a successful video survival observation.

First confirmed video article: physical tap(380,510) at89342.28 opened CCTV
“视频｜国际社会高度关注中美两国元首会晤”, detail record2 RESUMED89355.425.
Last timed alive sample+126.67s, body and video posters visible.

A detour to its author profile returned a network-error view. The error view
covered the back button below y88; physical back taps and a keyboard/back
command did not leave it. A single direct navigation click `c 50 70` at89844.20
returned to the article. This is explicitly NOT physical input acceptance.
Article opens remain real uinput; process and resource sampler were not restarted.

Second detail was a non-video control: CRI《讲习所：祖国和亲人牵挂着每一位海外游子》.
Text/images rendered and a physical upward swipe moved to further paragraphs.
It is excluded from the >=5 video-article count. A physical pull-to-refresh
at90090.36 replaced the feed headline set and loaded new CCTV entries.
