# Three/four patch stability follow-up

Only board5ea34a45; ability38-v7/out-sp20 base; no rebuild, no system writes,
no other boards. R2: partially, experiments in progress.

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
Another preserved fresh profile is used for `four46-fresh1`. Results pending.
