# Offline seal fingerprint compiler

## Evidence first

**An install manifest is not a sealed board snapshot.** Input APK paths and
historical hashes cannot replace installed `base.apk` identities. A baseline
short hash cannot describe Route B or BoatAttack overlays. This compiler accepts
only a complete, same-boot, explicitly read-only **effective** snapshot and writes
the existing `demo_selfcheck.sh` schema directly. It does not collect from a
board, apply overlays, change AGENTS, restore, authorize reboot or claim t5 done.

The actual selfcheck CLI is exercised offline with a generated seal containing
both overlays, then rejects a changed Route B member. A successful fixture prints
`OFFLINE_MATCH`, never live `PASS`. No real seal is published in this delivery:
the 61b final snapshot and both special-app decisions are still pending.

## Snapshot contract

Start with `snapshot-template.json`. The collecting lane/outer must retain raw
read receipts and fill these fields after final t3/overlay review:

- Exact 61b serial, timezone-bearing capture timestamp, boot ID before/after,
  zero writes/locks, and `errors=[]`; a changed boot or a partial read rejects.
- Effective `files` maps: `runtime`, `boot`, `overlays`, `installation`. SHA256
  is full-length. Duplicate paths across groups must have identical effective
  bytes; a replaced runtime JAR must not retain the old SHA in `runtime`.
  Collector must assert `file_inventory_complete=true`, not just supply one
  successful file. This assertion requires the collecting lane's membership
  receipts; the offline compiler cannot independently know every board path.
- `fingerprint_lines.runtime/boot`: original successful `sha256sum` lines from
  the batch tool, **with their whitespace preserved**. Membership must equal
  the corresponding group exactly. Short hashes use the production formula:
  SHA256 of sorted stripped lines joined by newline, no trailing newline,
  truncated to 12 hex digits. Optional `expected_fingerprints` must match.
- `system_params` including the observed `const.ohos.fullname` value.
- Complete installed APK package and required OH host-HAP inventory: package, observed version name
  and code, actual board APK path and SHA. `apk_hashes` supplies independently
  observed installed-file hashes. Every selected manifest app must match all
  three identities, and active BoatAttack and the Route B host must be installed.
  The existing selfcheck's `apk_path` field also accepts the installed host HAP
  archive path (it hashes bytes and asks BMS for that host's versionCode).
- Optional exact inventories/globs to detect extra effective runtime/overlay
  files. Every inventory path requires a sealed SHA. The current selfcheck
  checks each declared package; it does not independently enumerate new package
  names or compare versionName (versionCode + APK SHA are its identity checks).
  Thus snapshot completeness is a collector assertion, not invented here.

Read-only collection operations are `sha256sum`, `bm dump`, `param get`, and
boot ID reads. The snapshot template is **not** runnable collection code and
does not replace fresh return-code/transport evidence from cx-t0.

## Overlay slots

`overlay-inputs.json` contains exactly two slots, initially **pending**:

1. `toutiao-route-b`: route B, embedded Android package/APK identity, exact
   `ttbundle` member targets and SHA, including the embedded APK itself. Its
   BMS-registered host is **org.westlake.imehost**; com.ss.android.article.news
   need not be registered with unified BMS. Host HAP identity is sealed through
   `packages`; embedded APK identity through `files.overlays`. Evidence:
   `benchmark/2026-10-09-demo-toutiao/spare-5cd/overlay-manifest.md`, rows 1–6.
   Use persistent host-sandbox paths in the overlay snapshot, not B's private
   `/data/local/tmp/asx` alias from another namespace. No replacement of the
   common runtime generation is inferred. Route B launch/acceptance still needs
   a reviewed SAFE recipe: original scripts can kill main appspawn-x.
2. `boatattack`: one new runtime JAR + exactly three private native members,
   installed package and exact effective target SHA. The shared JAR replacement
   must also be reflected in the effective runtime fingerprint group.

Active slots require APK/version identity and pinned source and rollback descriptors. `absent` requires
an explicit reason and no member files. `pending` hard-refuses sealing; omission
cannot quietly turn an unfinished overlay into a sealed success. No paths, SHA,
APK identity or source provenance are guessed from the preliminary experiments.

```sh
python3 benchmark/2026-10-09-demo-baseline/t5/build_seal.py \
  --snapshot "$FINAL_READONLY_SNAPSHOT" --overlays "$FINAL_OVERLAY_INPUTS" \
  --manifest benchmark/2026-10-09-demo-baseline/demo-manifest.json \
  --out benchmark/2026-10-09-demo-baseline/t5/seal.json
bash scripts/lab/demo_selfcheck.sh --seal "$DEMO_SEAL" \
  --serial 61b0657200000000000000000324012c --out "$FRESH_LIVE_RECEIPT"
```

The compiler requires a fresh output, records all three input SHA, and prints
`SEAL_COMPILED_OFFLINE`. Subsequent live selfcheck remains mandatory. Final
seal creation is not final screenshot/interaction signoff. Restore rehearsal,
AGENTS registration and the runbook remain the other lanes/outer's t5 work.

Known answers and raw stdout/stderr are retained under `evidence/`. Changes stay
in the lane worktree for outer landing if Git metadata remains read-only.
