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
  into runtime/profile-backups/maps46-fresh2. The same child11045 is used for the article session below.

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

## Confirmed article session

All article opens use `uinput -T -d x y -u x y`; the navigation-only `c` fallback
above is excluded. Video articles contain embedded video posters with play
controls and readable body text. This validates video-containing article
survival, not successful video decoding/playback.

| Video ordinal | Evidence label | Article | Physical input uptime | Detail RESUMED uptime | Last alive after input |
|---|---|---|---:|---:|---:|
| 1 | article1 | CCTV 国际社会高度关注中美两国元首会晤 | 89342.28 | 89355.425 | 126.67s |
| 2 | article3 | CCTV 主播说联播：习主席讲述的这个故事，感动中美人民 | 90138.17 | 90140.748 | 125.84s |
| 3 | article4 | CCTV 美国各界人士：习近平主席此次访问是“历史性时刻” | 90345.51 | 90348.041 | 126.46s |
| 4 | article5 | CCTV 习近平和彭丽媛同美国总统特朗普夫妇茶叙 | 90546.46 | 90549.753 | 126.53s |
| 5 | article7 | CCTV Go“兔”月球——中秋寻嫦娥 | 90944.42 | 90946.982 | 127.00s |

Additional nonvideo control `article6`, Xinhua《习近平圆满结束对美国的国事访问》,
renders all three body paragraphs. Its comments panel reports a network error;
this is preserved in the screenshot and is not described as wholly functional.

This workload has not reached the original 65530-map limit. Completion can
establish bounded session survival with the raised limit, but cannot establish
that the sysctl change caused survival or fixed the previously crashing workload.
The prior crash article, People’s Daily《经纬线·习主席在美国讲述的中国故事》,
has not been repeated in this session. RSS fluctuation is not proof of a permanent
plateau or repair of renderer allocation growth.

## Bounded results and evidence

Five distinct video-containing articles completed in child11045 without a
restart, with readable body/video posters in every `article{1,3,4,5,7}-after125.jpeg`.
Durations in the table are measured from physical input, not RESUMED; these
are lower bounds from the last `/proc` alive sample, not crash times. The first
article required13.145s to RESUMED, so its +125 image alone establishes only
about113s after RESUMED. It remained open until the physical author-profile
touch at89486.94 (131.515s after RESUMED). The other four timed windows each
exceed120s after their respective RESUMED markers. This does not pass the older
#38 <2s opening SLA (subsequent delays2.578/2.531/3.293/2.562s).

203 resource samples span uptime89031.54–91091.19 (2059.65s,34.33min):
- maps3158 →21792; sampled maximum21792. Neither65530 nor1048576 was reached.
- VmRSS436.71MiB →1237.43MiB; sampled peak1468.98MiB (1.435GiB).
- VmSwap stayed0. Last120s endpoint RSS slope−45.40MiB/min, but maps continued
  to rise. The complete bounded session ran; a long-term plateau is not proven.
- Per-video sampled max maps:10467/14634/16525/18065/21779;
  peak RSS MiB:1019.06/1203.14/1296.48/1288.86/1327.93.

All five article windows: UnsatisfiedLinkError0, FATAL0, fatal-signal banners0,
getOwnCodecInfo No implementation0. Whole captured child log: GLES translation1,
GrGLInterface creation failed0, InitializeGL failure0, Fatal signal5=0, FATAL0.
Whole-log caveats: one earlier work_thread tid13287 SIGABRT banner and one
libmetasec_ml errno13 UnsatisfiedLinkError before the first article; the same
child survived both. These are not suppressed from the evidence or described
as “no errors globally.” npth-dumper-thr tid13028 was S in all35 samples per
video window, CPU delta0ticks. No RenderThread SIGSEGV was observed in this
session. Crypto and BoringSSL still have two offset-zero executable images;
TicketGuard routing/root-cause closure remains unproven.

Nonvideo controls article2 andarticle6 survived126.82s and126.63s from input.
Article2 rendered images and paragraphs and responded to a physical upward
swipe; article6 rendered text but comments showed a network error. Physical
feed refresh replaced headline sets. Final physical back at91099.82 returned
to the feed (`final-feed.jpeg`), child remained alive at final maps capture.

[Mapping and RSS curve](evidence/maps46-fresh2/maps-curve.png),
[CSV](evidence/maps46-fresh2/maps-curve.csv),
[per-window resource data](evidence/maps46-fresh2/resource-summary.json),
[log classification](evidence/maps46-fresh2/window-classification.json),
[lifecycle markers](evidence/maps46-fresh2/lifecycle-errors.txt),
[fifth article at125s](evidence/maps46-fresh2/article7-after125.jpeg).
PNG/SVG are derived from exported CSV by `scripts/plot_maps46.py`; the manifest
covers exported source evidence, while plots are separately tracked artifacts.

## Handoff

Experiment completed; R2=partially for mitigation causality. Bounded five-page
survival, four patch hashes and sysctl configuration are verified. The old
ceiling was not exercised; no A/B on the identical crashing article was run.
Before-session failures above prevent claiming universal startup stability.
No additional crypto closure or binary patch was mixed into this run.

Sampler stopped cleanly via VM `maps46-fresh2/stop-maps`; app left on feed,
child11045, parent11018, stage
`/data/local/tmp/a2hlab-app-f9c50f561b75433b97d54cc945f9aed8`.
Runtime `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-f9c50f561b75433b97d54cc945f9aed8`,
log under it `private-tmp/adapter_child_11045.stderr`.
The current max_map_count1048576 is nonpersistent; no system partition was
written. Original65530 is preserved in maps46-config/sysctl-before.txt.
Only board5ea34a45 was touched. Commits only; no push.
