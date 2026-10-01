# Toutiao first run on the unified state (U9, 61b) — first native wall, vs cc-t3's native-closure-prediction

Toutiao (`com.ss.android.article.news`) ran as an ordinary key in the 61b "remaining-original" shard on the
unified U9 state (run `20261001T192815-669fe3b4`, child PID 27706). This reads its U9 hilog against cc-t3's
`native-closure-prediction.md/.csv`. **Result: the predicted wall-1 is confirmed — `libflipped.so` cannot resolve
`libstdc++.so` in the app private namespace, inside `Application.attachBaseContext`, and that aborts bootstrap.**
cc-t3's prediction was written *for U10* (which adds `libstdc++.so` to `shared_sonames`, master `504b66cea`); **U9
does not have that add yet**, so Toutiao hits exactly the wall the prediction says U10 fixes.

## Facts (from the run; screenshots are outer-ring ground truth)
`facts.txt`: `toutiao  shots 2/2  alive t5=yes t20=no  child_hilog=3177  foreground_unconfirmed`
(shard TOTAL keys=10, alive_t20=4). So Toutiao was alive at t5, **dead by t20, never confirmed foreground** — it
did **not** light. Two screenshots captured for the outer ring at:
`westlake-harness-u7-executor/benchmark/2026-10-01-u9-native/rollout/approved-j10g/boards/61b-r2/runner/remaining-original/20261001T192815-669fe3b4/.../toutiao/`.

## First wall — CONFIRMED: `libflipped.so` → `libstdc++.so` in the app private namespace
hilog (PID 27706, thread 27719), verbatim with line numbers:
```
L31249  19:35:36.386 MUSL-LDSO: load libstdc++.so failed, namespace=westlake.anl.app.27706.2, errno=2
L31250  19:35:36.386 MUSL-LDSO: Error loading shared library libstdc++.so: (needed by .../com.ss.android.article.news/android/lib/arm64-v8a/libflipped.so)
L31251  19:35:36.386 [stderr] [B43-BIND] ensureBindApplication FAILED: java.lang.reflect.InvocationTargetException
        Caused by: RuntimeException: Unable to instantiate application ...MuteArticleApplicationStub: RuntimeException: attachBaseCtx invoke DelegateApp.attachBaseCtx err
          at com.tencent.tinker.loader.MuteApplication.attachBaseContext(SourceFile)
          at com.ss.android.article.news.mute.MuteArticleApplicationStub.attachBaseContext(SourceFile)
L31283  19:35:36.388 [stderr] Caused by: java.lang.UnsatisfiedLinkError: F02-A12-UNCLASSIFIED: dlopen_ns failed for .../libflipped.so: Error loading shared library libstdc++.so: (needed by .../libflipped.so)
                      at java.lang.System.loadLibrary(System.java:1661)
```
- `namespace=westlake.anl.app.27706.2` is the **app private namespace**; `errno=2` = ENOENT. `libstdc++.so` is not
  resolvable there because U9's `shared_sonames` does not yet include it.
- The failing `System.loadLibrary("flipped")` is on the **`Application.attachBaseContext`** path (Tinker
  `MuteApplication` → `MuteArticleApplicationStub` → `DelegateApp.attachBaseCtx`). So wall-1 breaks **bootstrap**,
  exactly as the prediction says (`libflipped.so` rank 0, loaded in `Application.attachBaseContext`, the U8
  death-chain wall 1). `ensureBindApplication FAILED` → the Application never finishes initialising.

## What's after — a Java cascade from the same root, not a second native wall
3s later the process dies instantiating MainActivity:
```
L31733  19:35:39.644 [CHILD_CK] J_invokeStaticMain_main_threw: RuntimeException: Unable to instantiate activity
   ComponentInfo{com.ss.android.article.news/...MainActivity}: NullPointerException:
   Attempt to invoke virtual method 'boolean java.lang.Boolean.booleanValue()' on a null object reference
     at com.ss.android.article.news.activity.MainActivity.<init>(SourceFile:327715)
```
This follows the aborted `Application` init: `MainActivity.<init>` reads a `Boolean` that is null because the
Application bootstrap (which would set it) was aborted by the `libflipped` failure. It is the **downstream Java
symptom of the same wall-1 root**, not an independent native wall. It cannot be disentangled on U9 alone — applying
the `libstdc++` add (→U10) and re-running will show whether the NPE clears with the wall (downstream) or persists
(a separate Java wall to chase).

## Is there another native load failure after `libflipped`, before death? — NO
Scanned PID 27706's full life and the 19:35:36.386→19:35:39.644 window specifically. **Between the `libflipped`
failure (L31249) and process death (L31733) the only native load failure is `libstdc++.so` itself** — the window
holds the `UnsatisfiedLinkError` + `System.loadLibrary` stack and the Java cascade, and **no other
`MUSL-LDSO`/`dlopen` failure**. So on U9 there is no second native wall to see: the app dies at bootstrap.

PID 27706's *other* native load failures all occur **~6 s earlier** (19:35:30), during runtime/typeface setup,
and are **benign (handled), not walls**:
- `libhwui.so` — `Error loading header libhwui.so: failed to map header` / `load … failed,
  namespace=westlake.sealed.child, errno=2` (**L28431–28433**), but **immediately resolved from
  `/system/android/lib64/libhwui.so`**: `OH_Typeface: Delegating to libhwui register_android_graphics_Typeface`
  and the Typeface natives hooked (**L28436–28442**). Failed in one namespace, satisfied via the system path →
  handled.
- `libsecurity_component_client_enhance.z.so` (ndk/default), `libartbased.so` (sealed.child/default, the #80
  host-only debug-ART probe) — known optional probes, benign.

**So the predicted next wall `libjnigraphics.so` is NOT reachable on U9** — the app dies in
Application/MainActivity bootstrap before any image-decode/feature lib loads; GLES/OpenSLES/V8/profiler group-C
libs likewise never load. **The next native wall is only observable after the U10 `libstdc++` add lets `libflipped`
load** and the app proceeds past `attachBaseContext`. Prediction §2 (`libjnigraphics` next) therefore remains a
*prediction*, to be verified on U10 — not seen (and not refuted) on U9.

## Benign noise (not walls; app continues past each)
- `libmmi_knuckle.z.so` — **1932×** `load failed namespace=ndk/default errno=2` + `NetPacket: … dlopen fail`: an
  OH multimodal-input knuckle-gesture lib the NetPacket layer probes repeatedly; absent on this device, tolerated.
- `libartbased.so` ×2 — the #80 host-only debug-ART probe (see `2026-10-01-n11b-r3-loaderror-analysis`), benign.
- `libsecurity_component_client_enhance.z.so` ×2 (`ndk` ns, SecComp optional init); `libhwui.so` ×1.
- `[B8-NATIVE] System.load(/system/android/lib64/libwestlake_html_compat.so) failed: path is outside app domain`
  — webview html-compat, a namespace-policy rejection, not a missing-lib wall.
- `[B32-J] [EARLY-TF] nativePrimeDefaultTypeface reflect FAILED` — typeface priming (the #97 Typeface family).

## Verdict vs cc-t3 prediction
- **Prediction validated, premise not yet met.** cc-t3: `libflipped.so`'s only blocking NEEDED is `libstdc++.so`;
  under U10 (libstdc++ added) libflipped resolves and bootstrap passes. The U9 run confirms `libstdc++` is the sole
  gating NEEDED at `libflipped`/`attachBaseContext` — and that U9 has **not** applied the add, so Toutiao walls at
  wall-1 exactly as predicted-for-pre-U10.
- **Recommendation (prediction §1/§2 stand):** apply the wall-1 `libstdc++.so` → `shared_sonames` add (U10,
  `504b66cea`) to the unified state, re-run Toutiao, and read the next wall. Predicted next generic wall =
  `libjnigraphics.so` (13 consumers, route-A provides it; same additive one-liner) — but it is not reachable until
  bootstrap passes. Also re-check whether the MainActivity `Boolean.booleanValue()` NPE clears with the libstdc++
  add (downstream) or survives (separate Java wall).

Source hilog (not committed): the run `toutiao/hilog.txt` above (33,280 lines); PID 27706 wall at ~line 31250,
NPE at ~line 31733.
