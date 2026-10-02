# Toutiao on the U10.1 + T8 + U11i base: wall 0 (install) and the walls after wall 2, predicted before the window

Written 2026-10-02 before any toutiao result on this base existed (window 1 r1 was refused by the environment
before any app ran; cx-t0 12:54 "no candidate app data"). The one later fact folded in is the r2 5ea install
failure (outer, 2026-10-02): it happens before the app runs, so it is wall 0, not a runtime result.
Rows: `predictions.csv`. Evidence lines: `evidence/u10-toutiao-hilog-excerpts.txt`.

## What was wrong first

- **The window put the toutiao probe on a board that has never installed toutiao.** Every successful BMS install of
  toutiao (U6, U7, r16, r17a/b, U9 signed, U10) was on **61b**. The r2 plan moved the probe to 5ea. 5ea/5cd run
  `libinstalls.z.so` **2c9a5294**, 61b runs **51e1b525**, and the U10.1 bundle's own approved identity
  (`benchmark/2026-10-02-u10-1-bundle/expected-{5ea34a45,5cd1e3dd,61b06572}.txt`) pins exactly that split, so the
  boards were never in one unified state for the install chain.
- **The earlier native prediction only checked DT_NEEDED** (`2026-10-01-toutiao-on-unified/native-closure-prediction`:
  "bootstrap resolves"). Library presence is not symbol presence: U10 shows three app libraries failing to relocate
  on bionic-only symbols.
- **Stub classes were checked by class, not by member.** T8's gate (`deployed_class_diff.py`) checks that classes
  are not dropped. `android.net.NetworkInfo` exists in the stubs jar but has 7 methods, and toutiao's network stack
  calls methods it lacks.

## Wall 0: install fails on 5ea/5cd, not caused by the candidate

| run | board | libinstalls | result | installd log at libcvt.so |
|---|---|---|---|---|
| U9 signed, U10 | 61b | 51e1b525 | `install bundle successfully.` | `operator():3278 accepted reviewed APK payload exception libcvt.so` (extractor at `:3355`) |
| U10.1+T8 window 1 r2 | 5ea | 2c9a5294 (baseline = candidate) | `code:9568260 install internal error` | `operator():3222 APK native extraction failed: CRC/ELF/owner/mode verification failed` (extractor at `:3320`), then `ExtractFiles(APK_NATIVE_SO) failed abi=arm64-v8a ec=8519936` |

Extraction runs alphabetically. It succeeds up to `libcjtfccsm.so`; the next entry in toutiao's 137 arm64 libraries
is `libcvt.so`, the one library 61b accepts only through its reviewed-payload exception (1 exception line in the U9
61b log). 2c9a5294 is the libinstalls the `2026-10-01-libinstalls-align/plan-draft.md` already documents as
failing at `installd_operator:3222` (fd-seal). DIGEST E.7 recorded the same `ec=8519936` for toutiao on 2026-09-28.

`provision_toutiao.sh` is no comparison point: it `bm install`s only the host HAP and untars the APK and its native
libraries into the Westlake runtime directory, so it never runs the BMS native-extraction check.

**Verdict:** wall 0 is a pre-existing per-board install-chain difference exposed by moving the probe. It is not a
U10.1/T8/U11i regression. Run the toutiao probe on 61b, or land the libinstalls alignment (51e1b525 on 5ea/5cd;
daytime, foundation restart) before probing toutiao there.

## Walls after wall 2, most likely first

Source: the U10 61b toutiao run (runtime 519148f0f41a; the last base where toutiao installed and ran) plus static
reads of APK a1112a0c. Walls 1 and 2 are covered on the new base: libstdc++ by U10.1 policy 0718f01e, the conscrypt
`SSLParametersImpl` by T8 stubs 2f365a75.

1. **Not finished by t20 (high).** In U10 the MainActivity transaction is queued at t+2s, but at t+12.9s the
   ActivityThread is still inside `Application.attach → ArticleApplication.attachBaseContext`. The U10 t20 shot
   is a white window. One measured cost: Mira's `PluginPackageManager.getInstance` retries 3×200 ms under a class
   lock when its in-process provider `com.ss.android.article.news.pm.PPMP` is unreachable. U10 logs six failures
   exactly 0.6 s apart on six threads, including the main thread. U11i publishes app providers only after
   `handleBindApplication` returns, so `attachBaseContext` and `Application.onCreate` still pay this.
2. **android.net stub members (high on background threads; fatal only on the main thread).**
   `stub_member_gap.py` finds 122 members toutiao references on stub classes that the stubs do not define
   (121 missing). Of 352 call sites, 302 have no local handler that catches an `Error`. T8's and U9's stubs have
   the identical 122 gaps. Known answer: U10's CronetInit thread died on `NetworkInfo.getSubtype()`. TTNet's
   Cronet layer also needs `getDetailedState`, `Network.getNetworkHandle`,
   `ConnectivityManager.registerDefaultNetworkCallback` and `TrafficStats.tagSocket`/`getThreadStatsTag`, all
   missing and all unguarded.
3. **Bionic-only symbols in app native libraries (verified on U10; not covered).** The U10 hilog shows
   `libttcrypto.so s=__errno` (×19), `libsscronet.so s=__cmsg_nxthdr` (×4) and
   `libmetasec_ml.so s=__system_property_read` (×4).
   - musl exports none of the three. Compat 015aa3a6 exports only `__system_property_read`.
   - Even so, app libraries do not resolve compat symbols: on U10.1, fennec's `libmozglue.so` still fails
     `__gnu_strerror_r`, which compat exports.
   - Inference, not proven: neither compat nor musl carries version definitions, so the cause is lookup scope,
     not version matching.
   - Effect: TTNet's Cronet native is unavailable (requests can only take the OkHttp fallback, which is where
     wall 2 sat), and the metasec SDK does not load.
4. **OkHttp after T8 (medium-low).** Toutiao's `Android10Platform` needs only the class to load, then uses
   `SSLSockets` (FZ-008) and `SSLContext("TLSv1.2")` (registered by `[B8-TLS]`). A per-request failure would show
   as an `IOException("Android internal error")` from ALPN setup on the Westlake socket. That is not fatal.
5. **Render (low for the first screen).** libandroid lacks `ANativeWindow_lock`/`unlockAndPost`, used by
   libanimax and libttmplayer. This was deferred to the next libandroid round.

## If toutiao is still not lit, read in this order

1. `install.txt`: `code:9568260` together with `APK native extraction failed` in install-hilog → wall 0 (board
   libinstalls), stop there.
2. `No platform found on Android` must occur 0 times. If it occurs, T8 did not take: check that the board's
   `adapter-mainline-stubs.jar` is 2f365a75.
3. ActivityThread-tid lines up to t20: `[B43-BIND] ... returned OK` / `performLaunchActivity` / first frame, and
   the `plugin_exception_monitor` count. If bind is still running at t20, it is timing: take t60 before naming a wall.
4. `NoSuchMethodError` with `adapter-mainline-stubs.jar`: a background thread is tolerated by B8-UEH, the
   ActivityThread tid is fatal.
5. `MUSL-LDSO relocating failed` lines (dso + `s=`) for walls 3 and 5.

## Rules this sets

- A probe board must match the app's install chain. Until libinstalls is aligned, toutiao (libcvt.so) runs on 61b.
- Native closure predictions go to the symbol level (undefined symbols vs what the namespace can really resolve),
  not only DT_NEEDED.
- Stub BCP classes are checked member by member against the app (`stub_member_gap.py`). Class-level diffs pass
  while `NetworkInfo` has 7 of AOSP's methods.

## Files

- `stub_member_gap.py`: APK member references vs stub JAR members, with local Error-handler cover per call site
  (D8 compiles `catch (Throwable)` to catch-all; a handler that rethrows its exception counts as finally).
- `test_stub_member_gap.py`: lookup rules plus the U10 known answer (5 tests; the APK tests skip off this machine).
- `stub-member-gap-t8.{csv,txt}`: the scan against T8 stubs 2f365a75.
- `predictions.csv`: one row per wall with evidence, confidence, coverage on the new base, and the first log to read.
- `evidence/u10-toutiao-hilog-excerpts.txt`: the cited hilog lines with line numbers, plus the U10.1 fennec line.
