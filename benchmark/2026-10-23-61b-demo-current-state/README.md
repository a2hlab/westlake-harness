# 61b demo current state (T55, 2026-10-23, first pass)

- **Board**: 61b, boot 350d374d (up about 18 h), no prior lock. The fresh `bm dump -a` (208 lines) is identical to the
  outer 10:02 index.
- **13 excluded APKs** (demo-list → peer record → package, see `targets-map.json`): **all 13 are already absent**, both
  in the fresh list and in the 10:02 index. Nothing was uninstalled. All 13 have a local recoverable APK whose SHA
  equals the record's `apk_sha256`. Toutiao, BoatAttack and the imehost host (HAP b189) remain installed.
- **Active start chain**: `01_westlake_u13_toutiao.cfg` 7b9f2c0e → ROOT `icon-manual-20261021-r3`.
  - The guardian shell (`entry.sh` of boot 350d374d) is alive.
  - That boot directory has no state or events yet: it waits for the host foreground.
  - No host, Toutiao or appspawn-x process; no stop markers.
- **Screen**: power was SLEEP. One wakeup and one screenshot: lock screen. No swipe, no tap.
- **Not verified**: Toutiao reopen white screen this round, and cold power cycle. The historical 115/13 list is
  history, not current proof.

Raw (argv/start/end/stdout/stderr/rc per command): `$HOME/.local/share/westlake/61b-demo-current-state-20261023/`.

## Outer review and parallel intake

The outer reviewer independently checked 13 original record hashes and all 13 recovery APK hashes, exact package absence and both preserved packages. Historical V2 and later T34 signatures were hash checked; neither proves a fresh cold power cycle. See `exclusion-map.json` and `outer-intake-review.json`.

Fresh `raw/00-ro/host.stdout` binds the installed HAP to b18978b8. The bounded REA attempt was blocked by client approval policy before execution; `rea/` preserves that distinction. The outer reviewer verified all nine HAP members and five existing source pins, without claiming new decompilation.

The second read-only collection timed out during an unbounded runtime file-hash walk; its partial output is retained privately and is not a full runtime fingerprint. No retry occurred. The current ordinary desktop observation proceeds separately under T56, with no runtime deployment. White-screen repair, manual reentry and physical power-cycle acceptance remain unverified.
