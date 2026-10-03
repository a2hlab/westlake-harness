# U14 stage-A observation keys (input for cx-t0, not a deployment plan)

Built by `build_keys.py` (read-only inputs on master). Priority per board: **movers > lottery > lit-regression**.

## Board load

| Board | runs | movers | white-watch (×1) | lottery (×6) | lit-regression | ~min | windows (≤25 runs / 45 min) |
|---|---|---|---|---|---|---|---|
| 5ea | 57 | 6 | 0 | 2 keys (12 runs) | 39 | 99.8 | 3 |
| 5cd | 58 | 10 | 5 | 2 keys (12 runs) | 31 | 101.5 | 3 |
| 61b | 59 | 8 | 2 | 2 keys (12 runs) | 37 | 103.2 | 3 |

Window split: window 1 per board = movers + lottery (the U14 signal, run first); windows 2..N = lit-regression. Stop scheduling new runs by minute 35 of each window.

## Shard provenance

- **movers** (per_key source + expectation in `u14-stage-a-keys.json`):
  - `u14-m5-watchlist` — 13 dialog-zorder keys (watchlist.csv rows; expectation per row).
  - `u14-flutter-libandroid` — localsend, fd-kitchenowl (5ea); fd-fluffychat, fd-libre (5cd): EGL interposer, first fatal moves past eglCreateWindowSurface.
  - `u14 ICU alias shim` — toutiao (61b).
  - `M5 named target` — cv2-org-andresoviedo-dddmodel2 (5cd; DIGEST 690/714/721, outer 09:25).
  - `u16 cluster D — u14-native-abi-gecko (7605812c)` — vlc (5ea), fd-fennec_fdroid (5cd): Gecko ABI f8619ad5 moves __pthread_cleanup_push/__gnu_strerror_r (U14 no-log fix observation; v5).
  - `u16 cluster C — u14-native-abi-v2 (f8619ad5)` — mcdonalds (61b), fd-im-vector-app (5ea): bionic _ctype_ (Realm) moves (U14 no-log fix observation; v5).
  - `bt-le-scancallback stubs 87cf65cc (u16 cluster J)` — fd-plus (5ea): bind NoClassDefFoundError (ScanCallback) moves (U14 no-log fix observation; v5).
- **white-watch** (×1, priority 2) — white-window family keys without signed k/n or flaky-registry entry: 5cd ×5 (fd-app, termux, cv2-ca-vaults-randomlydie, cv2-com-paultirk-yatoo, cv2-dev-obfusk-jiten-webview); 61b ×2 (cv2-com-degeder-yam, cv2-com-bytehamster-flowitgame).
- **lottery** (×6 consecutive, priority 3) — flaky keys ONLY (knowledge/gates/flaky-keys.json entry, or a signed 0<k<n; none has the latter today): 5ea ×2 (fd-noice, fd-uhabits); 5cd ×2 (fd-notes, wikipedia); 61b ×2 (antennapod, noice). Evidence per key recorded in u14-stage-a-keys.json (lottery.per_key).
- **lit-regression** — the U14 reference 126-lit set, each key on its reference board.

## Known answers (verified by build_keys.py at build time)

- lit-regression union across boards == the reference's **126** lit keys; no duplicates; every key on its reference board.
- every lottery key is evidenced: an entry in knowledge/gates/flaky-keys.json, or a signed k/n with 0 < k < n in a stage-A window signoff (verified at build time; today all 6 come from the registry).
- lit-regression **excludes the lit lottery keys** (U13 README footnote pattern): their ×6 doubles as the regression run. Known answer: lit-regression(120) ∪ lit lottery(6) == the reference's **126** lit keys, disjoint, boards match.

## Usage (cx-t0 turns this into plans; this file is NOT a plan)

    python3 scripts/lab/bms_batch.py --execute ... --keys "$(cat keys/<board>/<shard>.txt)" ...
