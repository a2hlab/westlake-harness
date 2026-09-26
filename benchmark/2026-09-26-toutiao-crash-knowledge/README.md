# Toutiao on OpenHarmony musl: the crash-class map and how each class is neutralised

Toutiao 13.9.0 (`a1112a0c…`) on DAYU600 / OpenHarmony 6.1.0.31, runtime built from Westlake `22b9453`.
By 2026-09-26 the feed displays fully, physical touch opens articles (body + images render, scrollable),
and a single instance has stayed up 20+ minutes. Getting there meant finding **seven crash classes** behind
"opens then dies in 1–3 minutes". This document is the durable finding: the root cause of each, the fix, and
the one generalisation that matters for any Android app on OH musl.

## The one generalisation

**ByteDance/Android native libraries that read Bionic libc *internals* break on OpenHarmony musl.**
Bionic and musl lay out `pthread_internal_t`, the malloc dispatch table, and `HMAC_CTX` differently; a library
that hard-codes Bionic offsets corrupts memory or faults on musl. Four of the seven classes are this one bug.
Each was neutralised on the musl side — **none required a real Bionic** — because the offending libraries are
security/telemetry/debug infrastructure that the feed and article reading do not depend on (metasec is inert on
OH per `benchmark/.../bionic-app-domain-metasec`). Auditing an APK's native libs for `TPIDR_EL0` pthread reads,
`__libc_malloc_dispatch`, and `HMAC_CTX` usage predicts this class before it crashes.

## The seven classes

| # | Signature | Root cause | Fix (musl-side, no Bionic) |
|---|---|---|---|
| 1 | WebView RenderThread SIGSEGV@0, article page | `webview_bionic_shim.c` `dlopen()` opens the NDK `libGLESv2.so` facade before its §734 translation to `platformsdk/libGLESv3.so`; the facade leaves `glGetString` NULL → Skia GL init fails → `GrContext` NULL → `GrDirectContext::flush` on null in destructor | Reorder the shim so the GLESv3 translation precedes the probe (`libwebview_bionic_shim.so` **85c789f4**) |
| 2 | SIGTRAP on `ThreadPoolForeg`, ~88 s, first video article | OH MediaCodec shim only bridges audio; `native_setup` never errors and hands an empty codec to Java; Chromium then calls the unregistered `getOwnCodecInfo` → `UnsatisfiedLinkError` (an Error, bypasses `catch(Exception)`) → JNI FATAL `brk` | `native_setup` throws `IllegalArgumentException`/`IOException` (caught, video just won't play); register `getOwnCodecInfo` → null (`liboh_adapter_bridge.so` **d4fae8e5**) |
| 3 | libnpth spins a full core at load | `libnpth.so` `JNI_OnLoad` walks a thread list `while(x){x=*x}` from `pthread_self()`; Bionic offset 0 is `next` (→NULL), **musl offset 0 is `self`** (→ infinite loop) | 1-instruction `ret` patch on the walk (`libnpth.so` **8b8d559c**) |
| 4 | `TicketGuardNetw` SIGSEGV@0x28 | A default-namespace second copy of `libttboringssl.so` binds `HMAC_Init_ex` to OH's OpenSSL3 (different `HMAC_CTX` layout) → `i_ctx` NULL | `LD_PRELOAD libttcrypto.so` first so all default-namespace unversioned HMAC binds to BoringSSL (watch `libsqlite.z.so`, the one OH HMAC importer) |
| 5 | `Chrome_InProcRe` SIGTRAP, ~100 s, long sessions | `--single-process` keeps the Blink renderer in the browser process; its PartitionAlloc grows unbounded (~200 MiB/min) and each `mprotect` splits a VMA until `vm.max_map_count` (65530) is hit — RSS only ~2 GB, `overcommit=1`, so it is the mapping count, not memory | Raise `vm.max_map_count` to 1048576 before launch (mapping count then plateaus ~22k) |
| 6 | musl mallocng heap-metadata corruption; SIGSEGV in whatever thread `free()`s next (SQLite via oh_android_runtime, Mali shader compiler, bd_tracker) | `libnpth_xasan.so` / `libnpth_heap_tracker.so` hook malloc via Bionic's `__libc_malloc_dispatch` / `__libc_globals` (strings prove it); on musl they trash the in-band chunk header | Shim REFUSE-list blocks loading these two pure-debug libs (folded into **85c789f4**) |
| 7 | main-thread NPE → `_exit(1)`, ~100–126 s | `libmetasec_ml.so` needs symbols the core `libandroid.so` never built (7 `ASensor*`, then 8 Bionic-libc compat like `__system_property_read`, `__openat_2`); relocation fails → a shared thread dies → `X.DEv` reads its null `Looper` → `Handler.<init>` NPE → `ActivityThread.main` returns. **NOT probabilistic — a missing-symbol chain.** Completing the symbol closure lets metasec load fully, which then SIGSEGVs in `DoLazyInit` reading Bionic `pthread_internal_t` via `TPIDR_EL0` — the true Bionic-bound residual | **Neutralise, don't complete-load**: a no-op stub `libmetasec_ml.so` (app-facing ABI is only `JNI_OnLoad` + one dispatcher `ms.bd.c.m.a`; the dispatcher must return non-null typed safe values or the app NPEs on Boolean unwrap). Under evaluation as of this date |

## The known-good stable baseline

Classes 1–4 and 6 are settled; 5 is a deterministic mitigation. Deploy as one stack:
`libwebview_bionic_shim.so 85c789f4` (carries GLES-order + heap-refuse) + `liboh_adapter_bridge.so d4fae8e5`
+ `libnpth.so 8b8d559c` + run.sh `LD_PRELOAD libttcrypto` / tt targets + `vm.max_map_count=1048576`.
Class 7 (metasec stub) and the two speed layers (JIT file cache, dex2oat AOT) stack on top, each verified alone.
Machine-readable manifest: `westlake-harness-triage46/.../BASELINE.md` and the stability-recipe `fixes.json`.

## Two speed levers (orthogonal to crashes)

- **JIT**: OH's XPM (code-signing enforcement) denies memfd RX, so ART falls back to an anonymous cache and toggles
  RX↔RWX per code publish — the main thread then waits on the mmap write lock. `WESTLAKE_OH_JIT_FILE_CACHE_DIR`
  (an app-private `O_TMPFILE` with dual RW/RX views) removes the toggle; p90 −61.6%. **Precondition:** the dir
  must be pre-created as the app UID, mode 0700, or ART silently falls back to anonymous. (`docs/parity/OH-ANDROID-PARITY-2026-09-05.md`)
- **AOT (dex2oat)**: roughly halves article-open (7.2/5.8 s vs 12–22 s). Must use Westlake's own host `dex2oat`
  (oat version **247**); the local AOSP14 / hanbin `dex2oat64` are oat 230 and their output is rejected.

## Methodology pitfalls (paid for in withdrawn conclusions)

1. **Do not count activity names as substrings** — `grep -c NewDetailActivity` hits the server settings JSON. An article opened only if a lifecycle line exists (`onCreate`/`onResume`/`START`/`[B47-SLA] ENTRY`) **and** the after-N-seconds screenshot shows the article.
2. **Do not diff dmesg line counts** — the ring buffer is full, counts stay constant and hide new avc; grep the text. `normal_hap` is Enforcing, the `su` domain is permissive.
3. **No native stack → no attribution** — DFX has a quota (60/UID/24h, first signal only), so SIG11/SIGABRT often leave no cppcrash. Deploy a passive backtrace recorder before blaming metasec/Bionic/JIT.
4. **One variable per test** — stacking two fixes (e.g. stub + JIT) makes the crash cause unattributable.
5. **Observation window ≥ 40 s (≥ 120 s for video)** — the detail activity can RESUME 15–26 s after the tap; the metasec/OOM layers only appear past ~100 s.
6. **Label consent-tap vs item-tap** — each run has two `uinput` taps; know which `queueMs` you are quoting.
7. **Screenshots are ground truth** — when log signals are ambiguous, the after-N screenshot (article vs feed vs host) decides. Several early "it works" calls were wrong on logs alone.
8. **Read `/proc/PID/maps` in full** — `hdc recv` of it returns a ~4 KB truncated fragment; `cat` on-device to a file first.

## Where hanbin's Bionic route stands

hanbin_adapter's "direction 2" (real Bionic process) targets exactly the class-1-generalisation, and is the
theoretically correct fix for metasec's `DoLazyInit`. But hanbin has **not** proven it: `debug.md` freezes at
2026-08-01, its "今日头条实测可用" (2026-07-22) was retracted on 2026-07-27 (process was actually dead), and it
was still debugging `libmetasec_ml` crashes on 2026-07-31. By 2026-09 it had pivoted to the on-screen graphics
pipeline and sits at phase 2 of 7 on DAYU200 (32-bit). Neutralise-on-musl reaches "read articles" far sooner.

## Evidence

Root-cause analyses and built fixes live in the sibling worktrees committed during the campaign
(`westlake-harness-triage46`, `westlake-harness-refined48`, `westlake-harness-stub48`, `westlake-harness-operator45`,
`westlake-harness-speed50`) and are indexed in `.octos/OUTER_LOOP_REVIEW.md` entries #38 and #45–#50, with the
distilled pitfalls in `.octos/KNOWLEDGE-DIGEST.md`. The cross-project generalisation is in mempal
`harmony/android-compat` (`drawer_harmony_android_compat_8b6f199a`).
