# Demo-baseline t2: Toutiao route choice by offline conflict + cost comparison (cc-t3, #91)

Contract: `specs/demo-baseline/t2-toutiao.spec.md` (scenario `demo_baseline_toutiao_route`). Static, offline, **zero
on-board**. This picks which of two routes to take to a spare board first, by listing — **from files** — every path,
process, package and ability each route writes, tabulating every conflict with evidence, and choosing the route that
changes the fewest files and touches no frozen item.

## What was wrong before / the rule this sets

- **The Sept demo and the #90 campaign are two different toutiao mechanisms, and that was never written down side by
  side.** The persistent Sept demo ran toutiao **embedded in an OH host HAP** (`org.westlake.imehost`, writing only
  `/data/local/tmp`, interactive on 5cd — DIGEST 113/329/337). The #90 unified state runs toutiao as a **BMS-installed
  Android app** (`com.ss.android.article.news`) under the shared route-a runtime, where it dies at the `libtttext_lite.so`
  ICU walls (DIGEST 711/717). Calling one "the route" hid that they share on-board paths.
- **Rule**: a route decision must list both routes' deployed paths/processes/packages/abilities from files, name every
  shared path as a conflict with its evidence line, and pick by (fewer files changed, reversible, no frozen item) — not by
  which one we remember working.
- **Rule (verified, not remembered)**: the ttbundle on this Mac is **6/7, not 7/7** — `tt-rt.tar` is absent
  (`shasum -c` → `tt-rt.tar: FAILED open or read`, `evidence/ttbundle-manifest.txt`). The spec's "MANIFEST 7/7" is the
  manifest's claim, not the bundle's on-disk state. Any Route-B plan must refetch and verify `tt-rt.tar` first.

## Route A — current "原包" route (BMS-installed Android app on the unified state)

Deployed facts (from files):
- **Package / ability**: `com.ss.android.article.news`, launched as an Android app via the route-a bridge; no OH host HAP.
- **Runtime**: the unified-state route-a runtime; on this OH6.1 board the live ART is `/data/local/tmp/asx/libart.so`
  (bind-mount, inode 321048 — DIGEST 83), app namespaces configured by `libapp_native_loader` (`ANL_Dlopen`, route-a
  74d1d6d4).
- **Walls** (why it is not interactive today):
  - **Wall 0 (install, board-specific)**: toutiao's 137 arm64 libs include `libcvt.so`, which only **61b**'s
    `libinstalls 51e1b525` accepts via a reviewed-payload exception; **5ea/5cd**'s `libinstalls 2c9a5294` rejects it
    (`install internal error`, ELF/CRC verification failed) — `benchmark/2026-10-02-toutiao-wall3-prediction`. So under
    Route A the demo board is effectively pinned to 61b unless the installer split is unified.
  - **Wall 1 (ICU namespace)**: `westlake.anl.app` namespace carries **no AOSP public-lib table** —
    `app_native_loader.c create_configured_namespaces` passes only the app path + bridge soname, so `libicui18n.so` is
    `ENOENT` (`namespace=westlake.anl.app.*, errno=2`) even though the file is present (DIGEST 717). Same family blocks
    `libGLESv2` (fd-stk), `libGLESv3` (subwaysurfers), `libjnigraphics`.
  - **Wall 2 (ICU data version)**: `libtttext_lite.so` `brk_open` does `scandir("/system/usr/icu")`, takes the **max**
    `icudt<NN>l.dat`, and `dlsym`s `ubrk_open_<NN>`. The OH board ships `icudt74l.dat` there → it wants `ubrk_open_74`, but
    our Android ICU only exports `_72` → `ICUWrapper::ICUWrapper()+100` SIGSEGV after bind returns (~21 s), DIGEST 711/717,
    `benchmark/2026-10-02-toutiao-longwait-cxt0`.

## Route B — "旧路线" ttbundle (`~/a2hlab-provision/ttbundle`, host-embed)

Deployed facts (from files — `evidence/routeB-*.txt`):
- **Host HAP**: `org.westlake.imehost` (module.json: stageMode, `EntryAbility` with `action.system.home`, versionCode 2,
  requests `ohos.permission.INTERNET`). Sandbox `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bf…`.
- **Android child**: `com.ss.android.article.news` (request.bin / watchdog PKG) — the **same** toutiao package, launched
  inside the imehost window.
- **Staging bins** (`/data/local/tmp/a2hlab-app-c91d26bf…/`): `source_app_namespace` (the spawner, uid 20010053),
  `host_spawn` (abstract socket `A2HSourcec91…`), `request.bin`; parent spawns `/data/local/tmp/asx/run.sh`.
- **Working dir**: `watchdog.sh` (guardian + selfheal under `/data/local/tmp/operator45*`), `start-parent.sh`, `spawn.sh`,
  `screen-gate`, `onscreen_keeper.sh`.
- **AOT**: prebuilt `aot/toutiao.{art,odex,vdex}`.
- **Missing**: `tt-rt.tar` (runtime layer) — NOT on this Mac. Because the launch script runs the **existing**
  `/data/local/tmp/asx/run.sh` (the unified route-a runtime mount, DIGEST 83), Route B as-archived is designed to **reuse
  the board's unified runtime**, not ship its own — consistent with the spec's "与当前路线共存". `tt-rt.tar` was the
  fresh-board runtime seed; on a board already in the unified state it is not strictly needed, but must be refetched to
  verify what, if anything, it would overwrite.

## Item-by-item conflict table (Route B's writes vs the current unified route)

| # | Route B writes / starts | Current unified route (A) | Conflict? | Evidence |
|---|---|---|---|---|
| 1 | HAP `org.westlake.imehost` (el2/100 sandbox) | installs toutiao as `com.ss.android.article.news`; **no imehost** in U14 composition | **No bundleName collision** — additive host HAP | `evidence/current-route-no-imehost.txt`; module.json |
| 2 | `/data/local/tmp/a2hlab-app-c91d26bf/` (source_app_namespace, host_spawn, request.bin) | route-a uses `/system/bin/appspawn-x` | **No** — `/data/local/tmp` only, additive. RUNBOOK warns `rm -rf /data/local/tmp/a2hlab-app-*` breaks it (DIGEST 337) | `start-parent.sh`, `spawn.sh` |
| 3 | `/data/local/tmp/asx/run.sh` (launched by the spawner) | **`/data/local/tmp/asx/` IS the live route-a runtime** (`libart.so` inode 321048; `lib/arm64-v8a/` overlay) | **SHARED PATH — must confirm B drops in a `run.sh` and does NOT overwrite `asx/libart.so` or `asx/lib`** (which the 100 unified apps use) | DIGEST 83/14/230 |
| 4 | Android child `com.ss.android.article.news` + prebuilt AOT | route-a would run the same package via BMS install + its own oat | **Same Android package** — do not install both; B's host-embed path replaces the BMS install of toutiao, not adds a 2nd | request.bin; `aot/` |
| 5 | `aot/toutiao.{art,odex,vdex}` into the app dalvik-cache | boot image via the **frozen dex2oat-once toolchain** | **No** — app-level AOT, not the boot image; does not touch the frozen toolchain | MANIFEST `aot/`; frozen.json `dex2oat-once` |
| 6 | `tt-rt.tar` runtime layer | unified `/data/local/tmp/asx` runtime (a specific generation's SHAs) | **UNKNOWN — missing from the bundle.** If refetched and it ships an older libart, dropping it into `asx/` would regress the 100 unified apps; if it is runtime-less staging, no conflict | `evidence/ttbundle-manifest.txt` (SHA FAIL) |
| 7 | `watchdog.sh` selfheal under `/data/local/tmp/operator45*` | route-a selfheal state is also `/data/local/tmp/operator45/selfheal48` | **SHARED selfheal path** — two guardians on one lock dir; confirm B's single-supervisor lock does not fight route-a's | RUNBOOK 75; `watchdog.sh` |
| 8 | `imehost0` host window + `action.system.home` launcher ability | SceneBoard; route-a apps draw directly | Additive launcher/home ability + host window; ZOrder vs `SCBScreenLock` (onscreen_keeper handles) | DIGEST 338/329 |

**Real conflicts to clear on a spare board: #3, #6, #7** (shared `/data/local/tmp/asx` runtime, missing+unknown
`tt-rt.tar`, shared `operator45` selfheal). **#4** is a design choice (host-embed replaces the BMS toutiao install, not a
collision). #1/#2/#5/#8 are additive, no conflict.

## Route A ICU-wall cost estimate (files to change)

| wall | minimal fix | files changed | /system? | frozen? |
|---|---|---|---|---|
| Wall 1 (ns public-lib table) | add AOSP public libs (`libicui18n`, `libGLESv2/v3`, `libjnigraphics`) to the `westlake.anl.app` namespace in `app_native_loader` → rebuild `libapp_native_loader.so` (single lib, swap-back reversible) | **1** deployed lib | yes (route-a lib) | **not in frozen.json** (no entry names app_native_loader/ICU) — still single-variable/ABI-recompile governance applies |
| Wall 2 (ICU data version) | `libtttext_lite` scandir picks `max NN` in `/system/usr/icu`; our Android ICU exports `_72` but OH ships `icudt74l.dat`. No clean single-file fix: either add an Android `icudt≥74l.dat` **and** export `ubrk_open_≥74` (ICU rebuild + data), or divert `/system/usr/icu` (OH's own ICU, **shared with the OH system** — high blast radius) | **2+** (ICU lib export + data file), one touching OH-shared `/system/usr/icu` | yes (OH-shared) | not a listed frozen entry, but OH-shared `/system/usr/icu` risks OH itself |

Route A clears a useful **class** at wall 1 (libGLESv2/v3/jnigraphics for other keys), but wall 2 is the expensive,
OH-shared half with no proven single-file fix.

## Decision

**Primary: Route B (host-embed ttbundle overlay), gated on three spare-board checks. Fallback: Route A wall-1-first.**

By the stated criterion — **fewer files changed, reversible, no frozen item** — Route B wins the static comparison:
- **Fewest files**: Route B changes **0 source/`/system` files** — it is an additive overlay (1 HAP install + ~8 files
  into `/data/local/tmp` + app-level AOT). Route A rebuilds ≥2 deployed `/system` libraries, one touching OH-shared
  `/system/usr/icu`.
- **No frozen item**: Route B touches **no** frozen.json entry (app-level AOT ≠ the frozen dex2oat-once boot image;
  no `/system` write). Route A's walls are not *listed* frozen entries either, but wall 2 edits OH-shared `/system/usr/icu`.
- **Reversible**: Route B rolls back by uninstalling the `org.westlake.imehost` HAP and `rm`-ing its `/data/local/tmp`
  dirs — no fingerprint change to the unified state. Route A requires swapping deployed `/system` libs back.
- **Proven**: Route B was interactive on 5cd (DIGEST 113/337); Route A has never been interactive (always dies at the ICU
  wall).

**Gating on-board checks before Route B is accepted** (next scenario, spare board, with rollback script per the spec):
1. **Refetch + verify `tt-rt.tar`** from hw248 against the MANIFEST SHA `014c566e…`; diff its payload against the live
   `/data/local/tmp/asx` to prove it does **not** overwrite the unified `libart.so`/`lib` the 100 apps use (conflict #3/#6).
2. **Coexistence**: with B overlaid, relaunch ≥10 previously-lit unified keys — all must stay lit by t20, else roll back
   (spec scenario 3). Confirms B reuses, not replaces, the unified runtime and the `operator45` selfheal (conflict #7).
3. **Both ICU walls actually cleared under B**: confirm `source_app_namespace` gives toutiao a namespace that sees
   `libicui18n` (wall 1) **and** that `libtttext_lite`'s `ubrk_open_<NN>` resolves under B (wall 2) — i.e. B's host-embed
   path sidesteps the walls route-a hits. If wall 2 still fires under B (B ships no ICU data), Route B does not actually
   solve toutiao and we fall back.

**Fallback = Route A, wall 1 first**: if any gate fails, do the single-lib `libapp_native_loader` namespace-table fix
(cheap, reversible, class-positive) on the unified state, and escalate wall 2 (OH-shared ICU) to the outer as a separate,
higher-risk decision. This keeps toutiao on the *same* unified state as the 100 apps — the campaign's hard requirement —
at the cost of the wall-2 ICU work.

## Files
- `evidence/ttbundle-manifest.txt` — MANIFEST + on-Mac presence + `shasum -c` (shows `tt-rt.tar` missing).
- `evidence/routeB-footprint.txt` — B's on-board paths/processes from its own scripts.
- `evidence/routeB-hap-module.txt` — imehost HAP bundleName/ability/permissions.
- `evidence/current-route-no-imehost.txt` — current U14 composition has no imehost HAP (additive, no collision).
- `results.json` — machine-readable route comparison + decision.
