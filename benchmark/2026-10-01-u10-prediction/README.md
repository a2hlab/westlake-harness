# U10 prediction table (written before the U10 window)

**Rule (2026-10-01):** a full sweep is only informative against a prediction written *before* it runs.
This is that prediction for U10. After the U10 window signs off, grade it with
`predict_vs_actual.py compare` (see `command-v1.txt`); a `regression` exits 1, a `missed-wall`
(predicted `lit?`, not lit) is a wall the static scanners did not see and feeds the next scan.

## Inputs (all evidence, cited)

| Input | Path | Commit / id |
|---|---|---|
| Baseline (U9 sign-off, 115/166 lit) | `benchmark/2026-10-01-u9-sweep/outer-signoff.json` | master 8b0c76e402; wall regen c671f4fc89 |
| Death clusters | `benchmark/2026-10-01-u8-death-clusters/clusters.json` | v7 |
| Flaky keys | `knowledge/gates/flaky-keys.json` | 7 keys |
| Tool | `scripts/lab/predict_vs_actual.py` | `predict` subcommand |

`predict_vs_actual.py` precedence per key: **observed > flaky > baseline-lit > cluster-covered > baseline**.
The 7 U10 beneficiaries sit in clusters `other`/`no-termination`, whose `coverage` dicts predate the U10
fix ids — so their `covered_by` column is intentionally blank and each is set via `--observed=lit?` with the
fix named in `reason`. "lit?" = the one named first wall is cleared; the *next* wall is unknown, so a miss
there is informative, not a surprise.

## U10 fix set (generic shared-layer only — no per-app hacks)

| Fix id (`--include`) | Layer | Beneficiary key | First wall it clears | Source |
|---|---|---|---|---|
| `libstdcxx` + `libjnigraphics` | native | `toutiao` | libflipped bootstrap can't resolve `libstdc++.so` in the app private namespace | `native-closure-prediction.md`; wall-1 landed master 504b66cea (cx-bms) |
| `abort-visibility` | native | `fd-meet` | soloader `UnsatisfiedLinkError` → `android_set_abort_message` not visible in bridge ns | `u9-first-wall.md` |
| `strerror_r` | native | `fd-fennec_fdroid`, `firefox` | native `signal` at startup; GNU-vs-POSIX `strerror_r` not exposed to app ns | `u9-first-wall.md` (APPSPAWN first-fatal) |
| `opensles-facade` | native | `mindustry` | `ExceptionInInitializerError` → OpenSLES facade ABI not transpiled | `u9-first-wall.md`; cx-bms Mindustry fix |
| `j10f-websettings-defaults` | jar (U10 37465d6d) | `fd-tutanota` | `getUserAgentString(...) must not be null` | `../2026-10-01-u10-jar/j10f-websettings-defaults.md` |
| `predicate` | jar (U10 37465d6d) | `cv2-com-nbossard-packlist` | `ClassNotFoundException: com.android.internal.util.Predicate` | `../2026-10-01-u10-jar/u10-classlist-diff.md` |
| `j10e-split` | jar (U10 37465d6d) | — (no new key) | behavior-unchanged split of J10eWebView; U10 jar base, proven byte-for-byte equal to J10g 238ffc14 | `../2026-10-01-j10-freeze-draft/split-equivalence.md` |

## Prediction (`predictions-v1.csv`, 166 rows)

| Prediction | Count | Meaning |
|---|---|---|
| `lit` | 112 | baseline lit; must stay lit |
| `lit?` | **7** | the 7 beneficiaries (all `dead` in U9) clear their named first wall |
| `flaky` | 6 | in `flaky-keys.json`: judged by repeat rate, not one run |
| `dead` | 25 | cluster not covered by a U10 fix |
| white/black window, app_failed, launcher-fg | 16 | not covered |

**The lit accounting closes with zero regression:** baseline 115 lit = 112 predicted-lit + 3 baseline-lit
keys that `flaky-keys.json` reclassifies to `flaky` (`antennapod`, `fd-notes`, `wikipedia`). No lit key is
predicted to go down — the flaky flag means "confirm by repeat rate", not "lost". The other 3 flaky rows
(`fd-noice`, `fd-uhabits`, `noice`) were already non-lit (white window) in U9. Byte-identical rollback is
proven each window (RUNTIME/BOOT fp unchanged), so a U10 regression would be a real defect, not drift.

### The 7 beneficiaries: `dead` → `lit?`

| Key | Cluster | Fix | Notes |
|---|---|---|---|
| `toutiao` | other | libstdc++ + libjnigraphics | U9 first run matched the libflipped/libstdc++ prediction exactly; `java-layer-prediction.md` lists further walls (null services, libnativewindow/graphics ctors) so **full-lit is not claimed** |
| `fd-meet` | other | abort-visibility | — |
| `fd-fennec_fdroid` | no-termination | strerror_r | — |
| `firefox` | no-termination | strerror_r | — |
| `mindustry` | other | opensles-facade | — |
| `fd-tutanota` | other | j10f-websettings-defaults | died in U9 on the J10f null-getter defect; U10 jar fixes it |
| `cv2-com-nbossard-packlist` | other | predicate | — |

**Ceiling if all 7 land and have no next wall: 115 + 7 = 122/166.** Realistically `toutiao` is expected to
move its wall forward (native closure clears, Java layer remains), so a `missed-wall` there is the *expected*
signal, not a failure — it tells the scanner which Java-layer wall to model next.

## What was wrong before / what this sets

- **Before:** these 7 keys were `dead` in U9. The temptation (esp. for `toutiao`) is a per-app patch.
- **Rule this keeps:** every U10 fix is a generic shared-layer change (native namespace policy / linker symbol
  visibility / ABI facade / framework jar default) that benefits a *class* of apps, not one. `toutiao` is
  restored as an ordinary unified-state key, no toutiao-specific code.
- **Grading:** `lit?` is a falsifiable claim about one named wall. The post-window `compare` turns every
  `missed-wall` into the next scan target, so the prediction table is the selection input for U11.

## v2 (2026-10-01 20:50, outer correction, before any U10 result)

Only change from v1: fd-tutanota lit? -> alive-white-window. J10f's real WebSettings defaults pass its U9 wall
(getUserAgentString non-null), but tutanota's UI is its web client (assets/tutanota/index.html, 3218 files) inside a
WebView and there is no WebView renderer -- the same ceiling U9 prediction v5 already recorded. Compare U10 against v2.

## v3 (2026-10-01, outer correction patrol ACK(90), before any U10 result)

Change from v2: **OpenSLES facade is deferred to U11, so `mindustry` is no longer a U10 beneficiary** — its
`--observed=lit?` line is dropped and `opensles-facade` leaves `--include`, so mindustry reverts to its U9
verdict `dead`. fd-tutanota stays `alive-white-window` (v2). Everything else unchanged.

- **lit? = 5** (was 6): `toutiao`, `fd-meet`, `fd-fennec_fdroid`, `firefox`, `cv2-com-nbossard-packlist`.
- `fd-tutanota` -> `alive-white-window`; `mindustry` -> `dead` (dead 25 -> 26).
- Lit accounting still closes: 112 lit + 3 lit->flaky = 115, zero regression. Ceiling if all 5 land: **120/166**.
- **U10 fix set (v3):** native `libstdc++`+`libjnigraphics` (toutiao), `abort-visibility` (fd-meet),
  `strerror_r` (firefox, fd-fennec_fdroid); jar `j10f-websettings-defaults` (fd-tutanota -> white),
  `predicate` (packlist), `j10e-split` (no-op). **No OpenSLES in U10.**
- **Native artifact pinned (outer ACK(90)):** U10 native = `bbe46462b` (compat `015aa3a6`, libnativeloader
  policy `621caec4`, appspawn-x host `62debf19`). Rollback target is **U9**, not U8:
  `565fc6fdc116` / `a2919b793eb6` + boot `4db882a81732` + 318 identity assertions.

**Compare U10 against v3** (superseded by v4 below).

## v4 (2026-10-01, cx-bms confirmation, outer patrol ACK(90), before any U10 result)

Change from v3: **libjnigraphics is deferred to U11 — the U10 libnativeloader policy adds `libstdc++` only.**
So `toutiao` goes `lit?` -> **`dead`**: its libstdc++ bootstrap wall clears (policy `621caec4`), but the next
wall is a libjnigraphics-needing feature lib (now U11). The first wall **moves**; toutiao does not light in U10
— judged by the window hilog (libstdc++ loader error gone, next fatal = a libjnigraphics SONAME), not by the
sweep verdict. Everything else unchanged from v3.

- **lit? = 4** (was 5): `fd-meet`, `fd-fennec_fdroid`, `firefox`, `cv2-com-nbossard-packlist`.
- `toutiao` -> `dead` (first-wall-move), `mindustry` -> `dead`, `fd-tutanota` -> `alive-white-window` (dead 25 -> 27).
- Lit accounting still closes: 112 lit + 3 lit->flaky = 115, zero regression. Ceiling if all 4 land: **119/166**.
- **U10 native (bbe46462b) refined:** policy `621caec4` = `+= libstdc++` **only** (libjnigraphics → U11);
  compat `015aa3a6` = GNU `strerror_r` (firefox, fd-fennec_fdroid); appspawn-x host `62debf19` =
  `U10ShareResidentCompat` (android_set_abort_message abort-owner visibility, fd-meet). Rollback target U9
  `565fc6fdc116` / `a2919b793eb6` + boot `4db882a81732` + 318 assertions.

**Compare U10 against v4** (the current live prediction; `predictions-v4.csv`, `command-v4.txt`).
