# Toutiao-on-unified copy-list — comparison ONLY (this round)

**Decision (user, 2026-10-01): MAINLINE.** Toutiao (`com.ss.android.article.news`) is restored on the
current code base as an **ordinary key** in the unified state — standard `bm` install, the same U9/U10
runtime, run inside a `bms_batch` shard with every other app. **No** tt-rt dedicated runtime, **no**
`provision_toutiao.sh`, **no** dedicated AOT, **no** watchdog. Each wall is fixed with a **generic** fix in
the shared layer (JAR / native / config) with **no regression** to other apps. The old route `tt-rt.tar`
is **only a source to copy generic fixes from**; Toutiao-specific hacks are **not** ported.

**This round delivers the comparison only.** The outer loop reviews this list before any code is written.
Every Toutiao fix that later enters the unified state must carry a **regression control** and pass the
full `compare_runs` sweep with **zero regression**. Normal pacing, no queue-jumping. Machine form:
`copy-list.json`.

## Structural comparison (SHA, death-chain libs; old tt-rt vs U9)
| file | old (tt-rt, works) | U9 (unified) | |
|---|---|---|---|
| `libstdc++.so` | `1d914dab` | `7e06cd8b` (native/payload/android/lib64) | differ — **present in U9**, so wall 1 is config, not a missing lib |
| `liboh_adapter_bridge.so` | `d4fae8e5` | `84695d62` | differ |
| `liboh_android_runtime.so` | `8ab6742d` | `ac59dec0` | differ |
| `appspawn-x` | `a7a358c6` | `1d3b0881` | differ |
| `fw/adapter-runtime-bcp.jar` | `ea5d8b27` (170 cls) | **absent** | U9 = `oh-adapter-runtime.jar` (PathClassLoader) + `adapter-mainline-stubs.jar` (BCP) |

The old route is a CLAMP48 **BCP** jar; U9 has no `adapter-runtime-bcp.jar`. 141 of its 170 classes are
absent from U9 but are the **old adapter core** (AbilityConnectionBridge / ActivityClientControllerAdapter
/ LifecycleAdapter / Oh*Converter), already re-expressed under new names in `oh-adapter-runtime.jar` —
**not Toutiao patches**. It carries **no** metasec / MainActivity / bytedance classes.

## Install
Toutiao enters the corpus as a normal key (`toutiao.apk`, `com.ss.android.article.news`), `bm`-installed
and run in a `bms_batch` shard. No special staging.

## Walls (U8 Toutiao death-chain order) → generic unified fix
### Wall 1 — `libflipped.so` private-namespace closure cannot resolve `libstdc++`
- **Evidence:** DIGEST 558 — fails "despite U8 globally deploying that SONAME shell"; `libstdc++.so` is
  present in U9, so the gap is the **app private namespace** not linking it (config, not a missing lib).
- **Generic fix:** make `libstdc++` (a shared system SONAME) resolvable from app private namespaces on
  route-A — add it to the private namespace's linkable set in the host `StockCreateConfiguredNamespaces`,
  or give that namespace a linked edge to the namespace that already holds `libstdc++`. **Generic:** any
  app whose bundled `.so` DT_NEEDs `libstdc++` benefits; apps that don't are unaffected.
- **Copyable source:** the old host's namespace-closure config for `libstdc++` (how tt-rt wired it into
  app private namespaces) — diff old vs U9 `StockCreateConfiguredNamespaces`; reference
  `benchmark/2026-08-23-toutiao/native-analysis/android11-import-resolution.json` + DIGEST N3b
  (`dlopen_ns`/`RTLD_NOLOAD`).
- **Layer:** native / host namespace config (shared). **Other-app impact:** none expected (additive;
  verify no second-copy of `libstdc++`).
- **Build:** after review — cc-t3 specs the rule + source, **cx-bms** builds into **U10 native** (one
  version with the shim), with a regression control + non-regressing full compare. **Not this round.**

### Wall 2 — MainActivity null Boolean (`enableGlobal`)
- **Evidence:** DIGEST 558 — "app-map state, not platform Boolean semantics": a consequence of wall 1's
  namespace/global linkage, not a standalone platform fix.
- **Generic fix:** none standalone — re-verify after wall 1; **do not** add a platform Boolean stub (that
  would be an app-specific hack and could touch other apps). Re-assess on-board after wall 1.

## Not ported (Toutiao-specific; the old route only lends generic fixes)
tt-rt dedicated runtime (old `fw/*.jar` + `boot/`), `adapter-runtime-bcp.jar`, the **metasec** safe-value
stub (ByteDance `ms.bd.c` dispatch), `webview-t-lib` (Toutiao's private Chromium — it renders via the
unified route-A WebView like other apps), `provision_toutiao.sh` / dedicated AOT / watchdog / the two
`c91d26bf` cleanup dirs. If Toutiao proves unstable **after** the walls clear, revisit only via a generic
mechanism with the regression gate.
