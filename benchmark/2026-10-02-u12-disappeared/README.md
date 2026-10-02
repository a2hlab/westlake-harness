# Window5: six unexplained disappearances, five repair clusters

The original `process-disappeared` label hid **seven explicit APPSPAWN termination
statuses for six keys**. It did not mean there was no cause in the original log.
Conversely, `OnRemoteDied` is downstream cleanup, SIGCHLD17 is a parent notification,
and a B8 background-thread "process kept alive" message does not describe the
completion of the app's outer crash handler. None is an independent killer.

Only the original runs selected by master **2aa6c49df0** `sources.json` are used.
`observations.json` pins each actual APK/run identity, hilog, record, process
snapshots and runtime fingerprint. Source paths below are portable; all hilog
numbers refer to the **original file**, not a grep output or the excerpt's line.
No board access, bundle edit, native implementation or new screenshot verdict occurs.

## Recovered status and root

| Cluster | Keys | App PID | Original hilog evidence | Actual status |
|---|---|---|---|---|
| Resident compat relocation scope | fd-fennec_fdroid, firefox | 25084, 25608 | Fennec:19016 relocation /19018 handler /19024 cause /19088 nested B8 handler /19154 status; Firefox:31058 /31062 /31068 /31138 /31211 | SIGKILL9 for both |
| Private zlib alias/route | burgerking | 570 | 19585 libmmkv NEEDED libz;19587 NitroMmkv ULE;19656 uncaught main thread;19725 preserve kill semantics;19919 status | normal exit1 |
| Locale display-country null contract | cv2-com-kaajjo-libresudoku | 9435 | 38564 NPE;38565 Locale.getDisplayName:2539;38566 ArrangementKt;38598 CrashActivity composition;38691 status | normal exit0 |
| Android dlext relocation scope, then real backend | ppsspp | 26744 | 30860 android_dlopen_ext relocation;30861 caught load error;32594 later VSync;32947 status | normal exit255, consistent with exit(-1) |
| VLC Bionic locale/cleanup residue | vlc | **4317 and 4353 separately** | first:19447 strtoll_l /19449 cleanup_push /19450 vlc load error /19606 exit; second:24281 /24283 /24284 /24375 | normal exit1 twice |

All six `faultlogs/` directories are empty. Each before/after fault inventory
has **identical SHA256**; old system-wide cppcrash entries are not new app faults.
`evidence/<key>-hilog.txt` retains numbered excerpts; `observations.json` holds
the last20 F/E and last10 app events **per PID**, exact same-PID MUSL errors,
external package/PID-bound exit records and separately marked cleanup events.
Driver E-level diagnostics and swallowed coroutine/class probes are context,
not promoted to terminal causes. No targeted lmkd/watchdog/ANR cause is established.

## Why these exit paths are not guesses from status alone

`dex.json` contains APK/per-DEX/tool SHA256 and original dexdump line/offsets.

- **Gecko:** both APKs' `mozilla.components.lib.crash.handler.ExceptionHandler.uncaughtException`
  contain the exact `Uncaught exception handled:` log literal, call
  `CrashReporter.onCrash`, delegate to the preceding UEH, then execute
  `Process.myPid → Process.killProcess`. Fennec classes2.dex:1719135–1719140;
  Firefox classes2.dex:2224102–2224107. The preceding handler is allowed to log
  B8 "kept alive" and return; the outer handler still kills. The observed sequence
  plus SIGKILL strongly corroborates app self-termination, **not an observed
  kernel syscall caller trace**. The `Directory separator` retry message is
  secondary to the GNU relocation failure, not a newly discovered independent root.
- **PPSSPP:** classes.dex `CheckABIAndLoadLibrary` catches the exact logged ULE
  and writes `m_hasNoNativeBinary=true` at offset0x1d (dexdump421958).
  `onCreate` tests that field, waits3000ms, then `System.exit(-1)` at0x17
  (423104–423115); successful branch0x1b bypasses that exit. This closes the
  earlier audit's exit-caller gap. VSync during the timed Java fallback does
  **not** prove the native binary loaded.
- **VLC:** classes5.dex `LibVLC.loadLibraries` catches the first c++ load error
  and continues. Failure of the subsequent `vlc`/`vlcjni` loading prints the
  observed `Can't load vlcjni library:` literal and invokes `System.exit(1)`
  at0x58 (921137–921172). Both real PIDs reproduce the same chain; neither is
  silently substituted for the other.
- **LibreSudoku:** classes.dex `GlobalExceptionHandler.uncaughtException`
  logs the throwable, invokes `launchActivity`, and `System.exit(0)` at0x30
  (846532–846536). The normal status is therefore not evidence of successful
  app completion. The captured stack is already in CrashActivity composition;
  the original entry into that Activity and exact native locale return operands
  are not instrumented.
- **Burger King:** the same main thread records the NitroMmkv exception and
  explicit `[W-ROOM-SURVIVE] main-thread fatal -> preserving kill semantics`
  before exit1. The original terminating syscall caller itself is not captured.

## Repair predictions: wall movement, not promised lights

`results.json`/`predictions.json` give one key per prediction, repair requirements,
original evidence path/lines and explicit unknown next fatal/t20. **Six conditional
wall-movement candidates; zero asserted new lights.** No repair is executed here.

1. **GNU scope (2 keys):** retain the real `__gnu_strerror_r` implementation and
   prove the single resident compat owner is in each ordinary relocation scope.
   Adding a version node or another policy string is not sufficient. Existing
   factory-libc disassembly is in the wall③ audit; no untraceable linker source
   is treated as same-source. The exports-only4698 candidate does not move these
   walls; a separately proved owner/scope fix should remove this handler chain,
   then the next Gecko loading/runtime failure remains unknown.
2. **zlib (1 key):** reuse reviewed U11 batch `host67753f77` precise package
   route and r109c shell50b9ab6a → providerab0820c6. Recipe commit
   `be16148da9ae7bb89c62e81e144ed0bceb5c4669`; details and source lines are in
   `benchmark/2026-10-02-u11-native-batch/README.md:73`. Publish only the private
   alias/provider, not a second root owner; policy already shares libz. Successful
   private closure should advance NitroMmkv initialization; next ReactNative
   API/first-screen behavior is unknown.
3. **Locale (1 key):** AOSP14r1 `Locale.java:2185` makes primary/default country
   calls then returns a possibly null result at2189; `getDisplayName:2539`
   dereferences it. Repair real LocaleNative/ICU behavior and retain countryCode
   after both lookups fail, preserving valid translations/empty-country behavior.
   This is **reference-source contract evidence**, not proof of rebuilding the
   deployed boot artifact. Source SHA checks match the supplied14r1 manifest.
   Do not disable the app's crash handler or blame Compose solely because it is
   the caller. Exact next failure is unknown.
4. **dlext (1 key):** deployed compat015aa **already exports android_dlopen_ext**,
   just as it exports GNU. PPSSPP's LIBC-requested relocation still cannot see
   it. Prove scope first. The existing wrapper weakly forwards
   `__loader_android_dlopen_ext`, or refuses nonzero extinfo if that backend is
   absent (`overlay/android_dlopen_ext.c:19`). The prior pinned actual app calls
   use0x200/0x210. A real namespace-aware backend is still required before calling
   PPSSPP repaired; plain dlopen ignoring those flags is not a fix. If full JNI
   loading succeeds, the no-native exit branch is bypassed; which subsequent
   extended-load call/fatal executes remains unknown.
5. **VLC (1 key):** compat015aa and factory libcfd3c lack `strtoll_l` and Android
   double-underscore cleanup helpers. Factory libc exposes only `_pthread_cleanup_*`;
   do not invent ABI equivalence. AOSP14 `stdlib_l.cpp:48`/`pthread_exit.cpp:52,61,81`
   define integer parsing and cleanup/exit ordering. Upstream shim HEAD532633da
   at1680/1869/1877 is a source candidate; cleanup introduced by826298cc.
   Its TLS explicit-pop list alone does **not** prove complete thread-exit/
   cancellation semantics or consumer record layout. Validate those boundaries
   plus `__pthread_cleanup_pop`, full native closure and sole-owner visibility.
   Removing only strtoll_l leaves the observed cleanup_push exit1 unchanged.

## Identity boundary and replay

`deployed_whois` ran first for compat/zlib/libdl; its raw text explicitly describes
signed **U9** maps, not a fresh window5 owner observation. Window5 fingerprints
independently pin compat015aa and loader0718. Archived unused aa7/old routes also
appear in fingerprints; their presence does not prove a selected live owner.
`native.json` retains actual consumer SHA/DT_NEEDED/LIBC versions; current compat
dynsym and factory libc dynsym are captured, not inferred from names.

```sh
python3 benchmark/2026-10-02-u12-disappeared/collect.py
python3 benchmark/2026-10-02-u12-disappeared/report.py
python3 benchmark/2026-10-02-u12-disappeared/test_analysis.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u12_disappeared
```

Collection needs the pinned local original runs/APKs/toolchain. Delivered tests
use only admitted small evidence/source files, never `.artifacts` or original
external directories. Raw command receipts stay in persistent worktree `.artifacts`;
public evidence changes only portable workspace prefixes. Landing uses additive
documentation deltas, never the entire dirty root README or DIGEST.
The first preflight invocation returned2 because this older worktree has no
`scripts/lab/land.py`; its output is retained as `preflight-initial-missing-tool.txt`.
The corrected invocation uses master's existing tool from this worktree, with
the same landing list; `evidence/preflight.txt` records the final result.
