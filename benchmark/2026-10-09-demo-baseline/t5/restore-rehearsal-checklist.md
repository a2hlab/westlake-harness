# Sealed restoration rehearsal — live execution pending

## Evidence first

Only mock rehearsal has run in this delivery. No final seal, approved sealed
provider set, spare-board assignment or write authorization is fabricated.
The U13 fresh-ticket path and autostart installer are candidate alternatives,
not two providers to execute together. See README.md and the runbook.

## Before a future authorized rehearsal

1. Outer selects a spare board, confirms actual host libraries/foundation maps,
   exact stock/install prerequisites and current boot, announces and owns its
   external lock. A spare board's physical bytes are not normalized to 61b by
   silently changing the seal; only serial projection is allowed.
2. Finish final live `seal.json`, durable archived members and a reviewed
   enabled `restore-deployment.json`. Bind one base provider, then each active
   Route B/BoatAttack overlay, and exact rollback scripts. Preserve fresh native
   tickets, frozen/image checks and the existing executor's stop/view/smoke gates.
3. Dry-run with a fresh persistent host output directory:

```sh
bash scripts/lab/demo_restore.sh --dry-run --rehearsal \
  --seal "$SEALED_IDENTITY" --deployment "$SEALED_RESTORE_DEPLOYMENT" \
  --serial "$SPARE_SERIAL" --out "$FRESH_DRYRUN_LOG_DIR"
```

The source SHA/table check and read-only precheck must be reliable. Missing read
status, wrong system version, immutable drift or unknown host behavior refuse.
Dry-run writes only host logs, never takes a lock or calls a replay provider.

4. Outer issues a fresh authorization bound to both object SHAs, spare serial,
   boot, holder and expiry. Then, in a separately authorized window:

```sh
bash scripts/lab/demo_restore.sh --execute --rehearsal \
  --authorization "$SPARE_RESTORE_AUTHORIZATION" \
  --seal "$SEALED_IDENTITY" --deployment "$SEALED_RESTORE_DEPLOYMENT" \
  --serial "$SPARE_SERIAL" --out "$FRESH_REHEARSAL_LOG_DIR"
```

No `--observed` fixture is permitted for execution. The original seal remains
byte-identical; only its serial is projected into a new host-side file. For the
sealed demo board, only the user's explicit unseal/write authorization suffices.

## Review and recovery

- Required: full live selfcheck equal except serial; native ticket admission,
  319 path/321 assertion evidence where applicable, parent/child/single-ART
  views, foundation host-library proof and outer-read HW/ZZ screenshots. Review
  Route B/BoatAttack identities and user-facing acceptance separately.
- Preserve every raw provider argv/rc/stdout/stderr and the new replay journal.
  The existing journal and archived payloads are not modified or deleted.
- On error, the driver preserves the external lock and logs; caller prints the
  reviewed failing layer's rollback and gets outer disposition. Do not kill
  the main appspawn-x, unmount beneath a live parent, broaden permissions, auto
  reboot, reuse stale tickets or silently retry a later overlay.
- Caller verifies restoration and smoke, obtains outer review, then explicitly
  UNLOCKs. The driver never takes/releases the board lock itself.

All live items above remain **pending**, not completed by the offline selector.
