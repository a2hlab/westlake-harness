# White vs lit: the white cluster is four mechanisms plus four unexplained keys, not one wall

#90, offline, no board. Only existing real runs are used. The question: what separates the 20-key white cluster
(`candidate-first-fatal-clusters` cluster 0, "no observed termination") from the lit apps?

**Result.** No single feature separates the cluster, because it is not one population. Of the 16 keys that showed
a live white or black window on their signing run:

- 12 fall into four mechanisms; each mechanism has a feature that is rare among the 117 lit keys:

| mechanism | white keys | feature, white vs lit | lit hits |
|---|---|---|---|
| **M1** multi-window: the top Activity's window gets the empty Surface | 2 | 2/16 vs 0/117 | none |
| **M2** the whole content is a WebView, and we have no renderer | 5 | 5/16 vs 1/117 | caniwebview: its WebView area is blank too, but its own native UI around it is lit |
| **M3** GLSurfaceView's Surface has no native window (EGL IAE) | 3 | 3/16 vs 1/117 | shadereditor: its GL view is not the main UI |
| **M4** no window session is ever created | 2 | 2/16 vs 0/117 | none |

- **4 keys stay unexplained**: dddmodel2, fd-mobile, itsdicey, AppManager.

**Paired runs.** For the same app on the same state, one run lit and one white (7 pairs, 4 keys, 11 runs), M1
classifies all 11 runs correctly. It is the mechanism of the lottery keys (wikipedia, noice, fd-noice, fd-uhabits).

**Static check of M1.** The cross-copy window lookup in the deployed bridge `84695d62` is a single process-wide slot,
overwritten by every createSession (`oh_window_manager_client.cpp:96-128`). Only the last-created window session can
be resolved by the other bridge copy.

## What was wrong before

- **e92a7a87a7** wrote "白是内容/渲染(N11h 双拷贝族)" (white is content/rendering, the N11h double-copy family). The
  outer loop refuted the double-copy half: two bridge copies are in 115/115 lit keys and 17/17 white keys
  (`2026-10-02-double-copy-universality`). That half is void.
  - The other half still stands: "not slow". 15 of 16 keys reach `activityResumed (first-frame)` (all but toutiao).
  - The double copy matters only through M1: with one window, "the last session" is always the only one.
- **Two earlier white-window discriminators were already withdrawn**:
  - "the Activity session is looked up twice" (DIGEST 2026-10-01 17:55: lit 90.5% vs white 70.6%);
  - "the icon session is not rescued" (17:57/18:00: a risk factor, not a discriminator).

  Both looked at the wrong window. What decides lit vs white is whether the **top** Activity (the last ability the app
  asked SceneBoard for) got the empty Surface. That holds for 11/11 paired runs and is 0/117 in lit keys.
- **The COMPOSE-WALL idea is dead again on the whole surface**: Compose apps are white 1/16 vs lit 15/117.
- **`per-key.csv` pointed some keys at the wrong run.** For wikipedia it held window 1, which was white, while the
  key is signed lit from window-5 r1. This round uses `u10-1-t8-reference/sources.json`, which records the run that
  carried each verdict.

## Data (all real runs, `pairs.json`, `population.py`)

**Pairs (step 1):** same key, same state, outer-signed t20 per run. 7 lit×white pairs over 4 keys, 11 runs:

| key | runs | state |
|---|---|---|
| fd-noice | lit, lit, white | U5 5ea |
| fd-uhabits | white, white, lit | U5 5ea |
| noice | lit, white | U7 61b |
| wikipedia | white (w1), lit (w5 r1), white (w5 r2) | U10.1T8 5cd |

The U8 61b repeats (`2026-10-01-u8-flaky-repeat`) cannot be used: their hilogs are gone; run_index says files_gone,
and only t20.jpeg is left.

**Population (step 2):** the U10.1T8 stage-A run that carried each signed verdict.
- **WHITE (16)**: cluster 0 keys signed alive-white-window / white / alive-black-window / alive-black-content on that run.
- **LIT (117)**: signed lit, plus the lottery fd-noice and yahtzeedicer, which were lit on their run.
- Left out:
  - frequent-habits (app_failed, never launched);
  - tutanota (dead).

**Hilog window.** From the launch minus 3 s to min(t20, hilog end), per the DIGEST rule: the captured hilog ends 4–7 s
before t20.

**Templates (`templates.py`).** Level + tag + message, with hex, numbers, the package name and the hitrace prefix
normalised. Scope is `app` (the app's pids) or `sys`. Presence counts, not line counts.

## Step 1: paired diff (`pair_diff.py` → `pair-diff.csv`, `pair-diff.txt`)

Templates present in only one side of a pair, ranked by keys and pairs:

**Only in the lit run:**
- **7/7 pairs, 4/4 keys**: `RSBaseRenderUtil::DealWithSurfaceRotationAndGravity`. render_service composed an app
  buffer. This is the outcome, not the cause.
- **5/7, 3 keys**:
  - `[OH_WSA-relayout] … visibility=`;
  - WMS `ForegroundTask` / `Foreground state invalid`;
  - the probe's view tree with `DL=T`.

**Only in the white run, 5/7, 3 keys**: the same view tree with `DL=F`. The views exist and have their size, but
were never drawn.

Following those lines to the window sessions gives the mechanism, readable in raw lines. In the white runs:
1. the app's second Activity (AppIntro / Intro / InitialOnboarding) is the one SceneBoard shows;
2. its window session was created **first**;
3. its `BBQ.update` finds `unknown sessionId` and gets `BBQ.getSurface: ohNativeWindow null — returning empty
   Surface`;
4. the launcher Activity, whose session was created second (= last), gets the native window and EGL surface but is
   not on screen.

The lit runs are the same with the creation order reversed. Example: wikipedia, lit r1 L21281–21489 vs white r2
L21579–21766.

`multiwin.py` turns this into one feature: misroute = ≥ 2 VRIs, and the last-requested ability's VRI got an empty
Surface and was never rescued. Results:
- white runs 7/7 True, lit runs 4/4 False (all 11 runs right);
- population: white 2/16 (noice, fd-uhabits), lit 0/117. The 28 lit keys with two sessions all have their top
  Activity resolved (top outcome `ok` 28/28).

## Step 2: population rates (`population.py`, `static_features.py`, `rank.py` → `ranked-features.csv`)

3894 templates occur in ≥ 3 keys; the Bonferroni 0.05 cut is p < 1.3e-5. **Only one template family passes**: the
Mali GL driver init / `glLinkProgram` in the app process.

| feature (kind) | white | lit | Fisher p | paired support | mechanism |
|---|---|---|---|---|---|
| GL program linked in the app (runtime, lit-side) | 9/16 | 117/117 | 9.2e-8 | 0/7 | symptom: the app drew more than a glClear |
| full-screen WebView content (view tree) | 5/16 | 1/117 | 7.6e-5 | 0/7 | **M2** |
| RS composed an app buffer (runtime, lit-side) | 12/16 | 117/117 | 1.5e-4 | 7/7 | outcome |
| APK references GLSurfaceView (static) | 7/16 | 7/117 | 2.0e-4 | n/a | M3 (static) |
| SceneBoard `StartAbilityBySpecified` launch | 7/16 | 11/117 | 1.4e-3 | 0/7 | association, confounded with the M2 shells |
| GLSurfaceView `eglCreateWindowSurface` IAE | 3/16 | 1/117 | 5.4e-3 | 0/7 | **M3** |
| no content leaves in the view tree | 6/16 | 11/117 | 6.6e-3 | 0/7 | content empty, any cause |
| **top Activity got the empty Surface** | **2/16** | **0/117** | 0.014 | **7/7** | **M1** |
| no window session created | 2/16 | 0/117 | 0.014 | 0/7 | **M4** |
| APK is Capacitor/Cordova | 2/16 | 0/117 | 0.014 | n/a | M2 (static) |
| APK has libGDX | 2/16 | 0/117 | 0.014 | n/a | M3 (static) |
| full-screen SurfaceView/GLView | 2/16 | 1/117 | 0.038 | 0/7 | M3 |
| WINDOW_STATE_ERROR event | 5/16 | 16/117 | 0.081 | 4/7 | does not separate |
| two window sessions | 5/16 | 28/117 | 0.36 | 0/7 | does not separate (M1 needs the order) |
| AppCompat (APK) | 10/16 | 67/117 | 0.45 | n/a | does not separate |
| launcher trampoline (66 scanned) | 3/8 | 14/34 | 0.72 | n/a | does not separate |
| Compose (APK) | 1/16 | 15/117 | 0.89 | n/a | does not separate |
| B10 startup / later ActionBar theme | 1/16, 2/16 | 17/117, 35/117 | 0.92, 0.97 | n/a | does not separate |
| double copy (outer table) | 17/17 | 115/115 | 1 | – | does not separate |

**Why the GL feature is strong but not a cause.**
- Seven white keys never link a single GL program: the Capacitor/WebView apps, termux, toutiao, dddmodel2 and
  webrtc-check.
- Five of them (all but termux and toutiao, which never create a window) do get an EGL surface
  (`eglCreateWindowSurface` succeeds), and their view tree is drawn (`DL=T`). The content draws nothing but the
  background, a glClear, which needs no shader. For the WebView apps that is the type-zero
  WebView stub.
- It marks "nothing beyond the window background was drawn" and points at the content layer, not the window path.

## Per white key (`white-keys.csv`)

| mechanism | keys | evidence |
|---|---|---|
| **M1** top Activity got the empty Surface | noice, fd-uhabits; also the lottery keys wikipedia, fd-noice when white | misroute True; pairs 11/11 |
| **M2** full-screen WebView, no renderer | vaults-randomlydie, degeder-yam, paultirk-yatoo (Capacitor/Cordova), jiten-webview, webrtc-check | view tree content = CapacitorWebView / WebView, 1200×1920; already DIGEST 2026-10-01 18:05 (J10g) for three of them |
| **M3** GLSurfaceView Surface invalid | flowitgame, fd-app, fd-shatteredpixeldungeon (two libGDX) | `GLSurfaceView: IllegalArgumentException: Make sure the SurfaceView … has a valid Surface`; DIGEST 2026-10-01 07:57 saw it on fd-app/SPD |
| **M4** no window session | termux (SceneBoard `StartAbilityBySpecified`, no app createSession), toutiao (still in Application init, known wall 1) | `createSession: success` 0; lit 117/117 have ≥ 1 |
| **unexplained** | dddmodel2 (empty FragmentContainerView, two sessions, top resolved), fd-mobile (black window, empty FragmentContainerView, two sessions, top resolved), itsdicey (black content, custom DiceView), fd-AppManager (white, own text views in the tree) | no app-side error/warning template that is rare (≤ 3/117) in lit keys; no separating view-tree or static feature |

## Top 3: mechanism, the smallest test, predicted movers

**1. M1: single-slot cross-copy window lookup.**

Mechanism, static, deployed bridge `84695d62`:
1. `createSession` publishes its native window through two process env vars, `WESTLAKE_WINDOW_SESSION_ID_V1` and
   `WESTLAKE_NATIVE_WINDOW_PTR_V1` (`oh_window_manager_client.cpp:96-103`, `:656-660`). Each new session overwrites
   them.
2. `oh_wm_get_native_window` (`:1015-1018`) asks its own copy's `sessions_` map first. For the compat shim that is the
   other bridge copy, so the map is empty. It then calls `readProcessWindowTarget`, which answers only when
   `sessionId == the last published one` (`:116-128`).
3. With two live windows, the first-created one always gets an empty Surface. The app is white exactly when that
   window belongs to the top Activity, and creation order between the two Activities is a race: that is the lottery.
4. `strings` on the deployed bridge shows exactly these two V1 names and no per-session variant.

Smallest fix (one file, bridge):
- publish per session, e.g. `WESTLAKE_NATIVE_WINDOW_PTR_V1_<sessionId>`, and read by sessionId;
- keep the V1 single slot as it is.

N11h-r2 (one copy, one `sessions_` map) would also fix it, but it changes namespaces for every app. The per-session
slot changes only the lookup.

Experiment, one board, ≤ 30 min:
- noice, fd-uhabits, wikipedia and fd-noice, ×3 each.
- **Pass:** misroute False in all 12 runs (`multiwin.py`) and t20 lit ≥ 10/12 (screenshots).
- **Fail:** misroute True after the fix. Then the lookup is not the only cause.
- **Regression control:** the 28 lit two-session keys keep their top Activity resolved in the next full sweep.

Predicted movers:
- white → lit: **noice, fd-uhabits** (2), high confidence; both light whenever the race goes the other way.
- lottery → stable: **wikipedia, fd-noice** (2).

**2. M2: no WebView renderer.**

The type-zero WebView stub (`WebViewProviderFix`) draws nothing. Apps whose whole UI is one WebView show the window
background: white, or black for webrtc-check. This is static and already known for three keys (DIGEST J10g). It is
confirmed here on the whole surface:
- full-screen WebView is in 5/16 white vs 1/117 lit;
- the one lit case, caniwebview, has a blank WebView area surrounded by its own native UI.

No experiment is needed. Predicted movers for any fix short of a real renderer: **0**. With a renderer: up to 5.

**3. M3: GLSurfaceView Surface without a native window.**

`EGLImpl.eglCreateWindowSurface` throws IAE for the GLSurfaceView's Surface, so the GL thread never gets a surface
and the window stays white. The decor window itself is fine. Static: the APK references GLSurfaceView in 7/16 white
vs 7/117 lit. The lit 7 do not use it as their main UI; shadereditor's IAE is in a preview view.

Static check before any board time: trace how `SurfaceView`'s child surface obtains an `ANativeWindow` on route A. Is
there a session/BBQ per SurfaceView, or does it reuse the parent's? The single-slot lookup above suggests a child
surface may also miss.

Experiment, if static points to a fix: flowitgame alone (no native libraries besides GL).
- **Pass:** no `Make sure the SurfaceView` IAE and the GL thread logs eglCreateWindowSurface OK.

Predicted movers:
- the EGL IAE disappears for 3 keys (flowitgame, fd-app, SPD);
- lit: flowitgame medium; fd-app low (also a `MediaStore.scanFile` NoSuchMethodError on a background thread); SPD
  low (has a missing-natives fallback path).

**Not separable: dddmodel2, fd-mobile, itsdicey, AppManager.**
- None shows a rare app-side error.
- Two have an empty FragmentContainerView, which points at fragment/content loading, but no log line says why.
- These need a probe of the fragment/content state, not another static pass.

**Predicted first-fatal (first-wall) movers from this round:**
- M1 fix: 2 white keys + 2 lottery keys stabilised;
- M3 fix: wall moves for 3, lit uncertain;
- everything else: 0.

## Rule this round sets

- A white-window cause must classify a **paired** lit/white run of the same app on the same state, and be rare in
  the lit population on the runs that carried the verdicts.
- Report every feature with both denominators, the Fisher p and the paired support. Present in both groups (double
  copy, two sessions, WINDOW_STATE_ERROR) means it is not the cause.
- For a multi-window app, judge the window of the **top** Activity, not "a window failed".

## Files

- `templates.py`: per-run template sets. Cache in `$WORKSPACES/westlake-inputs/cache/white-vs-lit`.
- `pairs.json`, `pair_diff.py` → `pair-diff.csv` (templates differing in ≥ 2 pairs), `pair-diff.txt` (stdout).
- `population.py` → `features-per-key.csv`, `features.csv`, `templates-rate.csv` (top 400 by p).
- `vrt.py`: the runtime's G2.14as view-tree dump parsed per run.
- `multiwin.py`: requested abilities, per-VRI surface outcome, misroute.
- `static_features.py` → `static-features.csv` (APK class defs/refs, trampoline scan, B10 theme table).
- `rank.py` → `ranked-features.csv`, `white-keys.csv`, `results.json`.
