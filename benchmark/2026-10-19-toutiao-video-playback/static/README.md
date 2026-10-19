# Toutiao video t1 — static evidence and first-fatal prediction (2026-10-19)

**Status (Update 4): P1 CONFIRMED on 61b; selected change proposed for outer approval — see Update 4.** *(Original status: needs_observation; kept below for history.)* All five media routes are `unknown`. One load-time first-fatal candidate (P1) is ranked first, with two read-only requests and one short window that confirm or refute it.

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

**RQ1 (outer, 61b parent mount ns):** the first `libOpenSLES.so` is `/system/lib64/libOpenSLES.so` `05d8ac90`. It exports `SL_IID_OH_BUFFERQUEUE` but **neither Android IID** ([outer-rq1](evidence/outer-rq1.txt), [exports](evidence/outer-61b-OpenSLES-exports.txt)). The static precondition therefore holds on the device. P1 is still **unknown, not confirmed**: no load attempt has been observed. It would be refuted only by an exact load-result record for the libttmplayer object showing success, or by a different first libttmplayer error. An unobserved attempt leaves it unknown.

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

## Update 1 — REA method evidence (outer MCP, 17:27) — **SUPERSEDED in part by Update 3; do not cite the struck claims**

We consumed four REA records from the main tree `.octos/` (hashes and evidence IDs are in [rea-analysis.json](rea-analysis.json)): the package summary, `TTPlayerLibLoader.loadLibrary()`, `loadPlayerlibrary(String)` and `TTPlayerRef.setSurface(Surface)`.

- ~~**The load is lazy, and a failure is silent.**~~ *(superseded: silence is branch-conditional, see Update 3)* `TTPlayer.<clinit>` calls `loadLibrary()`. The load order is `VCBaseKitLoader` → `ttcrypto`/`ttboringssl` → `mffmpeg` → `ttmplayer`; the beta/pgo variants depend on server config. Every Throwable is caught, `IsErrored` is set, and nothing is rethrown. `loadPlayerlibrary` returns `false` without an app log. **A failed libttmplayer load therefore produces neither a crash nor an app log line.** The RouteB `[SOURCE-NATIVE-LOAD-FAIL]` trace is the only observable. This fits the historical silent frozen cover but does not prove it.
- ~~`setSurface` → native `setVideoSurface` → `ANativeWindow_fromSurface`. A new `[WESTLAKE-ANWFS]` line is the surface-handoff marker~~ *(superseded: consumer is a static-import inference; an unattributed ANWFS line is supporting evidence only)*
- New **P1b** (unknown): `libvcbasekit` is an android-native-namespace target in RouteB, while libttmplayer (NEEDED `libvcbasekit.so`) loads in namespace 0. Observe which namespace each load reports.

**Minimal observation point** ([readonly-requests.json](readonly-requests.json) `observation_point`):

- **OP0** (zero UI, allowed now, including on 61b): grep the current `adapter_child_*.stderr` for the player load chain.
- **OP1**: a single video-card tap, only once a real feed is on screen. A network-exception page does not qualify. Use baseline/delta, two screenshots, and decision rows A–D.

`libttmplayerbeta`/`libttmplayerpgo` "No such file" lines are expected noise. Optional next REA reads: `TTPlayerLibLoader.loadLibs(ArrayList,boolean)` and `ITTPlayerRef.create`. t2 stays closed.

## Update 2 — loadLibs / setVideoSurface and reconciliation with t4 (no device operation)

New REA records (main `.octos/`): `method-3` `TTPlayerLibLoader.loadLibs` (`1ebaf718…`, `ev_0fd7b0e4…`) and `method-4` `TTPlayer.setVideoSurface` (`2fd77ae4…`, `ev_213e4d2e…`). We also reconciled with the t4 assessment `westlake-harness-t4/benchmark/2026-10-19-toutiao-rea-methods/assessment.md` (`0c724fb5…`). Its input hashes and evidence IDs for package and method-0/1/2 are identical to ours.

**Corrections to Update 1**

- **What the loader returns:** `loadPlayerlibrary` ignores the boolean from `loadLibs` and returns `true` unless `loadLibs` throws. In per-library mode (cfg3), a failed load can therefore leave `IsErrored=false`. "Returns false on failure" was too strong.
- **Which loader runs:** `loadLibs` dispatches to a configurable `ILibraryLoader` or to `mDefaultLibLoader`. Only the configurable branch catches Throwable. The actual mechanism (`System.load`, `System.loadLibrary` or a custom linker) is **not established**. We withdraw the implicit `System.loadLibrary` assumption.
- **Surface handoff:** `setVideoSurface` calls native `_setVideoSurface` only when `mHandle != 0`; otherwise it returns `-1` silently. Naming `ANativeWindow_fromSurface`/libhwui as the runtime consumer is a static-import inference that REA does not show.

~~**Static conclusion:** every Java-level outcome of a failed player load is silent. `IsErrored` may stay false, `setVideoSurface` returns `-1`, and no crash occurs.~~ *(superseded by Update 3)* This agrees with t4: no MediaPlayer fallback is shown in these methods, and hotfix branches can override the static paths. In-app state cannot confirm or refute P1, which stays **needs_observation**.

**Minimal runtime observation (amended `observation_point`)** — three independent runtime-side signals, all read-only:

1. The RouteB ART loader trace (`SOURCE-NATIVE-LOAD(-FAIL)`), which covers `System.load`/`loadLibrary`.
2. ~~Child `/proc/<pid>/maps` … covers custom loaders~~ *(superseded: maps shows mappings only; see Update 3)*
3. `ASX_DIAG_THROWABLE` output for `UnsatisfiedLinkError` on `com.ss.ttm.player` natives.

~~OP1 adds decision **E**: … meaning a custom loader; P1 is refuted for that copy.~~ *(superseded by Update 3)* OP1 also adds decision **F**: an UnsatisfiedLinkError with no maps entry. OP1 still requires a real feed with video cards first; Wi-Fi/board choice is pending the user's clarification.

## Update 3 — independent review corrections (t4 `video-branch-review-ack.md` `87804615…`, cx-seal); no device operation

These statements replace any conflicting text in Updates 1–2. All stay **unknown**, and P1 stays **needs_observation**.

1. **Maps:** `/proc/<pid>/maps` proves only that a file was mapped at that instant. It shows neither which loader made the call nor which linker namespace (maps has no namespace field). It does not show relocation success, JNI registration, or which copy the player uses. A mapping without a trace line can also be an inherited/pre-existing mapping or a gap in trace coverage. **Maps never refutes P1.** We keep full maps lines (address, perms, offset, dev, inode, path), not basename counts.
2. **Silence is conditional:** the ordinary loader branches may absorb failures. If execution reaches `setVideoSurface` with a zero handle, it returns `-1`. These methods do not prove that a failed load implies `mHandle==0`. They do not rule out earlier or later native-call errors: the nonzero-handle call has no local catch, and `loadLibrary`'s hotfix path lies outside its inner catch. **Overall error/crash behavior and the actual caller are unproved.** t4 did not make the stronger claim; it was ours.
3. **Decision rows:** if no attempt appears in the trace, the result is "attempt not observed; player creation unknown". A LOAD marker plus an unattributed `[WESTLAKE-ANWFS]` line is supporting evidence only. Refuting P1 needs a documented successful load result for the exact libttmplayer object, plus attribution of the consumer.
4. `ILibraryLoader` alone is not evidence of a custom native linker.

`rea-analysis.json` F2/F3/F4/F7/F8 are edited in place with superseded markers. The `readonly-requests.json` decisions C/D/E/F are rewritten accordingly.

## Update 4 — P1 confirmed on the real board; selected change proposed (no device operation by this lane)

**Observed (outer raw capture, [binding](evidence/live-r1-tap1-binding.txt)):** board 61b, boot `8f7f12bf`, parent 5287, child 9290, run.sh `d3518cef`. One tap was made at (600,1090) on the real recommended feed. The stderr delta shows `SOURCE-NATIVE-LOAD` for libmffmpeg, which succeeded including its init array. It then shows libttmplayer:

```
[SOURCE-NATIVE-LOAD-FAIL] path=/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so namespace=0 error=Error relocating /data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so: SL_IID_ANDROIDSIMPLEBUFFERQUEUE: symbol not found
```

`TTPlayer` class init is then rejected: `UnsatisfiedLinkError … TTPlayer._setSupprotSampleRates`. The JNI was never registered because the DSO did not load. The t20 and t25 screenshots are byte-identical (`b866c6b3`). Child maps contain libmffmpeg, libvcbasekit, libttcrypto and libttboringssl, with no libttmplayer and no libOpenSLES. This is decision **A**, and P1 is confirmed. The visible error also falsifies the old "silent" wording, which Update 3 had already withdrawn.

**Selected change ([selected-change.json](selected-change.json)), single variable, rollbackable:**

| Item | Value |
|---|---|
| New file | `/data/local/tmp/asx/libopensles_android_compat.so`, built verbatim from `opensles_android_compat.c` `cf45ad43` (Westlake, the same blob already deployed in the original Toutiao player route) |
| Edit | `run.sh` line 33: append `:/data/local/tmp/asx/libopensles_android_compat.so` to `LD_PRELOAD` (`d3518cef` → `ea984942`; [diff](selected-change/run.sh.diff)) |
| Namespace | libttmplayer stays in namespace 0. Only the provider of the two IIDs is added to the global preload set, which is the same mechanism RouteB already uses for libwebview_bionic_shim |
| Build | `dockbuild.sh cc` with OHOS clang 15.0.4 `feef13a3`, the same compiler as the existing RouteB preload DSOs. Recipe: Westlake `build.sh` `0d8e4f43` lines 89–93. Sources are copied into [selected-change/](selected-change/) |
| Rollback | Restore run.sh `d3518cef` from backup, remove the DSO, restart through the original cfg path |

**Why preload rather than player_anchor:** RouteB libart has a single android-native `ANCHOR` and no `NEXT_ANCHOR`. Anchoring would move libttmplayer into another namespace. The preload gives the same "compat before player" ordering without a namespace change.

**Expected:** the libttmplayer load result moves past the IID relocation. The next first fatal is unknown (P2 audio callbacks, P3 surface, network/content). **This is not a playback claim.** The t2 contract now pins the two sources, the recipe and the offline gates (lint 100%, [t2-lint.txt](selected-change/t2-lint.txt)). The board window, pass criteria and rollback are in `selected-change.json`.
