# page-bizzle `app_failed` in the U8 sweep = a cold-desktop capture race at run start (tool layer)

**Verdict (evidence-first):** `cv2-com-page-bizzle`'s `app_failed` in the U8 full sweep is a **tool/harness**
failure — bms searched for the desktop icon while sceneboard's app-grid desktop had not finished loading at the
**start of the run** — **not** an install, icon-conversion, or runtime defect of the app. The app installed fine
and has a valid launcher ability and a real raster icon; it was simply never clicked because the desktop was empty
in every dump taken during its window.

Run: `westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-cv2/20261001T122027-e3c3b085`.

## What `record.json` says
```
status: app_failed ; error: "exact desktop icon absent across searched pages" ; clicked: false
package: com.page.bizzle ; desktop_activity: com.page.bizzle.MainActivity
bms: {return_code: 0, queryable: true}        # install + bm dump both succeeded
install.txt: "install bundle successfully."
```
So the app **installed**; it failed at the desktop-icon-click step. `bms_batch.select_icon` (bms_batch.py:46,283)
searches the dumped layout for a node id starting with `AppIconCommonView_com.page.bizzle.`; finding none across
the searched pages raises `exact desktop icon absent across searched pages` (bms_batch.py:555).

## Why the icon was "absent": the dumps captured a tile-less desktop
- The bundle is **launchable**: `bundle.txt` has an ability with `isLauncherAbility: true`,
  `ohos.want.action.home` + `android.intent.category.LAUNCHER`, `visible: true`.
- The icon is a **real raster**: `aapt2 dump badging` → `application: icon='res/_X.png'` (a PNG at a compiled path,
  app package `0x7f`) — not a vector/adaptive icon, so this is **not** the frequent-habits XML-only case.
- Yet **all 20** of page-bizzle's page dumps (`icons-1-0..9`, `icons--1-0..9`) contain **0** `AppIconCommonView_`
  tiles and **0** `SCBDesktop` markers; the only window captured is `com.ohos.sceneboard WindowScene` (a non-app-grid
  scene). So there was no tile to match — the desktop app grid was not present in the capture.

## The desktop *did* have tiles — proof from run-siblings + run order
Sorting the run's keys by dump mtime (`settle-0.json`) against status and tile count:
```
12:20:37  app_failed            tiles=0    cv2-com-page-bizzle            <- run key #1
12:22:14  app_failed            tiles=0    cv2-com-trianguloy-clipboardeditor  <- key #2 (dumpLayout also failed)
12:22:48  foreground_unconfirmed tiles=228 cv2-com-zola-bmi               <- key #3: desktop now loaded
12:23:43  foreground_unconfirmed tiles=230 cv2-com-notecryptpro
 …        foreground_unconfirmed tiles=196..266  (grows as more apps install)
```
The run started `12:20:27`. **Only the first two keys** (the first ~2 minutes, before sceneboard finished building
the app grid after the U8 overlay apply) failed with tile-less dumps; from key #3 on the desktop carried 196–266
tiles and every app clicked. page-bizzle was simply the **first** key, dumped 10 s into the run against a desktop
that was not ready.

## Layer classification (tool / install / runtime)
- **Install:** OK — `install bundle successfully`, `return_code 0`, queryable, launcher ability present + visible.
- **Icon conversion:** OK — a real PNG icon; and the `AppIconCommonView_` scheme works for 100+ sibling tiles in
  the same run, so the icon pipeline is not implicated.
- **Runtime (app):** not reached — the app never launched; there is no app crash.
- **→ Tool / harness (desktop-not-ready at run start):** bms issued the icon search while sceneboard's app-grid
  desktop was still loading; it faithfully captured a tile-less scene and correctly reported "absent", but the
  cause is a cold-desktop race, not page-bizzle.

## Not the same as the other 3 "desktop icon absent" keys
The U8 sweep has 4 keys with this exact error; the dumps split them into **two** root causes:
- **page-bizzle** (and clipboardeditor): **tile-less capture** (0 `SCBDesktop`, 0 tiles) at run start → this
  cold-desktop race.
- **frequent-habits, privacyfriendlypasswordgenerator** (, wifianalyzer): captured a **populated** desktop
  (700+ `AppIconCommonView_` tiles, 160 `SCBDesktop`) with their **own** tile genuinely absent — a separate, real
  launcher-placement question (e.g. frequent-habits' `com.example.*` launcher-activity namespace vs its
  `com.frequent.habits` package), to be investigated on its own.

## Fix direction (harness, not this lane)
`board_run.py` / `bms_batch.py` should gate the **first** icon search on desktop readiness: press HOME and poll
until a dump contains `SCBDesktop` / `>0 AppIconCommonView_` tiles before searching, and classify a tile-less dump
as `desktop_not_ready` (retry) rather than `app_failed`. That would have rescued both run-start casualties
(page-bizzle, clipboardeditor) without a per-app change.

Evidence: `results.json` (this dir). Offline only; no board touched.
