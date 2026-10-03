# U14 readout: per-mover expectations + an auto first-fatal/z-order reader for the window run

#90, offline, no board. Goal: **speed the outer's U14 Stage-A verdict.** When the U14 window shards land, the
outer should not hand-read 24 hilogs. This ships (a) `expectations.csv` — for each of the **24 U14 movers**, what
t20 should look like and where the hilog first-fatal should move when the fix lands; and (b) `recipe/readout.py` —
point it at a U14 window run dir and it auto-extracts each mover's first-fatal / dialog z-order (reusing
`scripts/lab/{first_fatal,bind_status,dlopen_failures}.py`) and prints a **match / moved-past / unchanged /
moved-elsewhere** table against the expectations. Window shards are not out yet, so it is **self-tested on the U13
Stage-A window dir** (known answer: every mover is still at its pre-fix state → all `unchanged`).

## The 24 movers split into two axes (not one)
The task frames all movers as "first-fatal moves", but **14 of them never terminate** — they are already lit; the
M5 fix only changes **z-order**, not a crash point. Treating them on the first-fatal axis would mis-read them
(their `first_fatal.terminal` is `null`). So `expectations.csv` tags each mover with an `axis`:

| axis | n | keys | what the fix changes | how `readout.py` reads it |
|---|---|---|---|---|
| **zorder** | 14 | 13 M5 watchlist keys + `dddmodel2` (cluster G) | onCreate dialog rises **above** the activity window | `createSession androidType` + `UpdateZOrderInner` from hilog: dialog_z vs activity_z (DIGEST 690/714/721) |
| **first-fatal** | 10 | Flutter A×4, C×2, D×2, I toutiao, J fd-plus | the first fatal moves **past** the pre-fix wall | `first_fatal.py` terminal+root, corroborated by `bind_status` + `dlopen_failures --near-fatal` |

## Per-mover expectations (full table is `expectations.csv`; sources cited per row)
**z-order (cluster G, 14 keys)** — pre-fix (U13+M1): `dialog_z < activity_z` (dialog created first, pressed under
the main window, DIGEST 690: dddmodel2 686→102 < 687→103). **Post-M5 expected:** `dialog_z > activity_z`, app
stays alive (terminal null). **t20:** the app's own dialog on top of its own main UI, still lit (per
`2026-10-03-u14-m5-watchlist/watchlist.csv` `predicted_post_m5_t20`). dddmodel2 was white on U13 w/o M5; M1 is in
the U14 runtime so the lifted dialog has a Surface (DIGEST 721 erratum — M5 ships with M1).

**first-fatal (10 keys)** — pre-fix wall → expected post-fix wall (markers are failure/crash-anchored):

| key | cl | pre-fix first-fatal (U13) | expected post-fix move | expected t20 |
|---|---|---|---|---|
| localsend, fd-kitchenowl, fd-fluffychat, fd-libre | A | SIGSEGV at `libnativewindow ANativeWindow_getFormat` via `eglCreateWindowSurface` (EGLSurface=0; DIGEST 450/733) | past eglCreateWindowSurface → `EGLSurface=<non-zero>`, then signal 11 pc=0 `libflutter.so+0x4b655c` = Impeller GLES proc NULL (DIGEST 762/268); **libre** may hit libmpv→libmediandk instead | still NOT lit (deep wall; first-fatal only moves) |
| mcdonalds, fd-im-vector-app | C | bionic `_ctype_` symbol-not-found relocating Realm native lib (`librealmc.so`/`librealm-jni.so`) → bind fails | past the Realm load (u14-native-abi-v2 f8619ad5) | past Realm; next wall app-specific |
| vlc | D | bionic `__pthread_cleanup_push` not found (libvlc.so) | past the symbol (u14-native-abi-gecko 7605812c; **medium** — other libs not replayed) | past symbol; next wall unknown |
| fd-fennec_fdroid | D | bionic `__gnu_strerror_r` not found (libmozglue.so) | past the symbol (**high** — replay 0 missing) | past symbol |
| toutiao | I | app-ns `load libicui18n.so failed` (errno=2) then SIGSEGV (ICU 74 vs 72) | both ICU walls removed (ICU alias + app-ns public libs); feed risk stays | past ICU; may reach feed |
| fd-plus | J | `NoClassDefFoundError: android.bluetooth.le.ScanCallback` at bind | bind passes initPlugins (stub 87cf65cc) → `handleBindApplication returned OK` | bind completes; past plugin init |

## `recipe/readout.py` — one command over a window dir
```
readout.py <window-run-dir> [--json out.json] [--key KEY ...] [--repo /path/to/westlake-harness]
```
It rglobs `record.json` (keying by `record["key"]`, since runner dirs are nested), and per mover:
- **first-fatal axis:** `first_fatal.py` → terminal kind + root symbol; `dlopen_failures.scan(--near-fatal 3)` →
  near-fatal libs; `bind_status.scan` → bound/bind_failed/fatal_before_bind; then tests the row's
  failure-anchored `prefix_marker` / `postfix_marker`.
- **zorder axis:** parses `createSession androidType`→`UpdateZOrderInner` for the app's sessions → dialog_z vs
  activity_z, plus terminal (must stay null).
- **verdict:** first-fatal → `unchanged` (pre-fix wall still the fatal) / `match` (post-fix marker present) /
  `moved-past` (pre-fix gone, cluster's next wall is app-specific so no positive marker — success for C/D/I) /
  `alive-no-fatal` / `moved-elsewhere`. zorder → `match` (dialog_z>activity_z, alive) / `unchanged`
  (dialog_z<activity_z) / `regression-fatal` / `no-data`.

## Live U14 readout (window1 iteration `u14-A1-r3-20261003T120358`, snapshot while the window was still running)
Ran against the real U14 shards as they landed (`evidence/u14-window1-r3-readout.{txt,json}`). **23 of 24 movers
read as the fix predicted:**
- **All 14 M5 z-order movers → `match`** — the dialog now paints ABOVE the activity (e.g. dddmodel2 dialog_z=103 >
  activity_z=102; the exact inversion of the U13 102<103). M5 is working on every M5 key that ran.
- **Flutter localsend / fd-kitchenowl / fd-fluffychat → `match`** — `ANativeWindow_getFormat` is gone and
  `EGLSurface=<non-zero>` is present (localsend `EGLSurface=0000007EFBD36550`), crash now inside `libflutter.so`
  (the Impeller wall, DIGEST 762). The EGL interposer landed.
- **C mcdonalds / fd-im-vector-app → `moved-past`**, **D fd-fennec_fdroid → `moved-past`** — the `_ctype_` /
  `__gnu_strerror_r` relocation walls are gone. **D vlc → `alive-no-fatal`** (past `__pthread_cleanup_push`, bound,
  no fatal at capture — further than predicted). **J fd-plus → `match`** (bind OK, no ScanCallback).
- **fd-libre → `unchanged`** — the ONE Flutter key the EGL fix did NOT move: it still crashes at
  `libnativewindow ANativeWindow_getFormat+60` (no non-zero EGLSurface) plus a separate `fdsan_close_with_tag`
  crash. This matches clusters.csv A's lower-confidence note on libre and is the row the outer should look at.
- **toutiao → `no-run`** (its shard had not landed at snapshot time; re-run readout when it does).

**Run readout per ITERATION subdir, not over the whole plan dir.** A U14 window has several iterations
(`u14-A1-20261003T110222`, `…-r2-…`, `…-r3-…`); pointed at the plan root, `readout.py` takes the first run per key
and can mix a pre-fix r2 run with a post-fix r3 run. Point it at the latest iteration (here `…-r3-…`) for a
consistent readout.

## What was wrong before, and the rule this round
**The trap we did NOT fall into:** the "wall" tokens are benign-recurring. A global grep of each U13 mover hilog
shows `ICU` ×12, `eglCreateWindowSurface` ×6, `Impeller` ×2, `UnsatisfiedLinkError` ×1 **in every run** — none of
those is the wall (the DIGEST-762 lesson: a smoke/marker regex written loosely judges a working fix as FAIL, or a
pre-fix run as fixed). So readout anchors the first-fatal to `first_fatal.py`'s terminal selection and only tests
**failure/crash-anchored** markers (`ANativeWindow_getFormat\+`, `s=_ctype_`, `load libicui18n.so failed`,
`android/bluetooth/le/ScanCallback`), never the bare token.

**A real bug the negative control caught:** an earlier cluster-C marker `_ctype_|librealm-jni` matched a synthetic
`librealm-jni loaded OK` success line (and mcdonalds actually uses `librealmc.so`, not `librealm-jni`). Tightened
to `s=_ctype_ | _ctype_: symbol not found` (the relocation-failure signature). **Rule:** a wall marker must match
the *failure* line, not the library/class name — validate it with a post-fix negative control, not just a pre-fix
run.

**A second bug the live U14 window caught (marker FORMAT):** the Flutter post-fix marker was first written
`libflutter\.so\+0x4b655c`, copying the DIGEST's shorthand. The real DfxFaultLogger frame is
`#01 pc 00000000004b655c /…/libflutter.so(<build-id>)` — no `+0x`, and the Impeller `pc` offset is
**build-specific** (localsend `0x4b655c`, kitchenowl `0x4c367c`). So the shorthand marked a working fix as
`moved-elsewhere`. Fixed to `EGLSurface=0*[1-9A-Fa-f]` — the non-zero EGLSurface line, which is DIGEST 762's own
smoke marker (it explicitly warns the pointer has NO `0x` prefix, e.g. `EGLSurface=0000007F15F9F430`). This is the
same DIGEST-762 trap in a new place: do not hard-code a hex format or a build-specific offset into a marker.

## Verification (evidence/)
- **Self-test on U13** (`evidence/u13-selftest.{txt,json}`, source `evidence/u13-selftest-source.txt`): all **24
  movers → `unchanged`**. z-order movers show `dialog_z < activity_z` (dddmodel2 102<103, = DIGEST 690);
  first-fatal movers show `pre=True post=False` with the real terminal (signal / main_threw / process-disappeared /
  bind_failed) and corroborating bind status + near-fatal libs. That is the correct known answer — U13 predates
  every U14 fix — and proves the extractor works on both axes.
- **Negative control** (`evidence/synthetic-postfix/`): synthetic post-fix hilogs flip the verdicts — localsend
  (`libflutter.so+0x4b655c`, no ANativeWindow_getFormat) → `match`; ath0-rpn (dialog_z 103 > activity_z 102) →
  `match`; fd-plus (`handleBindApplication returned OK`, no ScanCallback) → `match`; mcdonalds (Realm loads, app
  dies later at a signal) → `moved-past`. Proves the classifier is not stuck on `unchanged` and the markers
  discriminate.
- `evidence/extractor-interfaces.txt`: the confirmed JSON shapes of the three reused tools.

## Boundaries
Offline; no board, no deploy, no push. Expectations are predictions sourced from the outer-reviewed
`u16-wall-clusters/clusters.csv` (A/C/D/I/J), `u14-m5-watchlist/watchlist.csv` (G), and DIGEST 450/690/714/721/733/762
+ entry 268 — **the board screenshot (`snapshot_display`) remains ground truth** for t20 (AGENTS 判定). readout.py
is a triage accelerator over the window hilogs; it does not replace the outer's sign-off. When the U14 shards land,
run it per window dir and read the `match`/`moved-past` rows first.

## Files
- `expectations.csv` — 24 movers: key, board, axis, cluster, source, confidence, prefix_wall,
  postfix_wall_expected, expected_t20, prefix_marker, postfix_marker, postfix_optional.
- `recipe/readout.py` — the window-dir reader + comparator.
- `evidence/u14-window1-r3-readout.{txt,json}` — the **live U14 readout** (snapshot, window still running).
- `evidence/u13-selftest.{txt,json}`, `evidence/u13-selftest-source.txt`, `evidence/synthetic-postfix/*`,
  `evidence/extractor-interfaces.txt`.
- `results.json`, `documentation.json`, `landing-paths.txt`.
