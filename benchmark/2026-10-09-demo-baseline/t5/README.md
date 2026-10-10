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
2. `boatattack`: the earlier tentative shape was one new runtime JAR + exactly three private native members,
   installed package and exact effective target SHA. The shared JAR replacement
   must also be reflected in the effective runtime fingerprint group.
   This is not a final PR03-port admission. If the accepted port changes that
   shape (for example four private members without a JAR swap), outer must review
   the compiler's shape constraint before final sealing; never replace a frozen
   JAR merely to fit an old template.

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
seal creation is not final screenshot/interaction signoff. The offline runbook
and restoration driver are now supplied below; live restore rehearsal, final
seal and AGENTS registration still require outer/user handling.

Known answers and raw stdout/stderr are retained under `evidence/`. Changes stay
in the lane worktree for outer landing if Git metadata remains read-only.

## Offline t5 closeout: runbook and restoration driver

`demo-runbook.md` replaces the oc-t4 draft's unsupported claims and guessed tap
coordinates. `runbook-order.json` is generated from the exact outer table and
the same mechanical t3 summarizer: **112 exact lit keys = 86 historical-content
+ 26 historical-empty keys**, with ten lit required games as a subset. The 16
non-lit rows, including OrganicMaps/STK splash, are appendix-only. Every entry
names the next key as its failure fallback. The runbook-signoff input is pinned;
two generations are byte-identical. Route B uses foreground desktop clicks,
not denied `aa start` (10107101); isolated asx-spawner watchdog, refresh and article
steps remain conditional on live acceptance. BoatAttack is explicitly pending
PR03 render-port acceptance, not an approved low-resolution/purple candidate.

`scripts/lab/demo_restore.sh` calls `restore.py`. The default is **dry-run**,
which validates every archived source/provider/rollback SHA and performs only
the actual read-only selfcheck. `--observed` is an offline-fixture mode and is
categorically refused with `--execute`. The disabled template cannot dispatch.
No genuine `seal.json` or enabled restore deployment is fabricated here.

### Restore deployment/provider interface (pending real bindings)

An enabled `demo-restore-deployment/v1` has:

- `files`: exactly every seal file and installed APK/HAP archive, each with
  `target`, `mode` (restore or verify-only), and `source:{path,sha256}`. Source SHA
  must equal the seal's expected SHA. Relative paths resolve against the
  deployment JSON, or use `$WORKSPACES/`. Missing/extra targets refuse.
- `providers`: one ordered `u13` base adapter, followed by active
  `toutiao-route-b`, then active `boatattack`. Each has `interpreter` (python3 or
  bash), pinned `program` and `rollback` objects, and exact disjoint mutable
  `targets`. The active overlay list must agree with the seal. Providers must
  be independently reviewed; a SHA pin is identity, not proof of safe behavior.
- Provider argv is `INTERPRETER PROGRAM --seal SERIAL_PROJECTED_SEAL --serial
  SERIAL --deployment DEPLOYMENT_JSON --out FRESH_STEP_DIR`. The provider must
  retain fresh ticket/lock/native/frozen/mount/parent/child guards, validate its
  archived inputs before board writes and preserve a journal. This driver never
  recreates a namespace/mount writer or silently relaxes those gates.

`--execute` additionally requires a fresh `demo-restore-authorization/v1` with
`authorized:true`, exact original `seal_sha256` and `deployment_sha256`, serial,
`valid_until` (timezone-bearing), external `holder` and current `boot_id`.
For the demo board, `authorized_by` must be `user`; outer cannot unseal it.
For `--rehearsal` on a different whitelisted board, signer is `outer(claude)`.
Only the serial is projected into a fresh host-side seal; the original seal
bytes and every other identity stay unchanged.

Precheck must have reliable reads, stable boot, equal system parameters and
immutable stock-installation prerequisites; incomplete observations refuse,
not become repair permission. Each provider starts only after the held owner,
boot, input-document SHA and source/provider hashes are rechecked. Final
read-only selfcheck must match all groups, package versions/APK SHA and declared
inventories. Failure preserves logs/external lock and requires outer review;
no automatic rollback/unlock, no kill of the main appspawn-x, no OS replacement.
Provider stdout/stderr and argv/rc are stored raw under the fresh output folder.

Outer's pending base choices are **alternatives**, not two base writes:

1. cx-t0 fresh-ticket U13 replay, master `5a172dd057`,
   `benchmark/2026-10-09-demo-baseline/t3/restore5cd-u13-ticket/`.
   Fresh native ticket → 319-path diff{} → parent/child/single ART → HW/ZZ t20.
2. cc-wiki `benchmark/2026-10-10-u13-autostart/payload/scripts/install-westlake-u13-autostart.sh`,
   5cd real reboot proves the mechanism only; not yet master or a sealed provider.

Choose and adapt one, then bind Route B and BoatAttack layers separately to the
final seal. Spare-board host libraries/mount behavior cannot be extrapolated to
61b's physical system files. Neither pending adapter is invoked by this task.

### Four scenario accounting

| t5 scenario | Offline evidence | Still pending |
|---|---|---|
| Selfcheck equals seal | Actual CLI generated fixtures / OFFLINE_MATCH | Final live snapshot + live selfcheck |
| Restore rehearsed | Mock replay from SHA-checked archives; read-before-write, serial-only spare projection, ordered three layers and final OFFLINE_MATCH | Enabled sealed providers + real spare-board rehearsal and screenshot review |
| Drift detected | Actual CLI returns nonzero and prints exact path + expected/actual SHA | No live mutation needed or authorized |
| Runbook order/fallback/steps | Exact-lit coverage, content-first, ten games, every fallback, Toutiao and pending Boat section | t4 stability, special-app live acceptance and final seal enablement |

The `demo_baseline_seal` Rust selector runs these Python known answers and
prints `OFFLINE_ONLY`. A passing fixture/selector is not proof that the Restore
scenario's real-board prerequisite has been achieved. This task performs zero
board/VM/SSH access, no AGENTS change and no seal/promotion authorization.

`fixtures/selfcheck-seal.json` and `fixtures/selfcheck-drift.json` are explicitly
synthetic offline fixtures, not a real sealed deployment. The latter changes
only the runtime-file SHA from a×64 to e×64. `evidence/drift-cli.txt` is the actual
CLI's raw output with rc=1; it prints the full path and both full hashes.
