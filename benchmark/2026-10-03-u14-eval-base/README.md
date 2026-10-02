# U14 evaluation base: the U14 reference set + the U14 watchlist

Offline, board #90, no board. The draft the U14 sign-off pairs against: the **U14 reference set** (what "lit" is expected
to be) and the **U14 watchlist** (the per-feature on-board judge criteria so a signer reads the expected changes, not
false regressions). Assembled from landed work; verdicts/promotions are the outer's.

## U14 reference set
U14 reference = **U13 reference (122 lit, `benchmark/2026-10-03-u13-reference`) + the gains signed at U13 promotion**.
Built the same overlay way as the U13 reference (carry the base tiles verbatim, trace each new tile to the run that
signed it). The U13-promotion gains known so far are U13 stage-A **window1** (outer-signed 2026-10-03,
`u13-stage-a-plan/window1-signoff`):

| new-lit key | board | k/n | t20 source |
|---|---|---|---|
| wikipedia | 5cd | 6/6 | U13 window1 lottery-wikipedia-* (M1 `[M1-COPY]`; `2026-10-03-wikipedia-m1-closure`) |
| fd-uhabits | 5ea | 6/6 | U13 window1 lottery-fd-uhabits-* |
| fd-noice | 5ea | 6/6 | U13 window1 lottery-fd-noice-* |

So the U14 reference tally is **125 lit = 122 (U13) + 3 (window1 M1 lottery gains)**, **pending window2+** (more U13
stage-A gains the outer signs later — add them to this set the same way before U14 pairing). When U13 is promoted, build
the U14 reference by overlaying these gains onto the U13 reference (new t20 = the window1 run t20, verdict=lit), exactly
like `build_reference.py` did for U13.

## U14 watchlist (per-feature on-board judge)
U14 stacks M1 (+ the `[M1-COPY]` base) with the bridge M5/M6, the ICU walls, the Flutter EGL interposer, and the a-path
lazy stubs. Each changes what some keys' t20/hilog show; the signer must judge by the criterion below, not by "looks
different from U13". Full per-item detail in `watchlist.csv`.

### 1. M5 sub-window zLevel — the 13 dialog-first lit keys (`benchmark/2026-10-03-u14-m5-watchlist`)
After M5 (`07fd530a`), these 13 lit keys surface their own dialog on top of the Activity (the dialog was pressed under
before). **Judge:** own dialog on top = expected, **score lit**; judge by `androidType`, not VRI name; a regression is a
white/black t20 or a non-app surface. Keys: `cv2-com-asdoi-timetable, cv2-com-ath0-rpn, cv2-com-github-dfa-diaspora-android,
cv2-com-harr1424-listmaker, cv2-com-knirirr-beecount, cv2-de-koelle-christian-trickytripper,
cv2-org-secuso-privacyfriendly{memory,pin,ruler}, fd-netguard, fd-stk, newpipe, opencamera`.

### 2. ICU walls — 3 board criteria (`benchmark/2026-10-03-u14-appns-build`, outer 04:01)
1. **One copy each, same ns:** `maps` show `libicuuc.so` (`9b36b989…`, f74827d9 + the one DT_NEEDED) and
   `libicu74compat.so` each mapped exactly once, same (app/bridge ICU) ns. Two copies = ns/double-load regression.
2. **The extra PT_LOAD loads:** patchelf relocated `.dynstr`; every ICU-using lit key from `helloworld` onward stays lit
   with no `MUSL-LDSO … failed` for `libicuuc.so`/`libicu74compat.so`.
3. **Toutiao ICU wall cleared:** no `load libicui18n.so failed, namespace=westlake.anl.app…` and no `ICUWrapper` SIGSEGV
   (pc=0); `dlsym(<ICU handle>,"ubrk_open_74")` resolves via the shim.

### 3. Flutter EGL interposer — board judge (cc-t3 `822dbf198f`, `2026-10-03-u14-flutter-libandroid`)
The Flutter-private `libandroid.so` = `fff9be31…` adds the hwui EGL interposer (+4 LIBEGL). **Judge (hilog):**
`eglCreateWindowSurface: detected ANW shim … unwrapped to OH NativeWindow=… -> EGLSurface=<non-null>` (vs the old
behavior binding platform libEGL and failing). **Cohort:** `localsend, fd-kitchenowl, fd-fluffychat, fd-libre` — first
fatal **moves past `eglCreateWindowSurface`** (next wall unknown: Impeller/Vulkan fallback, plugins, textures; lit
low–medium). Combined with the app-ns public-lib fix, these also need GLES/Vulkan visible (see
`2026-10-03-toutiao-next-wall` for the Lynx/V8 analog).

### 4. OH-DISPLAY-EVENT / APK-ORIENTATION — a-path lazy check (`2026-10-02-u14-bridge-r1r3`)
The U14 baseline bridge is instruction-equal to `84695d62` except the two **inert a-paths** OH-DISPLAY-EVENT and
APK-ORIENTATION (runtime `ac59dec0`/U13 `18763dd4` have no Java entry to reach them). **Judge (hilog, per app process):**
`[OH-DISPLAY-EVENT] dispatchDisplayEvent(int) unavailable` appears **once per app process and no other `[OH-DISPLAY-EVENT]`
line** (no `[OH-DISPLAY-EVENT] dispatched`), i.e. the lazy stub logs its one NoSuchMethod-equivalent and is never
actually dispatched. More than once, or a `dispatched` line, means the a-path became live (investigate). APK-ORIENTATION
is the same shape. These are **cleared/inert**, not walls — do not score them as regressions.

## This round's rule
A U14 sign-off pairs against the latest signed baseline (U13 ref + its promotion gains), and reads each stacked feature
with its own criterion: M5 re-stacks own-UI (lit), the ICU shim adds one NEEDED + a relocated segment (lit, one copy),
the Flutter EGL interposer moves the first-fatal past `eglCreateWindowSurface`, and the a-path stubs log one inert line
per process. "Different from U13" is expected where a U14 feature changed it; a regression is white/black, a non-app
surface, a double-load, or an a-path going live.

## Files
- `watchlist.csv` — the consolidated per-item watchlist (feature, keys, board-judge criterion, expected vs regression).
- `evidence/u14-reference-tally.txt` — the U14 reference = U13 122 + window1 gains, with the window1 signoff citation.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board. Reference/promotions are the outer's; the M5/EGL/a-path fixes are cc-t3's. Sources read read-only
(`westlake-harness`, `-t3`, `-u7-executor`, and my landed `u13-reference`/`u14-m5-watchlist`/`u14-appns-build`).
