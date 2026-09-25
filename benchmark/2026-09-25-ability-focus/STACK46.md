# Three/four patch stability follow-up

Only board5ea34a45; ability38-v7/out-sp20 base; no rebuild, no system writes,
no other boards. R2: partially. Three physical opens attempted with all four patches; only two
reached 120 seconds. ACK(blocked) for the full stability/zero-error requirement.

## Deployment

Existing WebView shim ecc7b12c and MediaCodec bridge d4fae8e5 remain unchanged.
npth original SHA256 `10641147b4c2a551e48162fa07f08776642147abc443d014756b909b6236076f`
was backed up on board at `/data/local/tmp/ability38-npth46-original.<full-sha>.so`
and VM `ability38/mc46-verification/original-npth.so` before replacing
runtime `lib/arm64-v8a/libnpth.so` with
`8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af`.
Binary comparison finds exactly four changed bytes at0x17930–0x17933:
`fd7bbaa9` becomes `c0035fd6` (RET). Deployment and comparison JSON are preserved.

The later tt-target instruction is a separate configuration. The supplied
`apply_tt_targets.py` changed only WESTLAKE_ANDROID_NATIVE_TARGETS in a backed-up
run.sh, adding libttcrypto, libttboringssl and libdelta; liblynxsecurity was
already present. Applying the script twice produced identical bytes. Exact
run.sh hashes, backup path and helper hash are in `tt-deployment.json`.
This is experimental routing, not proof that all DT_NEEDED loads use Bionic ABI.

## Trials before tt targets

`triple46-1` child21409 and `triple46-2` child22818 died with parent signal11
before any Activity ENTRY; no article observations, origins unknown. To get a
meaningful application test after repeated warm-start failures, existing
app-data/data/webview-t-data directories were **renamed into a backup**, not
deleted. `triple46-fresh1/fresh-profile.json` records the reversible backup path.
The framework, libraries and launch options did not change.

Fresh child24066 reached consent, which was physically accepted at uptime86002.84.
The old second CCTV article was no longer in the feed. Its fourth item was
another CCTV article, “视频｜国际社会高度关注中美两国元首会晤”, containing text and
embedded videos. Physical touch(380,516) at86062.13 entered NewDetailActivity
record2, RESUMED86075.438 (+13.308s). The last in-window live sample is+127.01s.
At+15s it was still loading; later screenshots show the real text and video
posters. A physical play tap at86155.36 (+93.23s) produced a spinner and native
player failures, but the article remained readable at the final screenshot.

npth-dumper-thr tid26085 stayed S in35 samples spanning126.76s, CPU ticks delta0;
NPTH-AnrMonitor likewise0. npth-worker used13 ticks, AnrInfoPol5, profiler3.
This establishes no dumper CPU spin in the observed window, not a sampled-PC
trace at0x179c0. Raw all-thread stats and derived CPU summary are retained.

No FATAL/SIGTRAP occurred. **UnsatisfiedLinkError was not zero**: metasec mapping
errno13, and after the extra play tap, TTPlayer._setSupprotSampleRates and
MediaPlayer.native_init were missing. The video-initialization fallback marker
was0, so this article does not prove Chromium exercised mc46's fallback.
A work_thread SIGABRT banner reports tid26541, distinct from child24066; the
article process continued through127s (consistent with the known fork-child
failure, not an app death). Do not claim video playback works.

## Four-patch trials

The three-patch survivor was intentionally stopped to apply the newly requested
tt targets. Four-patch warm child30201 (`four46-1`) died signal11 before Activity
ENTRY. Its attempted environ read occurred after death and returned no targets;
that is unavailable evidence, not proof the live environment omitted them.
Fresh child31619 (`four46-fresh1`) reached MainActivity/consent, then parent
reported signal11 before an article was opened; no matching primary faultlog
establishes the crashing thread/DSO. Its work_thread SIGABRT tid2712 must not be
relabeled as the main process's signal11. No TicketGuardNetw@0x28 evidence.

A second preserved fresh profile (`four46-fresh2`, child3716, parent3695) reached
the feed. Live `strings /proc/3716/environ` proves all four requested targets.
run.sh SHA256 changed from `65530f5cec5249c71ff03399a4fb78a5f3b9a264fd621be9bac6e5aace6e075c`
to `e166b07cbad67122bccee331c38f581c655333b2cd319f4703c94e6c2735c0a9`.
The original script remains backed up; no rebuild was needed.

First physical feed tap(380,548), uptime86673.32, opened the same CCTV article;
record2 RESUMED86701.800 (+28.480s), observed alive through+127.84s. Final
screenshot shows body text and embedded video posters. Dumper tid5773 stayed
S in35 samples over127.48s, CPU ticks delta0. No PC sampling was performed.
Global UnsatisfiedLinkError count was2: metasec mapping errno13 and Fresco's
libstatic-webp.so missing an __ndk1 shared_weak_count symbol. FATAL/SIGTRAP and
getOwnCodecInfo missing-implementation counts were0; video fallback marker0.
This proves bounded article survival, not successful video playback or that
mc46's decoder fallback was exercised.

After returning, feed refresh replaced the CCTV entry. A Chinese uinput text
query was rejected by uinput; My opened a login page, which was dismissed
without entering credentials. Subsequent valid opens use visible feed entries.

At uptime87220.21 the live process still had TWO offset-zero executable
mappings each for libttcrypto and libttboringssl; libsscronet had ONE.
The experimental four-name target set therefore did not eliminate duplicate
crypto images. No TicketGuard crash in a bounded window proves neither HMAC
binding correctness nor long-term immunity. The newer 15-library closure on
the board is a separate candidate and has not been silently mixed into this run.
## Four-patch final observations

All three are physical `uinput -T -d x y -u x y` feed taps in child3716, not i/c.
They are sequential opens in one process, not three independent cold starts.

| Open | Article | Input uptime | Detail record / RESUMED uptime | Last alive after tap | Result |
|---|---|---:|---|---:|---|
| video1 | CCTV, 国际社会高度关注中美两国元首会晤 | 86673.32 | 2 / 86701.800 | 127.84s | Body and embedded-video posters readable |
| video2 | 人民日报, 经纬线·习主席在美国讲述的中国故事 | 87170.41 | 5 / 87172.772 | 127.22s | Body and embedded-video poster readable |
| video3 | Same 人民日报 article reopened | 87339.26 | 6 / 87341.537 | 96.99s | Readable at+90s; first absent+100.73s |

Third window ended in **SIGTRAP, Chrome_InProcRe tid6853**; parent confirms
child3716 killed by signal5. PC0x7de1d4fec8 maps to
`libwebviewchromium.so +0x37cfec8` using the earlier same-process map.
The fatal banner has no backtrace/fault message. Function and precise cause
remain unknown; this is neither evidence of the old RenderThread GL destructor
SIGSEGV nor of TicketGuardNetw SIGSEGV@0x28. Do not attribute it to MediaCodec:
there is no getOwnCodecInfo missing-implementation, no new ULE, no JNI FATAL,
and no video-initialization fallback marker in this window.

Final whole-process counts: GLES translation1, GrGLInterface failure0,
InitializeGL failure0, getOwnCodecInfo missing0, ULE2, FATAL text0, SIGTRAP1.
Second-window counts: ULE0/FATAL0/fatal banners0. Third-window counts:
ULE0/FATAL0/SIGTRAP1. Startup's separate work_thread SIGABRT remains recorded;
it did not terminate the main process at that point. No matching OH faultlog
was collected. `fatal-tail.txt`, `fatal-pc-mapping.json`, `parent.log`, and raw
window logs preserve the attribution, rather than relying on substring counts.

npth dumper tid5773: CPU tick delta0 in all three windows (35/35/27 samples),
all S states; last window spans96.70s. This is no observed CPU spin, not proof
of all future npth behavior. The two crypto libraries grow from one mapping
after consent to two at87220.21. Both timestamps are preserved, so the earlier
single mapping must not be used to claim the duplicate-load problem is fixed.

No automatic retry hides the failed third window. Three attempts are complete,
**2/3 >=120s**, global ULE==0 and no-SIGTRAP fail. Video playback is unverified,
and Chromium decoder fallback remains unexercised in the captured logs.
Patched files remain deployed; the failed candidate's owned residual processes
are cleaned after evidence collection. No other board or system partition changed.

Screenshots: [video1 +125](evidence/four46-fresh2/video1-after125.jpeg),
[video2 +125](evidence/four46-fresh2/video2-after125.jpeg),
[video3 +90 before exit](evidence/four46-fresh2/video3-after90.jpeg).
Raw timing/CPU: `observation-summary.json`; global/window classification:
`assertions.json`, `window-classification.json`.
