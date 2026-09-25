# Toutiao on real Android: what normal looks like, and two OH problems read against it

On the OH board a tab tap during a networked first launch waits 11–17 s before the UI thread runs
it (#21). The app copies `libmetasec_ml.so` into `app_lib` and fails to load it (#23), feed
thumbnails stay grey, and every run logs a SIGABRT on a thread called `work_thread`. None of that
said what the same APK does where it is supposed to run. This run records that on a real Android
device, with the byte-identical APK, and reads the two OH problems offline against it
(board entry #26).

**Device:** `N100CU025C18D000128`, UNISOC `uis7885_2h10_native`, Android 16 (SDK 36) `userdebug`,
arm64, 1200×1920 at 320 dpi (the OH boards' resolution), WiFi with 0% loss to `www.toutiao.com`.
Toutiao 13.9.0 was already installed and `base.apk` hashes to `a1112a0c…7395`, the corpus APK, so it
was not reinstalled. The app's data was backed up before any `pm clear` and restored afterwards
(see [Data safety](#data-safety)).

Six runs: **F1–F3** are first launches (`pm clear`, consent, then four tab taps); **S1–S3** are
second launches on the data the preceding F run left. S1's taps landed on a login promo, so only its
launch phase counts.

## What it settles

- **Touch delivery is not slow on Android, even in a first launch.** From the event's timestamp to
  the moment the app's main thread starts `deliverInputEvent`: **2.3–71.6 ms** (median 4.1, n=15) in
  first launches, **2.6–6.8 ms** in second launches. This is the quantity Westlake measures as
  post→run, and there it is **11,016–16,730 ms** in a networked first launch (#21).
- **The app's own first-launch work never holds Android's main thread that long.** The longest
  main-thread slice is 0.96–2.0 s, during launch (`bindApplication` or the first activity
  transaction); once the feed is up the longest is 0.45 s and there are no slices of 500 ms or
  more. So an 11–17 s wait on OH is either
  work that takes far longer there, or work that Android does not do at all.
- **Tab → new content, when normal:** 0.36–0.90 s to switch the page. Content then arrives in
  2.6–3.3 s for a category fetched from the network for the first time (热点, 小视频). It takes
  about 1.1 s for 推荐, and 0.5–0.9 s for 小说. On a second launch 热点 takes 1.16 s from reused data.
- **`libmetasec_ml.so` loads once, from the install directory, and is never copied.** The load goes
  through `/data/app/…/lib/arm64/libmetasec_ml.so` in the app's classloader namespace
  (`nativeloader: … using class loader ns clns-9 …: ok`) in 6/6 runs. There is no `app_lib`
  directory, no copy of the library anywhere in the data directories, and `app_librarian/` holds
  only an empty version directory. The `app_lib` copy on OH (#23) is therefore the app's fallback
  after the first load failed. On Android that fallback never runs.
- **The large video thumbnails in the feed arrive as HEIC, and OH cannot load the HEIF decoder.**
  All four 960×540 covers in the cache are `ftypheic`, and they are the covers on screen
  ([`heic-feed-covers.jpg`](images/heic-feed-covers.jpg)). On OH, `libbdheif.so` fails in every run
  on `_ZNSt6__ndk119__shared_weak_countD2Ev`. That is not a missing NDK API; it is the C++ runtime.
  The fix is to load the decoder libraries in the Android-ABI namespace.
- **The `work_thread` SIGABRT does not kill the app.** The thread is Umeng's `HandlerThread`, and
  the abort follows Umeng's native `fork()` by 0.3–0.9 s in every run. The app pid keeps running,
  so the abort most likely happens in the forked child. That is a hypothesis; the next steps below
  can confirm it.

## Reference table

`results.json` → `reference`. Ranges are over valid taps. "Content" is the first frame after the
tap whose feed region has real items (see [Method](#method)).

| | first launch (F1–F3) | second launch (S1–S3) | OH / Westlake |
|---|---|---|---|
| cold start, `am start -W` TotalTime | 1828 / 1889 / 1924 ms | 3421 / 4007 / 4031 ms | — |
| event → main thread `deliverInputEvent` | 2.3–71.6 ms, median 4.1 (15 taps incl. consent) | 2.6–6.8 ms (8 taps) | post→run 11,016–16,730 ms networked first launch; 1 ms reused data + offline (#21) |
| tap → page switched | 362–899 ms | 368–705 ms | — |
| tap → content: 热点 | 2633 / 3132 / 3021 ms | 1163 / 1156 ms | — |
| tap → content: 小视频 | 2666 / 3313 / 2990 ms | 2749 / 2887 ms | — |
| tap → content: 推荐 (return) | 1097 / 1104 / 1099 ms | 1129 / 1104 ms | — |
| tap → content: 小说 / 热榜 | 小说 486 / 936 / 483 ms | 热榜 4010 / 3439 ms | — |
| `Choreographer: Skipped N frames`, launch | 30–39 (6 events) | 34–49 (8 events) | — |
| `Skipped N frames`, tap phase | 30, 35 | 33 | — |
| HWUI `Davey!` | 715 (launch), 711 (taps) | 731–954 ms (5, all in launch) | — |
| gfxinfo janky frames, launch / taps | 36–46% / 23–40% | 56–95% / 23–25% | — |
| longest main-thread slice, launch / taps | 964–1345 / 232–447 ms | 1691–2023 / 189–277 ms | — |
| `libmetasec_ml.so` mapped from | `/data/app/…/lib/arm64/` (6/6) | same | `/data/local/tmp/asx/lib/arm64-v8a/`, then `app_lib/` copy (#23) |
| `app_lib` directory / copies | none / 0 | none / 0 | created, `failed to map … errno=13` (#23) |
| image-cache formats (F1, 111 files) | HEIC 14, WebP 64, PNG 27, JPEG 3, GIF 3 | S3: HEIC 18, WebP 114, PNG 31, JPEG 5, GIF 3 | HEIF decoder fails to load |

This phone is itself janky: it is a low-end tablet, and a launch skips 30–49 frames at a time. The
reference is therefore an upper bound on what the app tolerates, not a smooth ideal. Second
launches start slower than first launches (3.4–4.0 s vs 1.8–1.9 s) because the SDKs gated behind
consent now initialise in `bindApplication`: 1.7–2.0 s, against 0.96–0.99 s in a first launch.

## Grey thumbnails

**Conclusion: the grey 16:9 video covers on OH are explained, and the fix is known.** Their bytes
are HEIC, and the only library that decodes them, `libbdheif.so`, cannot be loaded.

Why it cannot be loaded:
- It is loaded in namespace 0.
- The search order puts `/system/lib64` before the app's library directory, so `libc++_shared.so`
  resolves to OH's copy. Both copies end up mapped.
- OH's copy does not export the NDK's `std::__ndk1` C++ ABI. The OH SDK build exports 0 `__ndk1`
  symbols and uses `std::__n1`; the APK's copy exports 1760.

In sensor-online-3, 15 distinct app libraries fail the same way, among them `libgifimage`,
`libquick`, `libkeva` and `liblynx`.

Fresco does not crash on this. It swallows the `Heif` class failure (logged as "Rejecting
re-init … nativeheif.Heif", 400–900 times per run) and falls back to the platform decoder. That
fallback leaves the placeholder grey on OH.

Evidence (`oh-evidence.txt` quotes every line):

- `sensor-online-1/child.stderr:7745`: `[SOURCE-NATIVE-LOAD-FAIL] … libbdheif.so namespace=0 … _ZNSt6__ndk119__shared_weak_countD2Ev: symbol not found`.
- `:7741`: the search path, `/system/lib64` ahead of `/data/local/tmp/asx/lib/arm64-v8a`.
- `maps-early.txt:954` / `:1685`: both copies of `libc++_shared.so` mapped.
- `sensor-online-3/child.stderr:21092`: `libgifimage.so` fails on `…__shared_weak_count13__get_deleter…`.
- On Android, `libttheif_dec`, `libbdheif`, `libgifimage`, `libstatic-webp` and `libimagepipeline`
  all load through `clns-9` (`runs/*/logcat-excerpt.txt`).
- The OH screenshot [`oh-sensor-online-3-idle.jpg`](images/oh-sensor-online-3-idle.jpg) shows the
  video cover and the article thumbnail both grey. On Android
  ([`android-first-feed.jpg`](images/android-first-feed.jpg)) they are drawn.

**Fix:**
- Add `libbdheif.so`, together with `libttheif_dec.so`, and `libgifimage.so` to the Android-ABI
  native targets. That is the mechanism `libsscronet.so` already uses.
- Do not add C++ ABI symbols to a shim.
- The wider option is to let namespace 0 resolve the APK's `libc++_shared.so` for app libraries.
  It would fix all 15 libraries at once, but it is riskier: OH's own users of that library are
  already mapped against the system copy.

**Not proven:** whether the smaller article thumbnails are HEIC too. OH logs no image URLs or
content types, and on Android article and gallery pictures are mostly WebP. If those thumbnails stay
grey after the fix, check WebP decoding through `BitmapFactory` and the upload path next.

**Would disprove it:** grey tiles whose bytes are JPEG or WebP, or covers that stay grey with
`libbdheif` loaded.

**Not read:** the board's own `/system/lib64/libc++_shared.so`. The board was read-only this round.
Check it with `llvm-nm -D <copy> | grep -c __ndk1`.

## The `work_thread` SIGABRT

**Conclusion: this is Umeng's thread, it does not kill the app, and the abort is most likely in a
child process that Umeng forks.** It appears in all 7 Toutiao runs in `applib23` that get past
startup.

Every occurrence has the same form:
- `sigaction #16 signal=6` is immediately followed by `Fatal signal 6 (SIGABRT), code -6 (SI_TKILL)`
  on `Thread: <fresh tid> "work_thread"`.
- The backtrace is empty.
- `x13` holds the ASCII text `" is null"`.

What is verified:

- **Who creates the thread.** `com.umeng.mc.e.a()` (`classes17.dex` 0x9658de) is the only code
  referencing the string `"work_thread"`, and it does `new HandlerThread("work_thread")`.
- **What runs before the abort.** In every run, `libumeng-spy.so` loads 0.3–0.9 s before the abort.
  Its `Java_com_umeng_umzid_Spy_getNativeID` calls `signal(17 = SIGCHLD)` at 0x7bfc, then `fork()`
  at 0x7c00.
- **Who installed `sigaction #16`.** It is not a reset to SIG_DFL. Its flags (`0x18000004`) and
  callback are byte-identical to `#3`, which `libsafe-mode-native-lib.so` + 0xb28
  (`handler(int, siginfo*, void*)`) installed at startup (`sensor-online-1:337-344`, maps line 1560).
  Entries `#9`–`#15` are Chromium crashpad, at `libwebviewchromium.so` + 0x4099190
  (`:17081`, maps line 570). So `#16` is crashpad putting SafeMode's handler back before
  re-raising the signal.
- **Whether the app dies.** Not from this abort, and no cppcrash was collected for it.
  - In diag1 and fix1 the app is still alive (state `S`) at the harness's final check.
  - In the other five runs the process is gone by the final check, but the same pid keeps logging
    for another 26–51 s after the abort first. Example: sensor-online-1, pid 3485, 15:41:39 before
    the abort, last line 15:42:05.

**Hypothesis: the abort happens in the child forked by `getNativeID`.** A forked child inherits the
name `work_thread`. Three things support this:
- The aborting tid is fresh and never appears again in the log.
- The app survives.
- After the abort, the shim's `sigaction` counter hands out `#16` a second time in the app
  (`fresh-online-1:21646` then `:22640`; `diag1:22517` then `:23391`). That is what happens if the
  counter was incremented in a copy of the process.

The alternative, that the handler chain parks the thread forever, is not excluded.

**Next steps:**
1. On the board, read-only: `ls /data/log/faultlog/temp /data/log/faultlog/faultlogger | grep cppcrash-<abort tid>`.
   The harness only collects `cppcrash-<app pid>`, so a dump for the child would have been missed.
2. Add `fork`/`abort`/`raise` interposers to the preloaded `libwebview_bionic_shim.so`. They should
   log pid, tid, comm and `dladdr` of the caller, tagged `[WESTLAKE-FORK]`/`[WESTLAKE-ABORT]`.
3. As an A/B test, withhold `libumeng-spy.so`. `Spy.<clinit>` catches the load failure. If the
   abort disappears, the attribution is confirmed.
4. Check a side effect: after Umeng installs its SIGCHLD handler, which loops on `waitpid(-1)`, no
   `[WESTLAKE-REAP]` line appears again.

## Method

- **Taps** are `input tap` at fixed coordinates, 7.3 s apart. Before each tap, `drive.sh` closes the
  system notification prompt and Toutiao's login promo with BACK. It never sends BACK while focus is
  null or unknown.
- **Touch latency** comes from atrace (`input view gfx am wm dalvik` plus app tracing). It is the
  main-thread `deliverInputEvent` begin minus the `eventTimeNano` of the event it carries.
  `tapcmd_to_main_ms` (89–313 ms) is the `input` command's own cost and is kept separate.
- **Visual timing:**
  - screenrecord writes a Winscope metadata track: per-frame `CLOCK_MONOTONIC` plus the
    realtime→elapsed offset. `drive.sh` stamps every action with `CLOCK_REALTIME`, so taps, frames
    and atrace share one axis. On this phone monotonic and elapsed agree to under 1 µs.
  - The feed region is y 240–1700. The page has switched once it differs from the frame before the
    tap. Content is the first such frame whose grey standard deviation is above 30. Measured values:
    a blank loading page ~0.3, a skeleton 13–22, the text-only 热榜 ~35, image feeds 56–85.
- **Jank** comes from `dumpsys gfxinfo`, reset after the launch phase, plus logcat
  `Choreographer`/`Davey!` lines for the app pid and the atrace main-thread top-level slices.
- **Native loading and image formats** come from `/proc/<pid>/maps`, `nativeloader` logcat lines, a
  `find` over the data directories, and the magic bytes of every Fresco disk-cache entry.

## Data safety

- **Backup.** Before the first `pm clear`, `/data/user/0`, `/data/user_de/0` and `Android/data` of
  the package were tarred with `--selinux --numeric-owner`: 16,860 + 5 + 60 entries. One runtime
  socket cannot be archived.
- **Restore.** After the runs: `pm clear`, then extract the tarballs. Re-tarring and listing the
  restored trees gives 0 differences in mode, owner, size, mtime and path for all three.
- **Check.** A relaunch opens the feed with no consent dialog and the user's own local channel
  (广州); the runs had 深圳 ([`restored-state.jpg`](images/restored-state.jpg)).
- **Not restorable:** `pm clear` also resets runtime permission grants, and the grants before the
  runs were not recorded. After the runs no dangerous permission is granted, and the notification
  prompt is left undecided (dismissed with BACK).
- **Backup copy.** The backup stays on the phone at `/data/local/tmp/tt26-backup` (root-only,
  1.5 GB); delete it when no longer wanted.

## What was wrong first

- **S1.** The login promo (`TransparentAccountLoginActivity`) opens about 8 s into a second launch
  and takes focus, and all four S1 taps landed on it. `drive.sh` now closes it: first BACK hides its
  keyboard, second closes it. S2 and S3 replace S1's tap phase.
- **Tab names.** Tapping 热点 auto-scrolls the tab strip, so the later fixed-x taps hit 小视频 and
  小说 (first launch) or 小视频 and 热榜 (second launch, where 推荐 is pinned left), not the names in
  `drive.sh`. Labels are read from the pixels instead
  ([`tab-strips-F1F2S1S2.png`](images/tab-strips-F1F2S1S2.png), [`tab-strips-F3S3.png`](images/tab-strips-F3S3.png)).
- **Content threshold.** The first threshold, std > 40, missed 热榜, a white text list at ~35. It
  is now 30. That only changed 热榜 and moved two 小视频 values 20–120 ms earlier, onto a
  half-drawn grid.
- **Logcat readers.** `run.sh` backgrounded `adb logcat` through a shell function, so `kill` hit the
  subshell, and each reader kept appending later runs to earlier files. It is fixed in
  `scripts/run.sh`. The archived logs were cut at END + 10 s, and every `summary.json` re-derived
  from the cut logs is byte-identical, because all logcat metrics are filtered by the app pid.
- **The offline analysis's first draft.** It guessed OH's libc++ namespace was `__h`. The OH SDK
  copy uses `__n1`; what matters is that neither exports `__ndk1`.

## Rules this adds

- Compare touch latency on Android as event time → main-thread `deliverInputEvent` (atrace). It is
  the same quantity as Westlake's post→run and costs no instrumentation.
- Time screen recordings with the Winscope metadata track, not frame indices or OCR.
- Read which tab was hit from the pixels. A scrolling tab strip makes fixed coordinates lie.
- Before `pm clear` on someone's device: tar the data with `--selinux --numeric-owner`, verify the
  restore by listing, and record `dumpsys package` runtime permissions, which `pm clear` also resets.
- A native library that fails only in namespace 0 on a `std::__ndk1` symbol is a C++-runtime
  resolution problem, not a missing API. Route it to the Android-ABI namespace.

## Layout

| Path | What |
|---|---|
| `results.json` | Everything above: the reference by condition, per-run summaries with verified tab labels, metasec, thumbnails, `work_thread`, data safety, raw-archive hashes |
| `scripts/` | `run.sh` (host) + `drive.sh` (device) for one run; `analyze.py` → `runs/<RUN>/summary.json`; `aggregate.py` → `results.json`; `strip.py`/`tabcheck.py` for frame sheets |
| `runs/<RUN>/` | `drive.log` (realtime stamps), `amstart.txt`, `gfx_*.txt`, `native-maps.txt`, `imgmagic.txt`, `logcat-excerpt.txt` (original line numbers), `summary.json` |
| `runs/raw-sha256.txt` | Hashes of the raw `screen.mp4`, `atrace.txt` and `logcat.txt` kept in VM a2hlab at `~/a2hlab/android-ref26/` |
| `oh-evidence.txt` | The OH log lines, ELF and dex facts quoted verbatim for the two offline conclusions |
| `images/` | Tab-strip checks, HEIC covers, the OH grey-thumbnail screenshot, Android feed, restored state |
