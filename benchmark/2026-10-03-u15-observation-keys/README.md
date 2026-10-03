# U15 stage-A observation keys (input for cx-t0, not a deployment plan)

Built by `build_keys.py`. **Reference is a PLACEHOLDER**: built against the U14 reference (126 lit);
after U14 stage-A is signed, swap `REF` to the U15 reference and rebuild (the reference_note field
in `u15-stage-a-keys.json` says the same).

## Board load

| Board | runs | movers | theme-watch (×1) | white-watch (×1) | lottery (×6) | lit-regression | ~min | windows (≤25 runs / 45 min) |
|---|---|---|---|---|---|---|---|---|
| 5ea | 57 | 5 | 1 | 0 | 2 keys (12 runs) | 39 | 99.8 | 3 |
| 5cd | 59 | 6 | 1 | 4 | 2 keys (12 runs) | 36 | 103.2 | 3 |
| 61b | 58 | 1 | 5 | 2 | 2 keys (12 runs) | 38 | 101.5 | 3 |

Window split: window 1 = movers + theme-watch + white-watch + lottery (signal first); windows 2..N = lit-regression. No new runs after minute 35 of a window.

## Shard provenance

- **movers** (per_key source + expectation in the json):
  - `u15-alias-theme-watch (driver)` — fd-api (5ea): POSITIVE, fix should move it off the AppCompat wall.
  - `u16 cluster E — u15-framework-bitmap` — cv2-com-stoutner-privacybrowser-standard (5ea), fd-musicplayer (5cd): moves=2, high.
  - `u16 cluster F — u15-runtime-m3 (94c31177)` — fd-app, fd-shatteredpixeldungeon (5cd): moves=0, medium (GLSurfaceView watch).
  - `u16 cluster K — u15-stubs-nsd + flutter-v2` — fd-immich (5cd): moves=1, medium.
  - `u16 cluster M — u15-jar-v1 TrampolineFinishOrder` — x (61b): moves=0, medium.
  - `u16 cluster L — u15-jar-v1` — fd-api (same key as the alias-theme driver; one entry carries both sources).
  - `u15-flutter-libandroid-v2 ATrace (9b824502, carries fff9be31 EGL)` — localsend, fd-kitchenowl (5ea); fd-fluffychat, fd-libre (5cd).
  - `u15 ANL dual alias b96a8991 (org.jitsi.meet) + resident host 9e3ad72e` — fd-meet (5ea; outer 11:36): markers [N2-OWNER] ABI global ready / [N3-OWNER] resident runtime published; expected move unknown (anl-review.md).
- **theme-watch** (×1, disjoint from all other shards per the 09:50 rule): keys overlapping lottery stay in lottery (json flags them `theme_watch` inside lottery.per_key: fd-uhabits/fd-notes/wikipedia); a lit key's theme-watch run doubles as its regression run (moved out of lit-regression: 5ea fd-tasks; 5cd photophase; 61b fd-calendar/fd-filemanager/fd-gallery/fd-libretube/fd-organicmaps). Remaining theme-watch: 5ea fd-tasks; 5cd photophase; 61b the five above.
- **white-watch** (×1): white-window family keys without flaky evidence (5cd: termux, cv2-ca-vaults-randomlydie, cv2-com-paultirk-yatoo, cv2-dev-obfusk-jiten-webview; 61b: cv2-com-degeder-yam, cv2-com-bytehamster-flowitgame). fd-app / fd-shatteredpixeldungeon moved into movers (cluster F).
- **lottery** (×6 consecutive, doubles as regression): flaky-only gate (knowledge/gates/flaky-keys.json entry or signed 0<k<n): 5ea fd-noice + fd-uhabits; 5cd fd-notes + wikipedia; 61b antennapod + noice. Evidence per key in the json.
- **lit-regression**: reference lit set minus the lottery keys.

## Known answers (asserted at build time)

- **generic disjoint invariant**: every key appears in exactly ONE shard per board (all shards pairwise disjoint) — asserted at build time.
- lit-regression(113) ∪ lit theme-watch(7) ∪ lit lottery(6) == reference 126 lit keys; disjoint; every key on its reference board.
- Every lottery key evidenced (registry entry or signed 0<k<n); today all 6 from the registry.

## Usage (cx-t0 turns this into plans; this file is NOT a plan)

    python3 scripts/lab/bms_batch.py --execute ... --keys "$(cat keys/<board>/<shard>.txt)" ...
