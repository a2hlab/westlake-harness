# OPERATIONS — durable manual icon reentry candidate (61b)

Offline-built, **disabled by default**. This lane (inner CC) produces the generator,
sources, tests and this runbook. **The outer loop owns all device actions** (deploy,
arm, trigger, reboot, screenshot, rollback) under its own board lock. Nothing here
touches the device.

## 1. Generate the candidate payload (host, clean tracked checkout)

Disabled (review) build — the committed copy was produced exactly this way:

```
sh benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh \
   --out <OUTDIR>
```

Armed (publication) build — outer only, with explicit approval:

```
sh benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh \
   --out <OUTDIR> --enable --approved-by 'outer(codex)'
```

Defaults: `--root /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r1`
(the generator refuses any ROOT not under `recovery-attempts/icon-manual-`),
`--serial 61b0657200000000000000000324012c`, `--owner-uid 20011206`,
`--service westlake-icon-manual-20261019`. `--enable` without
`--approved-by 'outer(codex)'` is refused. The generator hash-verifies the 16 base
sources it consumes against `generator/base-pins.json` (the other 3 pins are diff bases
only; see §7) and fails closed on any mismatch; it never reads
the untracked capture-feed payload. Output is deterministic (identical `MANIFEST.sha256`
across runs). `prepare.py` must see `STARTUP_ENABLED=1` and
`STARTUP_APPROVED_BY='outer(codex)'` before it treats the payload as armed.

Outputs under `<OUTDIR>`: `payload/` (21 files), `MANIFEST.sha256`, `generation.json`,
`diffs/` (base→candidate unified diffs), `build.log`, `build-command.txt`.

## 2. New durable ROOT, isolation from the sealed boot

The candidate deploys to a **new** ROOT (`icon-manual-20261019-r1`), distinct from the
sealed `r1-9763171a-preview`. `boot-entry.sh` does `mkdir "$ROOT/boots/$BOOT"` and
aborts if it exists, so the live sealed boot `6944c37e-31a6-4846-8f1f-48088a917153` is
never overwritten. The payload's `recovery.cfg` is a **reference artifact only and is NOT
installed**: the real deploy transaction (§3) reuses the existing init cfg and changes
only its boot-entry path. No new init service, trigger, or permission is introduced.

## 3. Deploy (outer, board-locked) — bound to the real transaction

The deploy transaction lives in the main tree at
`benchmark/2026-10-19-toutiao-icon-deploy/` (`prepare.py` + `deploy.py`). It keeps the
existing init cfg `/system/etc/init/01_westlake_u13_toutiao.cfg` — its single service
`westlake-u13-toutiao-overlay`, trigger `sys.westlake.demo.u13.ready`, and permissions —
and only repoints `services[0].path[1]` from the old `…/r1-9763171a-preview/boot-entry.sh`
to `…/icon-manual-20261019-r1/boot-entry.sh`. `prepare.py` rejects any cfg change beyond
that one path (`a == b` after the swap) and requires an **armed** payload
(`STARTUP_ENABLED='1'`, `STARTUP_APPROVED_BY='outer(codex)'`, matching `STARTUP_SERIAL`
and `STARTUP_MEMBERS_SHA`). It does **not** copy the candidate `recovery.cfg`.

Steps (outer):

1. Read-only check first; hold the board lock; stage rollback.
2. Generate an **armed** payload:
   `sh benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh --out <OUT> --enable --approved-by 'outer(codex)'`.
3. Package the transaction (host, no device):
   `python3 benchmark/2026-10-19-toutiao-icon-deploy/prepare.py --payload <OUT>/payload --before <pulled 01_westlake_u13_toutiao.cfg> --boot <boot-uuid> --out <pkg>`.
   This copies the members, writes `before.cfg`/`after.cfg` (after = before with only the
   boot-entry path repointed to the new ROOT), and `plan.json`.
4. Place the new ROOT and write `after.cfg` to the existing CFG path via `deploy.py`
   (receipt-backed), applying member modes from `members.tsv` (scripts 550,
   `decoder-probe.jpeg` 440; `boot-entry.sh`/`config-common.sh` 550; manifest/startup 440),
   owner 0:0. The service/trigger/permissions are unchanged.
5. **Fresh boot is the only execution path this round.** Reboot; the existing service fires
   on its existing trigger `sys.westlake.demo.u13.ready` and now runs the new ROOT's
   `boot-entry.sh`, which builds `boots/$BOOT/` and `exec entry.sh`; `entry.sh` waits for
   the first manual host foreground window (first tap) and launches the guardian unchanged.

## 4. Restart / first-launch boundary

Board fact 2026-10-19 (read-only, evidence `$HOME/.local/share/westlake/toutiao-resume-20261019/61b-guardian-details.txt`):
on the current boot the child 13101 exited at uptime 22640; the **old sealed watchdog**
auto-retried and then `START_FAILED`; the original parent `11444` (birth `107387`) is
**still alive**. This is the old guardian's behaviour, not a regression of this
candidate, which is not deployed.

- The candidate **never cleans up the old run's socket and never signals/kills parent
  11444**. `start-parent.sh` refuses when the socket already exists
  (`EXISTING_SOCKET_NO_TAKEOVER`), and the guardian refuses a socket without a verified
  parent identity (`socket_without_parent_identity`). This is by design.
- On the **same boot** while parent 11444 / its socket are alive, a fresh first-launch
  (parent=new) will **refuse** — correctly. Do **not** work around it by clearing the
  socket or killing the parent.
- **Fresh boot is the only supported execution path this round.** A fresh boot has no old
  socket/parent; the candidate builds a new `boots/$BOOT` and is the single guardian.
- A same-boot attach is **not offered**: there is no reviewed/audited attach
  implementation in this delivery, so no direct attach operation is provided. (The
  guardian does accept `TT_PARENT_PID`/`TT_CHILD_PID` ownership-gated attach internally,
  but wiring and reviewing that path is future work and must not be performed ad hoc.)

## 5. Rollback (outer)

Rollback restores the original cfg and **never deletes the candidate ROOT evidence**:

1. Restore `before.cfg` to the existing CFG path (repoints `services[0].path[1]` back to
   the sealed `…/r1-9763171a-preview/boot-entry.sh`); service/trigger/permissions were
   never changed. `deploy.py`'s receipts/`before.cfg` are the rollback source of truth.
2. Optionally write a `stop` under the candidate `$ROOT` (and under `$ROOT/boots/*`) — a
   stop in any candidate boot persists across future boots and makes the guardian refuse.
3. **Do not delete the candidate `$ROOT`**: preserve its `boots/*` state, events and
   captures as evidence. The sealed `r1-9763171a-preview` and its boot are untouched
   throughout.

## 6. Acceptance (outer, human review — spec scenario 5)

Ground truth is a `snapshot_display` screenshot, not process liveness. Accept only when,
on a real board: Toutiao exits → a real **desktop→home icon tap** brings the feed back
(one tap → one spawn), and a reboot + manual tap also recovers; with the feed screenshot,
the child process identity, and the capture receipts all present. Do **not** claim the
random SIG11 is fixed — this candidate only adds manual reentry.

## 7. Source correspondence & integrity

- `generator/base-pins.json` — SHA-256 + provenance (V/R/base-ref) of all 19 base files.
  **Verification split (accurate):** the generator itself hash-verifies **16** of them at
  run time (12 `copy` rows + 3 `sed-*` rows config-common/entry/recovery.cfg +
  `base-ref/startup.env`; see `build.log` `pin OK`/`sed-*` lines). The remaining **3** —
  base `watchdog.sh` (2b635ef1, superseded by `src/watchdog-reentry.sh`),
  `base-ref/members.tsv` (5aa8940e) and `base-ref/startup.expected.sha256` (9799ad8e) —
  are used only as diff bases and are **not** checked by the generator. All **19/19** were
  confirmed by the outer loop's independent offline review, not by the generator.
- `generator/base-ref/` — the 3 mechanical base files (members.tsv, startup.env,
  startup.expected.sha256) pinned so the generator runs on a clean checkout.
- `candidate-payload/diffs/` — exact base→candidate unified diffs (watchdog, entry,
  config-common, recovery.cfg, members, startup, startup.expected) + the two new files.
- `candidate-payload/MANIFEST.sha256`, `generation.json` — per-file hashes + the cascade.
- Final reviewed source SHAs: watchdog-reentry.sh `bd2f83be…`, reentry-common.sh
  `43d7b073…`, reentry-seams.sh `febc7094…`.
