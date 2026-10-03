# U15 stage-A alias-theme regression watchlist: an alias-theme fix is a *splash*-theme fix

#90, offline, no board. cc-t3's U15 runtime JAR v1 makes every themeless `<activity-alias>` launch inherit
the **target** activity's theme (AOSP behaviour; the fd-api AppCompat fix generalised — see
`benchmark/2026-10-03-u15-fdapi-theme`). This lists the **other** alias-launch keys besides fd-api, and for
each says **what the t20 screenshot should be** after the swap, so the stage-A U15 run can tell a real
regression from an expected no-change. (`evidence/alias-theme-map.txt` = the per-key theme map;
`evidence/baseline-shots.txt` = the current t20 ground truth; `watchlist.csv` = the machine-readable table.)

## What the fix does, and the one finding that drives every verdict
AOSP: an alias with no `android:theme` inherits the **target** activity's theme. route-A instead falls a
themeless alias back to the **application** theme (`AppSchedulerBridge:793`
`if (ai.theme==0 && appInfo!=null) ai.theme=appInfo.theme`). The deployed U13 JAR already *logs* the target
theme via `[B8-ALIASTHEME] "<target> theme re-resolved X -> Y"` but does **not** apply it; U15 JAR v1
**applies** it (`launch.theme = Y`).

**Finding:** across the 10 keys where `Y != X`, **every `Y` is a splash theme** —
`AppTheme.Splash` / `SplashTheme` / `MwmTheme.Splash` / `SplashScreenThemeBase` / `Theme.Vector.Launcher`
(`aapt2 dump resources`). These apps declare the Android-12 SplashScreen pattern on the launched component:
the launcher component carries a splash theme, and the app calls `installSplashScreen()`/`setTheme()` after
the first frame to swap to its real UI theme. **So the fix governs the pre-content (splash) window, not the
steady-state.** A lit key's **t20 is past the splash → unchanged**; the swap only affects the first ~0.5–1 s.

## The set (swept all 231 stage-A hilogs; `[B5-ALIAS] ordinary=false` = a real alias launch)
**14** alias launches. **10 change theme** (`X!=Y`), **4 are no-ops** (`X==Y`). "Others besides fd-api" that
change = **9**. cc-t3's dispatch says **8**; the +1 is **fd-fennec_fdroid** (Firefox) — it dies
*before bind* (`libmozglue.so` ULE), so the theme is never applied at runtime; excluding it gives exactly the
8 that reach the window and change: wikipedia, fd-notes, fd-calendar, fd-filemanager, fd-gallery,
fd-musicplayer, fd-organicmaps, fd-im-vector-app. We report the measured 9 and flag fennec so cc-t3 can map
to its own count — the per-key verdict is the same either way.

## Watchlist — which t20 shot should be what (★ = baseline screenshot READ this round)
| key | theme was → now | U13 t20 (baseline) | expected t20 after U15 fix | flag |
|---|---|---|---|---|
| **fd-api** (driver) | DeviceDefault → `AppCompat` | home/crashed (AppCompat ISE) ★ | **Termux:API UI renders** (crash cleared) | **POSITIVE — the fix target**, lit likelihood medium |
| **wikipedia** | `AppTheme` → `AppTheme.Splash` | **LIT** onboarding (globe + 全世界的知识) ★ | **UNCHANGED** lit onboarding | WATCH: not stuck on splash |
| **fd-notes** | `AppTheme` → `SplashTheme` | **LIT** notes editor ★ | **UNCHANGED** lit editor | WATCH: not stuck on splash |
| **fd-calendar** | `AppTheme` → `SplashTheme` | **LIT** month view (十月) ★ | **UNCHANGED** lit month view | WATCH: not stuck on splash |
| **fd-filemanager** | `AppTheme` → `SplashTheme` | LIT (0-protection) | **UNCHANGED** lit file list | WATCH: not stuck on splash |
| **fd-gallery** | `AppTheme` → `SplashTheme` | LIT (0-protection) | **UNCHANGED** lit gallery grid | WATCH: not stuck on splash |
| **fd-organicmaps** | `MwmTheme` → `MwmTheme.Splash` | LIT (0-protection; map drew) | **UNCHANGED** lit map/first-run | WATCH: not stuck on splash |
| fd-musicplayer | `AppTheme` → `SplashTheme` | home/crashed (Bitmap colorspace IAE) ★ | **UNCHANGED** home/crashed | NEUTRAL: blocked by **Bitmap** wall (U15 #1), not theme |
| fd-im-vector-app | `Theme.Vector.Light` → `…Launcher` | dead (bind-fail Realm `_ctype_`) | **UNCHANGED** dead-at-bind | NEUTRAL: dead before window (needs U15 compat v3 / native_abi v2) |
| fd-fennec_fdroid | `NormalTheme` → `SplashScreenThemeBase` | dead (fatal-before-bind `libmozglue.so`) | **UNCHANGED** dead-before-bind | NEUTRAL: dead before window (needs U14 native_abi) |
| fd-uhabits | `AppBaseTheme` *(unchanged)* | LIT (lottery) | **UNCHANGED** (no-op) | CONTROL: any t20 change = **bug** |
| fd-tasks | `Tasks` *(unchanged)* | LIT (lit-regression) | **UNCHANGED** (no-op) | CONTROL: any t20 change = bug |
| fd-libretube | `SplashScreenTheme` *(unchanged; alias has own theme)* | additional run | **UNCHANGED** (no-op) | CONTROL: any t20 change = bug |
| cv2-…photophase | `0x7f1100b2` *(unchanged)* | LIT (0-protection) | **UNCHANGED** (no-op) | CONTROL: any t20 change = bug |

### The three groups, in words
- **Watch-lit (wikipedia + Fossify notes/calendar/filemanager/gallery + organicmaps):** already lit; the swap
  makes the **splash** correct, not the steady UI. t20 **must stay the same lit screen**. The **only**
  regression this fix can introduce here is a **stuck splash** — if a key's t20 now shows the splash drawable
  (`SplashTheme`/`AppTheme.Splash`/`MwmTheme.Splash`) instead of its real UI, the route-A splash-dismiss broke
  under the newly-applied splash theme. That is the shot to scrutinise.
- **Neutral (fd-musicplayer, fd-im-vector-app, fd-fennec_fdroid):** blocked by an **upstream** wall
  (Bitmap-colorspace / Realm `_ctype_` / mozglue). The theme fix does not light them; for Element and Firefox
  the theme is never even reached (dead before the window). t20 **unchanged**.
- **Control (fd-uhabits, fd-tasks, fd-libretube, photophase):** `X==Y`, so the fix is a **literal no-op**.
  t20 **must be byte-identical** — these are the canaries: any change here means the fix is doing something it
  shouldn't (e.g. clobbering an already-correct theme).

## What was wrong before / what this round fixes in our reading
The dispatch framed the fix as "these keys **change to the target theme**", which reads like "their screen
changes". The data says the opposite for the lit keys: the target theme is a **splash** theme the app
discards after one frame, so **t20 does not change** for a key that reaches its UI. Reading it as "new
screen" would have mislabelled an expected no-change as a pass, or (worse) read a stuck-splash regression as
"the fix working". The watchlist pins the correct expectation per key.

## This round's rule
An alias-theme fix is a **splash-theme fix**: every target theme it applies is the launcher component's
Android-12 splash theme, dismissed after first frame. Judge a **lit** key's t20 as **unchanged** (watch only
for a *stuck-splash* regression); the **only** t20 that should actually improve is the one whose wall **was**
the theme (fd-api). Keys blocked by an upstream wall don't move, and theme-unchanged keys are the control
that must stay byte-identical. Confirm against the `[B8-ALIASTHEME] X->Y` log and the `aapt2` theme name
(is `Y` a `*.Splash`/`Splash*` style?), not against the dispatch's key count.

## Files
- `evidence/alias-theme-map.txt` — all 14 alias launches: alias→target, X→Y with theme **names**, changed vs
  no-op, the cc-t3 "8 vs 9" reconciliation, and the verbatim `[B5-ALIAS]`/`[B8-ALIASTHEME]` source lines.
- `evidence/baseline-shots.txt` — current t20 ground truth per key (5 shots read), run-group buckets, and the
  not-lit keys' first-fatal wall layer; screenshot paths ($WORKSPACES-normalised).
- `evidence/corpus-alias-scan.txt` — the static universe: 16 launcher-alias apks / 14 themeless (aapt2 scan).
- `watchlist.csv` — machine-readable per-key expected-t20 + regression flag.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push; **static + screenshot-read only** — no on-board U15 run. The t20 predictions are
to be **confirmed by the stage-A U15 run** (screenshots = ground truth per AGENTS.md); where a baseline shot
was not read, the lit/unlit call is the runner's pre-classification bucket, flagged as such. The "8 vs 9"
is cc-t3's bookkeeping to settle. Sources read read-only: the U13 stage-A hilogs + t20 jpegs
(`westlake-harness-u7-executor`), the app apks (`westlake-inputs/apks`), the first-fatal clusters
(`westlake-harness/benchmark/2026-10-03-u13-first-fatal-clusters`), the adapter source (`westlake-harness/bms`).
