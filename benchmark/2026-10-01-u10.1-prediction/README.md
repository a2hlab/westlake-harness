# U10.1 prediction v5 (pre-window)

Next round = **U10.1 native + U11g JAR** (`73c0da44…`). Written before the window; grade with
`predict_vs_actual.py compare` after sign-off (`command-v5.txt`). Baseline = U9 sign-off (115/166 lit).

## Result (`predictions-v5.csv`, 166 rows)

| prediction | count | meaning |
|---|---|---|
| `lit` | 112 | baseline lit; must stay lit |
| `lit?` | **4** | `x`, `fd-client`, `cv2-com-nononsenseapps-notepad`, `fd-api` (U11g JAR beneficiaries) |
| `flaky` | 6 | flaky-keys.json (3 of them, antennapod/fd-notes/wikipedia, are baseline-lit) |
| `dead` | 29 | incl. toutiao/fd-meet/fennec/firefox/packlist/tutanota/mindustry |
| white/black/app_failed/launcher | 15 | not covered |

Lit accounting closes: 112 lit + 3 lit→flaky = **115 baseline, zero regression**. Ceiling if all 4 land: 115 + 4 =
**119/166** (`x` was `alive-white-window`, the other 3 were `dead` — all 4 are net-new).

## --observed (each with its basis)

| key | U9 | v5 | basis |
|---|---|---|---|
| `opencamera` | lit | **lit** | reverted to U9 — U10.1 native removes the U10 regression that hit it |
| `fd-organicmaps` (organicmaps) | lit | **lit** | reverted to U9 — same |
| `toutiao` | dead | **dead** | libstdc++ cleared by U10.1, but first wall **moved** to OkHttp conscrypt (`com.android.org.conscrypt.SSLParametersImpl` absent — `okhttp-platform.md`); not lit |
| `fd-meet` | dead | **dead** | U10 window observed unchanged (abort-message visibility did not clear its wall) |
| `fd-fennec_fdroid` | dead | **dead** | U10 window observed unchanged (GNU strerror_r did not clear its wall) |
| `x` | alive-white-window | **lit?** | U11g TelephonyFetcher → `getSystemService("phone")` non-null → telephony cast passes |
| `fd-client` | dead | **lit?** | U11g WlSSLEngine → `createSSLEngine` non-null → Dagger graph builds → accountManager non-null |
| `cv2-com-nononsenseapps-notepad` | dead | **lit?** | U11g AppContentProviders installs the app's own ContentProvider → `query` non-null |
| `fd-api` (com.termux.api) | dead | **lit?** | U11g J10dTheme alias guard → AliasTargetTheme's AppCompat theme wins → AppCompatActivity starts |

## Keys deliberately NOT re-observed (stay at baseline `dead`)

- `firefox` — same `strerror_r` as `fd-fennec_fdroid`; treat as dead (U10 observed unchanged). Not in `--observed`
  so it lands on baseline `dead` either way.
- `cv2-com-nbossard-packlist` (Predicate) and `fd-tutanota` (J10f defaults → white window per v2) — their fixes are
  in the **U10 JAR carried into U11g**; their outcome was set by the U10 window, not re-predicted here. (If the
  U10 sign-off recorded packlist lit / tutanota white, carry that into the compare baseline.)
- `mindustry` — OpenSLES deferred to U11; baseline `dead`.

## Regression controls

- **Lit, must stay lit (115):** the baseline-lit set; any → non-lit is a `regression` (compare exits 1).
- **Provider-cluster controls (79):** the already-lit keys that declare ≥1 ContentProvider
  (`regression-controls-provider.txt`). U11g's `AppContentProviders` installs app providers at bind — these 79
  must stay lit (installing their providers must not crash them). e.g. `aegis`, `anki`, `markor`-class note apps,
  `cv2-com-knirirr-beecount`, `cv2-de-koelle-christian-trickytripper`, `opencamera`, `fd-organicmaps`, …
- **okhttp controls (stay lit):** `fd-droidify`, `newpipe` — stock okhttp 4.x (no conscrypt dependency); they must
  stay lit (the toutiao conscrypt finding must not touch the stock-okhttp path).

## What this sets

The round's net-new coverage is **4 `lit?`** (the U11g JAR fixes); the U10.1 native round is mostly a
**regression repair** (opencamera/organicmaps back to U9) plus confirming the native fixes that U10 observed as
no-ops (fd-meet/fennec stay dead). toutiao advances one wall (libstdc++ → conscrypt) but stays dead — the compare
should classify toutiao as a **hit** (predicted dead, still dead) with the first-wall-move read from its window
hilog, and its next wall (OkHttp conscrypt) routed to the conscrypt/BCP lane.
