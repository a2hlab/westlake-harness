# U14 predicted vs actual — the 13 non-lit keys clusters.csv assigned to U14, read on the window-1 signed runs

#90, offline. For each of the 13 non-lit keys `benchmark/2026-10-03-u16-wall-clusters/clusters.csv` groups under U14
(7 clusters A/C/D/G/H/I/J; 11 predict a first-fatal move, G's 2 are z-order/dialog), this compares the prediction to
the U14 stage-A **window-1 signed** runs, then re-clusters the NEW first-fatals into a U17 candidate table.
Signatures are the exact U16 wall-cluster stack (`compare.py` imports `u16-wall-clusters/collect.py`:
`first_fatal` + `cluster_key` + `bind_status` + `dlopen_failures --near-fatal 3`).

> **Errata (outer 88648a6eb9).** The window-1 sign-off's `keys[].lit_runs` is a pair_sheet **pre-screen** field; it
> read 0 for vlc / termux / dddmodel2 even though `summary.gains` (signed 12:52) recorded them showing their own UI.
> The authoritative lit call is `summary.gains` + `keys[].outer_eyeball` (the re-read t20 screenshots), **not**
> `lit_runs`. This version reads lit from `summary.gains`/`reference`/`outer_eyeball`; an earlier version read
> `lit_runs` and wrongly called vlc/dddmodel2/termux not-lit.

## Headline
Of the 11 predicted first-fatal moves, **10 are confirmed** — 8 moved to a new fatal and **2 moved all the way to a
lit screen (vlc, termux)**; the one miss is **fd-libre** (still `ANativeWindow_getFormat`), whose fix is exactly the
**U16 A‴ `u16-flutter-egl-names`** eglGetProcAddress hook built today, not anything in U14, so it is expected and
owned. Separately, G's **dddmodel2 lit its own Menu dialog = the M5 target**. **3 keys newly lit on U14: vlc,
dddmodel2, termux** (termux is lit but hits a functional bootstrap wall behind the lit screen — see U17).

## Per-key (window-1 `u14-A1-r3-20261003T120358`; lit = outer sign-off `summary.gains`/`outer_eyeball`)
| cl | key | predicted | actual | new first-fatal / lit detail | facts |
|---|---|---|---|---|---|
| A | localsend | past eglCreateWindowSurface → Impeller | **moved** | `signal pc0→libflutter.so` (Impeller) | dead; t20=no |
| A | fd-kitchenowl | ″ | **moved** | `signal pc0→libflutter.so` | dead; t20=no |
| A | fd-fluffychat | ″ | **moved** | `signal pc0→libflutter.so` | dead; t20=no |
| A | fd-libre | ″ | **unchanged** | `signal libnativewindow.z.so(ANativeWindow_getFormat)` — raster eglGetProcAddress bypass, fixed by U16 A‴ (not U14) | dead; t20=no |
| C | mcdonalds | past the Realm `_ctype_` load | **moved** | `process-disappeared` (cause not captured) | alive t5=yes **t20=no** |
| C | fd-im-vector-app | ″ | **moved** | `signal librealm-jni.so` (now crashes *inside* Realm) | t20=no |
| D | fd-fennec_fdroid | past bionic `__gnu_strerror_r` | **moved** | `signal libmozglue.so` (now crashes in Gecko glue) | t20=no |
| D | vlc | past bionic `__pthread_cleanup_push` (medium) | **LIT** | own welcome page "欢迎使用 VLC!" (gain) | alive t5/t20=yes |
| G | dddmodel2 | dialog on top (M5, no first-fatal) | **LIT** | own Menu dialog visible = **M5 target** (gain) | alive t20=yes |
| G | fd-AppManager | white→own splash (M5) | **pending-window2** | not in window-1 sign-off (window 2 `u14-A2-20261003T131427` pending) | — |
| H | termux | first fatal → TermuxInstaller bootstrap | **LIT** (functional wall) | own terminal UI + bootstrap-install error dialog (gain); wall = `/data/data/com.termux/files` missing → **U17** | alive t20=yes |
| I | toutiao | both ICU walls removed | **moved** | `process-disappeared` (cause not captured) | alive t5=yes **t20=no** |
| J | fd-plus | bind passes initPlugins | **moved** | `java IllegalStateException: Surface was not locked` | t20=no |

Verdict counts: `moved 8, lit 3, unchanged 1, pending-window2 1`.
- **A (Flutter):** 3/4 moved past `eglCreateWindowSurface` to the Impeller `pc=0`/`libflutter.so` wall; only
  **libre** stayed — its raster thread resolves the surface entry via `eglGetProcAddress`, which the U14 PLT
  interposer doesn't cover (`../2026-10-03-u16-libre-anw/`); U16 A‴ covers it.
- **C/D:** all moved past the bionic relocation walls; **vlc went all the way to lit** (own welcome page); fd-im-vector
  now crashes *inside* `librealm-jni.so`, fennec inside `libmozglue.so`, mcdonalds's process vanished without a
  captured cause.
- **G (z-order, not a first-fatal move):** **dddmodel2 lit its own Menu dialog — the M5 target confirmed**;
  fd-AppManager waits for window 2.
- **H termux:** **lit** (own terminal UI) but its TermuxInstaller shows a bootstrap-install error → a functional wall
  (below), not a render wall.
- **I/J:** toutiao moved past ICU (process gone by t20, cause silent → unlocalized); fd-plus moved past `ScanCallback`
  to a `Surface was not locked` IllegalStateException.

## U17 candidate table (new post-U14 first-fatals, ranked; `u17-candidates.csv`)
| category | keys | new wall |
|---|---|---|
| **U17 candidate** | fd-im-vector-app | `signal librealm-jni.so` — past `_ctype_`, now a crash inside Realm's own JNI |
| **U17 candidate** | fd-fennec_fdroid | `signal libmozglue.so` — past `__gnu_strerror_r`, now a crash in Gecko's glue |
| **U17 candidate** | fd-plus | `java IllegalStateException: Surface was not locked` (`Surface.unlockSwCanvasAndPost`) |
| **U17 candidate (functional)** | termux | hardcoded `/data/data/com.termux/files` not present → bootstrap-install fails (details below) |
| U17 candidate (unlocalized) | mcdonalds, toutiao | `process-disappeared` — moved, but the fatal cause was not captured → needs a fuller dump/rerun to localize |
| owned — U16 | localsend, fd-kitchenowl, fd-fluffychat | `signal pc0→libflutter.so` — Flutter Impeller GLES-proc gap, owned by `u16-flutter-impeller-build` + `u16-flutter-egl-names` (A‴) |

### U17: termux bootstrap — hardcoded `/data/data/<pkg>/files` (the ② investigation)
- **What breaks:** `Termux:TermuxInstaller: FileUtils Error: The termux files directory not found at path
  "/data/data/com.termux/files"` → `setupBootstrapIfNeeded` aborts. termux is lit (its terminal UI shows) but can't
  install its bootstrap.
- **Where our dataDir/filesDir actually maps:** the runtime overrides it — hilog `[B43-BIND] dataDir overridden:
  /data/app/el2/100/base/com.termux`. `fixDataDirs` (AppSchedulerBridge.java:340-360) points
  `ApplicationInfo.dataDir`/`getDataDir()`/`getFilesDir()` at **`/data/app/el2/<uid>/base/<pkg>`** (writable OH
  sandbox), so every app that calls `getFilesDir()` is already fine.
- **Does `/data/data/<pkg>` exist in the child ns:** effectively **no**. `appspawn_x_sandbox.json` tries to
  bind-mount `/data/data/<PackageName>` from the host, but the host `/data/data/<pkg>` does not exist on OH → the bind
  fails (hilog `APPSPAWN ... errno:2 bind mount …`), so the sandbox `/data/data/<pkg>` is empty/absent; its
  `/data/user/0/<pkg>` compatibility symlink points at the same empty location.
- **Why termux specifically:** termux **hardcodes** `TERMUX_FILES_DIR = /data/data/com.termux/files` (a
  `TermuxConstants` compile-time constant), bypassing `getFilesDir()`, so the dataDir override doesn't reach it.
- **Minimal fix (predicted move):** make the sandbox `/data/data/<pkg>` (and the `/data/user/0/<pkg>` symlink)
  resolve to the real dataDir `/data/app/el2/<uid>/base/<pkg>` (symlink or redirected bind) instead of binding the
  absent host path. Then the hardcoded `/data/data/<pkg>/files` lands on the real, writable files dir and bootstrap
  installs.
- **Who it moves (corpus DEX scan, `evidence/datadata-dex-scan.txt`):** across all corpus APKs, **only the Termux
  family hardcodes `/data/data/<pkg>/files`** — `com.termux` and `com.termux.api`. Every other app uses
  `getFilesDir()` (already fixed). So the fix moves **termux** (+ `com.termux.api` if it is ever a run key); no other
  key regresses or benefits.

## Method / rules
- `compare.py` imports `u16-wall-clusters/collect.py` and reuses its helpers verbatim. **Lit is only ever the
  sign-off `summary.gains`/`reference`/`outer_eyeball` (screenshot), never the `lit_runs` pre-screen field** (the
  errata). Signals are identified by the thread-correct crashing frame from `first_fatal`'s fault-thread report
  (build-id + `+offset` stripped), because `cluster_key` leaves the frame empty for signals and the bare `signo` line
  is identical across every SIGSEGV; a `pc=0`/"Not mapped" top frame is kept as the Impeller signature. The shared
  `earliest_wall` (`DisplayManagerProjectionProxy.dispatchDisplayEvent`) is benign context, not the fatal.
- **moved** = U14 terminal identity differs from the U13 window-1 run's; **unchanged** = same; **lit** = sign-off gain.
- Window 2 (`u14-A2-20261003T131427`, cx-t0) is still running; re-run `compare.py` after its sign-off to fill
  fd-AppManager and add any second-board runs.

## Files
- `compare.py` — the comparison + re-clustering (imports the U16 wall-cluster stack; lit from `summary.gains`).
- `predicted-vs-actual.json` — per-key rows (prediction, u13-before, u14-actual signature + facts, lit, verdict) + the
  new-wall buckets. `u17-candidates.csv` — the ranked U17 table. `evidence/datadata-dex-scan.txt` — the corpus
  `/data/data/<pkg>` hardcode scan.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board, no deploy, no push. Lit/not is the outer's window-1 sign-off screenshot (`summary.gains`/
`outer_eyeball`); alive counts are the run `facts.txt`. The U17 table is a prediction over the window-1 runs; window-2
and the on-board screenshots refine it. No fix is built here — this is the predicted-vs-actual read that feeds the U17
plan (the termux bootstrap fix is a sandbox-config change for the outer/cx-bms).
