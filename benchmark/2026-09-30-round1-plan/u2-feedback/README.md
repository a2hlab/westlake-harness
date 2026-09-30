# U2 first-wall score and J4 / N3 batch handoff

**What changed:** old labels are insufficient: Noice now reaches a Java MediaRouter failure, SPD reaches **EGLImpl** (not GLImpl), and Flutter splits into runtime dependency and property-symbol failures. Four archived FDSAN reports are **DEBUG SIGNAL** diagnostics; the same PIDs continue into loading errors and `System.exit(1)`. They must be reviewed first, but cannot replace the subsequent fatal with an invented FDSAN abort.

The outer `2026-09-30-u2-sweep/results.json` signs **24 lit / 42 unlit**. All three archived 119-path maps match; all 66 APK hashes match the frozen cohort. This receipt uses only `u2-{5ea,61b,5cd}`. Habit Tracker's signed 1/3 reruns stay a separate intermittency note; they do not change its sweep verdict. Frozen U1 feature predictions are not edited, and U2 is not their exact profile.

## Score and evidence boundaries

- U0 first-checkpoint comparison over 42 unlit keys: **17 exact hits, 19 changed/unpredicted first checkpoints, 6 unknown**. One of the 19, VLC's resource wall, was already a U0 secondary wall: known-first-or-secondary coverage is **18/42**. The remaining 18 changed first walls are new relative to that U0 receipt, often revealed by successful earlier repairs, not evidence that those repairs failed. Three hits are host input gates. This is descriptive transfer, not prospective scanner accuracy.
- Literal frozen U1 light labels: **22 hits / 27 predicted lights**, **5 false alerts**, **2 missed lights** (Anki and BinaryEye were predicted to advance). Precision 81.5%, recall 91.7%; `advance` and `unknown` are not darkness predictions. All 21 U0 lights retained; Anki, AntennaPod and BinaryEye added. False alerts: API Demos, both Noice keys, Habit Tracker, Wikipedia.
- **34/42** have an explicit PID-attributed fatal, **5** have no process fatal, **3** stop at host input validation. fd-noice has fatal background tasks on missing `SSLSockets`, with the process kept alive; the relationship to its white UI is unproved. The other four (AppManager, Termux, fd-mobile, Habit Tracker) have no selected fatal. Do not invent a death cause for them.
- Four faultlogs all match target PID and BMS UID. `evidence.json` retains headers, SHA-256, hilog chains and numbered events. `unlit-42.csv` separates **first failed checkpoint**, **first fatal**, secondary observations, layer confidence and repair owner. PPSSPP still fails libGLESv2 before a later RenderThread SIGSEGV; its missing crash stack leaves the signal root cause unknown.

## Next batches, ranked by first-wall app count

| Batch / cluster | Primary apps | Additional observed apps | Work |
|---|---:|---:|---|
| N3 namespace/dependencies | 7 | 3 | Flutter 3: private libandroid needs liboh_android_runtime; BurgerKing/OrganicMaps/McDonald's: libandroid; PPSSPP: GLESv2. Additional VLC:GLESv2, SPD:libstdc++, Element:libandroid. |
| J4 boot API closure | 5 | 0 | Feeder: NetworkRequest.getNetworkSpecifier; Gallery: MediaStore field; OsmAnd: NetworkInfo.getState; Wikipedia: TagSoup.setProperty; X: NetworkCapabilities bandwidth method. Coordinate boot classpath owner; a replacement in an ordinary JAR may not supersede these classes. |
| J4 null producer investigation | 3 | 0 | BreezyWeather, Catima widget update, WiFiAnalyzer: repeated getClass NPE. Same exception shape is **not** proof of a common producer or one repair. |
| N3 EGLImpl | 2 | 0 | Unciv + SPD: `_eglGetDisplay(Object)J`; preserve already added GLImpl behavior and resolve SPD's earlier dependency as well. |
| N3 JNA resource | 2 | 0 | Firefox + Fennec still cannot find libjnidispatch resource; errno symbol work alone is insufficient. |
| N3 property symbol | 2 | 1 | Aves Libre + Saber: `__system_property_find`; same later failure in Immich, masked by its verifier first wall. |
| J4 TLS Java | 1 fatal + 1 secondary | 0 | Nextcloud: WestlakeSSLContext has no SSLEngine; fd-noice: SSLSockets class missing on background workers. |

Full sorted batches are **[J4.json](J4.json)** and **[N3.json](N3.json)**, with exact keys, source paths and line-numbered failures. Remaining first-wall groups: J4 API Demos theme (already targeted by J3), LibreTube cache size, SystemVibratorManager initialization, OpenCamera null Intent producer, MediaSession service resolution, MediaRouter service, Restrictions collection, Sentry metadata and Immich verifier interface; N3 OpenSLES `slCreateEngine`, WebView provider and VLC theme resource projection. Layer assignments with `low`/`medium` confidence are investigation ownership, not proven root causes. Publish one JAR batch and one native batch after source validation; do not change frozen implementations without the existing rules.

Exclusive primary routing is **J4 19 / N3 20 / input 3**, covering 42 keys; N3's 20 include four diagnostic-only no-fatal apps. Cross-layer secondary memberships are listed separately and must not be summed as extra cohort apps. `N3-additional-fdsan.json` covers the 4 shared loader/FDSAN diagnostics without double-counting their namespace failures. Input gates remain Seal ZIP sidecar, Toutiao ELF32 sidecar and Subway Surfers identity mismatch, outside either runtime batch.

## Facts and reproduction

Original producer totals (also independently recounted: **126 captured**, t5 **33 alive / 30 absent / 3 unknown**, t20 **31 / 32 / 3**):

```text
5ea TOTAL keys=22 screenshots_captured=40/40 alive_t5=10 alive_t20=9
61b TOTAL keys=22 screenshots_captured=44/44 alive_t5=11 alive_t20=10
5cd TOTAL keys=22 screenshots_captured=42/42 alive_t5=12 alive_t20=12
```

```sh
python3 benchmark/2026-09-30-round1-plan/u2-feedback/extract.py
python3 benchmark/2026-09-30-round1-plan/u2-feedback/classify.py
python3 benchmark/2026-09-30-round1-plan/u2-feedback/validate.py
```

Offline only; no board lock/action, no runtime/source patch. R2: evidence attribution/profile/record checks verified; screenshot decisions inherited unchanged from outer; low-confidence causes, missing crash stacks and white-screen mechanisms remain unknown. Full source evidence hashes are in `evidence.json`, `run-audit.json`, `results.json` and `SHA256SUMS`.
