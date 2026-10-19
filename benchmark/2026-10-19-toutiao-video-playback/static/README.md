# Toutiao video t1 — static evidence and first-fatal prediction (2026-10-19)

**Status: `needs_observation`. No route is confirmed; no selected change; t2 stays closed.** All five media routes are `unknown`. One load-time first-fatal candidate (P1) is ranked first, with two read-only requests and one short window that confirm or refute it.

## What was wrong before

- The 2026-09-28 report attributed the frozen cover to `ReliableSurface` stubs and `SetMetadata -5`. `ReliableSurface` wraps HWUI's main window. That directory keeps no raw log, and no evidence binds a video producer to those buffers. That run's runtime identity was not recorded. It is not treated as current (`historical_is_current: false`, H0).
- Earlier work also inferred that "decoders are present, so decode is fine". Library presence does not show that the player library **loads**. This round checked whether it can load.

## Current identity (outer read, parent only)

61b, boot `6944c37e`, OH 6.1.0.31. Parent 11444 runs the **RouteB / asx v1 bundle**, not the unified U-series runtime. The APK is `a1112a0c` (byte-identical to every local copy). The other pins are run.sh `d3518cef`, libandroid `c9969638`, libhwui `a11c9154` and media_jni `f3943601`. The bridge (`d4fae8e5`) and runtime (`8ab6742d`) are historical RouteB pins (p7), not fresh reads. No child was alive, so the actual video consumer is unknown. Inputs: [61b-media-identity.txt](evidence/61b-media-identity.txt), [run.sh excerpt](evidence/61b-run.sh.excerpt.txt). The full maps stay in persistent storage; their SHA256 is in prediction.json.

## Five routes

| Route | Consumer (APK) | Provider in RouteB default ns | State |
|---|---|---|---|
| network | TTVideoEngine MDL `libavmdl*`; libttmplayer/libmffmpeg/libvcn | `libavmdl*` and `libttopenssl` are absent (4 LOAD-FAILs each in a RouteB feed log); not in APK `lib/` | unknown |
| decode | libttmplayer `b427614d`: ffmpeg/ByteVC1/2 software; Java `AJMediaCodec` via JNI | software path self-contained; MediaCodec natives in bridge d4fae8e5 (fail-loud) | unknown |
| video_surface | `ANativeWindow_fromSurface` → EGL, or `ANativeWindow_lock/unlockAndPost` (CPU) | fromSurface = **libhwui a11c9154** (emits `[WESTLAKE-ANWFS]`); lock/unlockAndPost = LD_PRELOAD `libwebview_bionic_shim` **stub** ("CPU rendering path not implemented"); root libandroid exports no `ANativeWindow_*` | unknown |
| audio | OpenSL ES incl. `SL_IID_ANDROIDSIMPLEBUFFERQUEUE`, `SL_IID_ANDROIDCONFIGURATION`; JNI `android/media/AudioTrack` | **no known provider** for the two Android IIDs (RouteB libs, APK libs, OH NDK OpenSLES ABI) | unknown |
| lifecycle | TTVideoEngine pause/resume/release | n/a until the player loads | unknown |

## P1 — ranked first-fatal candidate

`libttmplayer.so` is `BIND_NOW`. Both IIDs are non-weak `GLOBAL OBJECT UND` and use `R_AARCH64_GLOB_DAT`. We resolved its full undefined set against every known provider in the run.sh lookup scope: preloads, NEEDED closure, RouteB libs and OH sysroot ABI. **Exactly two symbols remain unresolved: `SL_IID_ANDROIDCONFIGURATION` and `SL_IID_ANDROIDSIMPLEBUFFERQUEUE`** ([reproduce.sh](evidence/reproduce.sh), [stdout](evidence/reproduce.stdout.txt)). The prediction is that the first player init logs:

```
[SOURCE-NATIVE-LOAD-FAIL] path=.../libttmplayer.so namespace=0 error=Error relocating .../libttmplayer.so: SL_IID_ANDROID…: symbol not found
```

The log format and musl wording are taken from a real RouteB child log ([excerpt](evidence/routeb-child6243-loader-excerpt.txt), for example `Error relocating …libsysoptimizer.so: … symbol not found`). That log is feed-only and contains no libttmplayer line.

**Prior art (copy first):** the original Westlake Toutiao route already solved this load. In `westlake/scripts/toutiao/run_tt.sh` (last touched at a9fd5ad7) and `native/build.sh` (0d8e4f43), libttmplayer was loaded through `nsprobe/libwestlake_player_anchor.so`. That anchor's ordered DT_NEEDED places `libopensles_android_compat.so` (source `cf45ad43`, which defines exactly these two IIDs and maps SIMPLEBUFFERQUEUE to OH's `SL_IID_BUFFERQUEUE`) before `libttmplayer.so`. RouteB dropped it: no anchor env, no `nsprobe/`, libttmplayer outside NATIVE_TARGETS. RouteB libart `78e34445` also supports only one `ANCHOR` (no `NEXT_ANCHOR`). See [prior-art-player-route.txt](evidence/prior-art-player-route.txt). Westlake never evidenced playback beyond this load, so the prior route only addresses P1.

**RQ1 (outer, 61b parent mount ns):** the first `libOpenSLES.so` is `/system/lib64/libOpenSLES.so` `05d8ac90`. It exports `SL_IID_OH_BUFFERQUEUE` but **neither Android IID** ([outer-rq1](evidence/outer-rq1.txt), [exports](evidence/outer-61b-OpenSLES-exports.txt)). The static precondition therefore holds on the device. P1 is still **unknown, not confirmed**: no load attempt has been observed. It would be refuted by another global provider, by a different first libttmplayer error, or by the engine never trying libttmplayer.

## Conditional next walls

- **P2:** IID symbols alone do not produce audio. OH OpenSLES PLAY `RegisterCallback` returns FEATURE_UNSUPPORTED (DIGEST 2026-10-02).
- **P3:** On the CPU render path, the lock stub drops frames silently. On the GLES path, OH libEGL's acceptance of the hwui-prewrapped window is unverified (DIGEST 733 precedent).

## Minimal observation ([readonly-requests.json](readonly-requests.json))

- **RQ1** (pure read): done; see above. libEGL is `platformsdk/libEGL.so` `96bc1421`; libGLESv2 is `ndk/libGLESv2.so` `5b4f734b`.
- **RQ2** (pure read): the first attempt used a wrong path (`asx/private-tmp`; [outer-rq2](evidence/outer-rq2.txt)). That attempt is **not** evidence that playback logs are absent. Redo it at `/data/service/el1/public/appspawnx/adapter_child_*.stderr`; this path comes from the 2026-10-12 RouteB capture (`[AppSpawnX] [CHILD] opened …/adapter_child_6243.stderr`).
- **RQ3** (outer window ≤10 min, 5cd/5ea, not 61b): one video tap, a 30 s window, and two screenshots. Use baseline/delta for stderr and hilog; **never** run `hilog -r`. Exact criteria are in the JSON.

## Parallel inputs

- **p7 inventory:** consumed, including the RouteB pins.
- **pB APK lane:** consumed. One correction: libttmplayer does reference `android/media/AudioTrack` and `AJMediaCodec` via JNI strings, so "NO AudioTrack" applies to NDK imports only. The pB REA receipt is pending and will be consumed when it lands.

## Rule set

Rank by **load-time closure first**. Before blaming a render or buffer layer, prove that the consumer DSO loads in the namespace the runtime actually uses. Compute the undefined-symbol closure against the deployed providers of that exact bundle; RouteB ≠ unified runtime.

Files: [prediction.json](prediction.json), [source-search.json](source-search.json), [readonly-requests.json](readonly-requests.json), [static-receipt.json](static-receipt.json), [results.json](results.json). No device command, build, runtime change or push was made by this lane.

## Update — REA method evidence (outer MCP, 17:27)

We consumed four REA records from the main tree `.octos/` (hashes and evidence IDs are in [rea-analysis.json](rea-analysis.json)): the package summary, `TTPlayerLibLoader.loadLibrary()`, `loadPlayerlibrary(String)` and `TTPlayerRef.setSurface(Surface)`.

- **The load is lazy, and a failure is silent.** `TTPlayer.<clinit>` calls `loadLibrary()`. The load order is `VCBaseKitLoader` → `ttcrypto`/`ttboringssl` → `mffmpeg` → `ttmplayer`; the beta/pgo variants depend on server config. Every Throwable is caught, `IsErrored` is set, and nothing is rethrown. `loadPlayerlibrary` returns `false` without an app log. **A failed libttmplayer load therefore produces neither a crash nor an app log line.** The RouteB `[SOURCE-NATIVE-LOAD-FAIL]` trace is the only observable. This fits the historical silent frozen cover but does not prove it.
- `setSurface` → native `setVideoSurface` → `ANativeWindow_fromSurface`. A new `[WESTLAKE-ANWFS]` line is the surface-handoff marker, but only after a successful load.
- New **P1b** (unknown): `libvcbasekit` is an android-native-namespace target in RouteB, while libttmplayer (NEEDED `libvcbasekit.so`) loads in namespace 0. Observe which namespace each load reports.

**Minimal observation point** ([readonly-requests.json](readonly-requests.json) `observation_point`):

- **OP0** (zero UI, allowed now, including on 61b): grep the current `adapter_child_*.stderr` for the player load chain.
- **OP1**: a single video-card tap, only once a real feed is on screen. A network-exception page does not qualify. Use baseline/delta, two screenshots, and decision rows A–D.

`libttmplayerbeta`/`libttmplayerpgo` "No such file" lines are expected noise. Optional next REA reads: `TTPlayerLibLoader.loadLibs(ArrayList,boolean)` and `ITTPlayerRef.create`. t2 stays closed.
