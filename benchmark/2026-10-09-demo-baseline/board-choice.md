# Demo board choice — read-only t1 evidence

## Recommendation

Select **61b0657200000000000000000324012c** for t3/t4. This is a selection
recommendation for outer scheduling, **not sealing**, not a new UI signoff and
not authorization to start t3 in this round. No board was locked or written.

All three boards match their signed retained **U13** fingerprints. U14 remains
a candidate; historical U14 screenshots do not prove it is the live baseline.
61b has the reviewed `51e1b525` installation service already at both aliases.
5ea/5cd retain `2c9a5294`, which rejects the exact Seal ZIP payloads and
Toutiao's ARM32 libcvt member. Choosing61b avoids an installer/foundation change
and its USB recovery risk. The difference is part of signed U13, not drift.

## Three-board comparison

| Board | Runtime / boot fingerprint | Signed U13 match / same boot during reads | /data free GiB | Historical U13 signed lit keys | Gallery screenshot provenance keys | libinstalls |
|---|---|---|---:|---:|---:|---|
| 5ea | `821de739cf81` / `ee927db88a67` | yes / stable | 159.22 | 47 | 58 | `2c9a5294` |
| 5cd | `821de739cf81` / `ee927db88a67` | yes / stable | 145.41 | 46 | 61 | `2c9a5294` |
| 61b | `452447a4a0ba` / `ee927db88a67` | yes / stable | 93.12 | 33 | 10 | `51e1b525` |

Runtime has124 file rows per board; boot has36. Both installation aliases were
read separately. Fingerprint equality is the existing signed disk-file-set
check; this round did not claim fresh process-root321 assertions, loaded
installation service verification, single-ART maps, or screen brightness.
`pidof appspawn-x` is retained as raw presence only; its two PIDs are not counted
as two parent services.

## Capacity

The full signed gallery superset has **128 distinct packages**. Every APK path
is present in the VM. Sizes total **1,756,238,122 bytes**; the contract's ×3
estimate is **5,268,714,366 bytes (4.91 GiB)**. All boards exceed it.61b has
**99,990,618,112 bytes (93.12 GiB)** free, leaving **94,721,903,746 bytes**
after that estimate. This is a conservative gallery-superset estimate for the
manifest that cx-bms is building, not its final audited APK total. Final
manifest extras (especially BoatAttack and the chosen Toutiao route) must be
added and capacity checked again before t3. No existing APK/data was deleted.

`df -k /data` reports `/dev/block/sda63`; toybox prints a bind-mount alias as
its displayed mount point. Capacity is taken from that filesystem's Available
column, not from the misleading last-column path.

## History and its limits

Historical U13 count = union of keys with `lit_runs>0` or `verdict=lit` in
Stage A window1–4 outer signoffs, grouped by the actual recorded board. Counts
are **47 /46 /33**. Keys tested on several boards can appear in several sets.
Unequal shard coverage makes this unsuitable as a hardware success-rate ranking.
The gallery's129 chosen screenshot sources are58 /61 /10 respectively; these
are a separate provenance metric, not current simultaneously lit apps. Legacy
`lit` includes empty-list/loading UI; neither count establishes100 own-content
first screens. The final demo manifest and t3 human review establish that.

## Evidence and procedure

- `evidence/readonly-20261009/receipt.json`: timestamps, every exact read command,
  return code, stable before/after boot IDs; per-board raw df and both fingerprints.
- `evidence/apk-capacity.json`: all128 input paths and byte counts, no missing file.
- `evidence/history.json`: exact signoff sources and each board's counted keys.
- `results.json`: selection, signed expectations, capacity margins and service SHAs.
- Signed expectations: `benchmark/2026-10-03-u13-stage-b/results.json`,
  `README.md:44–48`; scope is the retained U13 state, not old underlay.
- Installation behavior: `benchmark/2026-10-02-libinstalls-unification/README.md:57–76`
  and `evidence/source.diff`; disk SHA alone does not assert the service loaded it.
- Contract: `specs/demo-baseline/t1-inventory.spec.md:17–21`.
- Transport/reboot discipline: `.octos/OPS-RUNBOOK.md:9–12,144`.

`collect_readonly.py` ran in a2hlab through the existing `hdc_mac.sh` forwarding
transport, importing only bms_batch fingerprint functions. Its transport accepts
only a fixed read-command allowlist: cat boot/uptime, df, pidof and sha256sum.
It never instantiates guarded deployment objects, never invokes batch preflight,
never installs/starts an app, captures a screen, changes logs/clock/power settings,
or takes a lock. **Remote write operations=0; lock operations=0.** The paused
hw248 watcher remains stopped; this new task did not restart U14 window7.
