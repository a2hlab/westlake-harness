# fd-saber + x: alive-white on 61b window2, mechanism via the white-vs-lit separation

#90, offline, no board (window3 wrapping — untouched). Correction follow-up (outer 07:06, on-board re-judged): in my
`u13-dead-keys-recheck` I wrongly called **fd-saber** and **x** (`com.twitter.android`) lit/BIND-OK-moved. Their t5/t20
original screenshots are **full-screen white, process alive** — BIND OK / Impeller fallback / no-crash in the *log* only
mean "did not crash", not "on screen" (AGENTS: **screenshots are ground truth**). This re-reads both as alive-white and
judges the white mechanism with cc-t3's separation-table discipline — *does any lit key share the condition?*
(`evidence/separation.txt` has the counts.)

## The separation discipline first: two obvious markers are REFUTED
Grepping all three windows' hilogs:
- **`OpenGLWrapper: Failed to load GLES library using dl open`** (fd-saber's loud signal) appears in **~70 keys,
  including lit** wikipedia (6/6), fd-uhabits (6/6), fd-noice (6/6), helloworld (×11), zigzag (×11), newpipe, markor,
  localsend… → **shared with lit → not the cause.**
- **`OH_LifecycleAdapter: setAppVisibility: viewRoot null (decor not attached)`** (x's signal) appears in **~72 keys,
  same lit set** → **shared with lit → not the cause.**

So fd-saber's GLES-load-fail and x's `viewRoot null` are **red herrings** — lit keys show them and still draw. (Consistent
with DIGEST 679: the only Bonferroni-passing template, "app links a GL program", merely means "content drew nothing but
background" — a description of white, not a cause.)

## The discriminating signal: window published, but activity self-terminates and renders ~0 frames
Markers lit refs do **not** have (`evidence/separation.txt`):

| | app frames/buffers | `verificationAllToken failed` | early `finishActivity: OH TerminateAbility` | bind-starts (relaunch) |
|---|---|---|---|---|
| **fd-saber** (white) | **1** | **1** | **1** (right after BIND OK) | 1 |
| **x** (white) | **1** | **1** | **2** | **2 (relaunch)** |
| helloworld (lit) | 8 | 0 | 0 | 1 |
| zigzag (lit) | 18 | 0 | 0 | 1 |

Both white keys **publish a window session** (saber 7 / x 17 window-publish markers — so it is *not* M4 "no session") yet
render **~0 app frames** (vs lit's 8–18), and both hit `TerminateAbilityWithFlag verificationAllToken failed` + an
**early** `finishActivity: OH TerminateAbility` that the lit refs never do. So the white = **the app's activity
self-terminates (and, for x, relaunches) before it renders any frame into its published window** → the window carries no
app content → full-screen white. (Clean 2×2; n=2 lit refs — small, but the frame-count discriminator agrees.)

## Per-key
- **fd-saber** (Flutter, pid 5833): harness injects `[B8-IMPELLER] EnableImpeller=false` → forced GL/Skia backend; the
  EGL14 + EGLImpl `_eglCreateWindowSurface` hooks are in place (RegHook → liboh_android_runtime). Right after `BIND OK`
  it does `finishActivity: OH TerminateAbility` + `verificationAllToken failed`, ~0 frames → the FlutterActivity is torn
  down before rendering → white.
- **x** (`com.twitter.android`, pid 9567): `finishActivity: OH TerminateAbility rc=0` then `rc=22` + AMS
  `verificationAllToken failed`; **relaunches** (2nd `ensureBindApplication`, pid 9779); the 2nd launch reaches `RESUMED`
  but `setAppVisibility: viewRoot null (decor not attached)` and ~0 frames → terminate/relaunch without attaching content
  → white. (`libtwittermedia` `libGLESv2` ULE + crashlytics `__register_atfork` are non-fatal/media — not the cause.)

## Is fd-saber the U14 Flutter EGL wall? — No
The U14 Flutter EGL interposer (`fff9`, cc-t3 `822dbf198f`) fixes a **live** activity whose `eglCreateWindowSurface`
returns null (it unwraps the ANW → non-null EGLSurface). fd-saber here is different: its activity is **terminated**
(TerminateAbility), the `eglCreateWindowSurface` hook is present and never reported failing a surface, and the loud
`Failed to load GLES` is lit-shared. So fd-saber is **not** cleared by the Flutter EGL interposer — it is the
activity-terminate/no-render white, a different wall.

## M-class
Neither is **M1** (empty live Surface from the single-slot lookup — here the window is torn down / no frames, not an
empty-but-live Surface), **M2** (full-screen WebView — neither renders via WebView), or **M5** (sub-window zLevel). Both
fit a **new class: "window session published, activity self-terminates (`TerminateAbility` + `verificationAllToken
failed`) and renders ~0 frames"** — closest in *effect* to M4 (no persistent window content) but via a
published-then-terminated session, not a never-created one. **The WHY is unresolved** (needs a focused dig): fd-saber is
likely the forced `EnableImpeller=false` with no loadable GL/Vulkan backend → Flutter aborts the activity; x is the
splash/trampoline terminate + relaunch path. Both are **unowned** — not moved by any current U14/U15 part.

## This round's rule
Screenshots are ground truth — `BIND OK` / a rendering-backend "fallback" line / no crash in the log do **not** mean
on-screen. And before naming a white mechanism, run the separation: a marker present in lit keys (here `Failed to load
GLES`, `viewRoot null`) cannot be the cause; keep only the signal lit keys lack (here `verificationAllToken failed` +
early `finishActivity` + ~0 frames).

## Files
- `evidence/separation.txt` — the refuted markers (lit-shared) + the discriminating counts + per-key reading.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board (window3 untouched); no push. Verdict basis = the outer's on-board screenshot re-judgment (alive-white);
this deliverable adds the mechanism, not the visual verdict. Sources read read-only: the U13 run hilogs
(`westlake-harness-u7-executor/.../2026-10-03-u13-stage-a-plan/window1|window2|window2-61b`). The WHY (what finishes each
activity) is left open pending a focused experiment.
