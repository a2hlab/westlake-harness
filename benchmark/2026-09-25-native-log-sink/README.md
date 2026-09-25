# #44 — App-native library logs visible in the child (liblog → hilog + gated stderr)

**Board entry:** `#44` in `.octos/OUTER_LOOP_REVIEW.md`
**Date:** 2026-09-25
**Status:** **VM-side done** (source change + single-library rebuild, verified). **On-board Toutiao verification is pending an outer-loop board slot** — 5cd1e3dd is occupied by #42's Toutiao timing, and the task says to ask before running Toutiao there.

## Why app-native logs vanish in the child

#41 had to downgrade a conclusion because the child's native log channel is broken: app-native `__android_log_print` / `__android_log_buf_write` (Cronet, ttnet, Lynx, metasec) are silently dropped, and metasec's own marker (`E METASEC : MSTaskManager::DoLazyInit`) is a *native* log, so its absence proved nothing.

Root cause, from inspecting the built libraries:

- `out-all0925/core-runtime/liblog.so` exports `__android_log_print` / `__android_log_set_logger` / `__android_log_write_log_message` **but contains no `HiLogPrint`, no `0xD000F00`, no `register_hilog`** — the hilog bridge is **not in liblog.so**.
- The bridge (`android_log_hilog_bridge.cpp`, whose constructor calls `__android_log_set_logger(hilog_logger)`) is compiled into **`liboh_adapter_bridge.so`** and **`liboh_android_runtime.so`** instead.
- `__android_log_set_logger` merely sets a per-liblog-instance global (`logger_write.cpp`: `logger_function = logger;`, no abort). So setting it from those OH-facing libs only affects *their* liblog instance. The liblog instance the app's own native libraries bind — a copy in the ART classloader namespace, and/or one whose logger the framework never set — keeps liblog's **default logd writer, whose socket is dead on OH**. Result: dropped.

`★ Insight ─────────────────────────────────────`
- The fix has to live *inside* liblog.so, not in a sibling library: only a constructor compiled into liblog.so runs for **every** liblog instance, including the app-namespace copy. A setter in another .so can only reach the instance that other .so is linked against.
- `__android_log_set_logger` has no once-guard, so multiple registrants are safe (last wins) — but "last wins" is why placing the setter only in a late-loading sibling can't be relied on; self-registration at liblog load is the robust point.
`─────────────────────────────────────────────────`

## The fix

`westlake/framework/core/jni/westlake_liblog_native_sink.cpp` (new), added to `liblog.so`'s `sources` in `westlake/native/libraries.json` (8 → 9). A `__attribute__((constructor))` calls `__android_log_set_logger(sink)` so every liblog instance self-registers. The sink:

- **hilog** — `HiLogPrint(LOG_TYPE_CORE, level, 0xD000F00, tag, "%{public}s", msg)`, the same domain/route as the B.37 Java fix. `HiLogPrint` is resolved through `dlopen("libhilog.so")` + `dlsym` (cached), so **liblog.so gains no hard `libhilog` dependency** and stays loadable in namespaces that cannot see libhilog. `%{public}s` avoids hilog's `<private>` redaction.
- **stderr** — when `WESTLAKE_SOURCE_LOG_STDERR=1`, also `write(2, …)` in logcat form `"<prio> <tag> : <msg>\n"`. The env is read **once and cached**; when unset (the default, and every #38 timing run) the stderr branch is skipped entirely, so the hot path is one cached branch plus the pre-existing HiLogPrint call — no queueMs impact off-diagnostic.

This is the native-side equivalent of the B.37 Java fix (`android_util_Log.cpp` `Log_println_native`): direct-to-HiLogPrint, bypassing the dead logd transport.

**Source commit:** `e627b77` on branch `fix/native-log-sink-44` in the westlake source repo (committed only, not pushed; the shared tree was restored to detached `22b9453` afterwards).

## Build verification (`evidence/liblog-build-verify.txt`)

`build_android_native.py --library liblog.so` → `out-log44/lib/liblog.so`, sha256 `fcdfd9b6…`:

- **DT_NEEDED: `libc++.so`, `libc.so` only — no `libhilog`** (dlopen path holds).
- Exports intact: `__android_log_print`, `__android_log_buf_write`, `__android_log_set_logger`, `__android_log_write_log_message`.
- Constructor present: `westlake_register_native_log_sink` in INIT_ARRAY.
- Sink strings present: `WESTLAKE_SOURCE_LOG_STDERR`, `HiLogPrint`, `libhilog.so`, `%{public}s`, `AndroidLog`.

## On-board acceptance (pending a board)

To be run once the outer loop frees a board (not while #42 times Toutiao):

1. Overlay `out-log44/lib/liblog.so` onto the runtime staging's `liblog.so`; launch Toutiao via `probe_source_app.py` with `--runtime-env WESTLAKE_SOURCE_LOG_STDERR=1`.
2. `child.stderr` should now show app-native log lines (Cronet/ttnet/Lynx/metasec tags).
3. Compare the native-tag volume and set to the Android reference `N100CU025C18D000128` logcat for the same process; list the tag-set differences.
4. Confirm no main-thread slowdown: #38 `queueMs` before/after unchanged (stderr is off by default; measure the diagnostic run).
5. Answer the #41 open question: **does `METASEC` / `MSTaskManager::DoLazyInit` actually appear on OH** once the native channel is visible.

## Layout

| path | what |
|---|---|
| `results.json` | root cause, fix, build verification, pending on-board plan |
| `evidence/liblog-build-verify.txt` | rebuilt liblog.so: deps, exports, constructor, sink strings, sha256 |
| `scripts/westlake_liblog_native_sink.cpp` | the sink source added to liblog.so |
