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
`--approved-by 'outer(codex)'` is refused. The generator verifies every base source
against `generator/base-pins.json` and fails closed on any mismatch; it never reads
the untracked capture-feed payload. Output is deterministic (identical `MANIFEST.sha256`
across runs). `prepare.py` must see `STARTUP_ENABLED=1` and
`STARTUP_APPROVED_BY='outer(codex)'` before it treats the payload as armed.

Outputs under `<OUTDIR>`: `payload/` (21 files), `MANIFEST.sha256`, `generation.json`,
`diffs/` (base→candidate unified diffs), `build.log`, `build-command.txt`.

## 2. New durable ROOT, isolation from the sealed boot

The candidate deploys to a **new** ROOT (`icon-manual-20261019-r1`), distinct from the
sealed `r1-9763171a-preview`. `boot-entry.sh` does `mkdir "$ROOT/boots/$BOOT"` and
aborts if it exists, so the live sealed boot `6944c37e-31a6-4846-8f1f-48088a917153` is
never overwritten. `recovery.cfg` is rewritten with the new ROOT path, a distinct init
service/param (`westlake-icon-manual-20261019`) and condition
(`sys.westlake.demo.iconmanual.ready`) so it cannot collide with the sealed service.

## 3. Deploy (outer, board-locked)

1. Read-only check first; hold the board lock; stage rollback.
2. Copy `payload/*` to `$ROOT/` on device; apply member modes from `members.tsv`
   (scripts 550, `decoder-probe.jpeg` 440); `boot-entry.sh` 550; cfg/data 640; owner 0:0.
3. Install `recovery.cfg` as the init cfg for the new service.
4. Bring it online on a **fresh boot** (preferred): reboot, then set the trigger param
   `sys.westlake.demo.iconmanual.ready=true`. The init job runs `boot-entry.sh`, which
   builds `boots/$BOOT/` and `exec entry.sh`; `entry.sh` waits for the first manual host
   foreground window (first tap) and launches the guardian unchanged.

## 4. Restart / first-launch boundary (read this before same-boot deploy)

Board fact 2026-10-19 (read-only, evidence `$HOME/.local/share/westlake/toutiao-resume-20261019/61b-guardian-details.txt`):
on the current boot the child 13101 exited at uptime 22640; the **old sealed watchdog**
auto-retried and then `START_FAILED`; the original parent `11444` (birth `107387`) is
**still alive**. This is the old guardian's behaviour, not a regression of this
candidate, which is not deployed.

Rules for bringing the new candidate online:

- The candidate **never cleans up the old run's socket and never signals/kills parent
  11444**. `start-parent.sh` refuses when the socket already exists
  (`EXISTING_SOCKET_NO_TAKEOVER`), and the guardian refuses a socket without a verified
  parent identity (`socket_without_parent_identity`). This is by design.
- Therefore, on the **same boot** while parent 11444 / its socket are alive, a fresh
  first-launch (parent=new) will **refuse** — correctly. Do **not** work around it by
  clearing the socket or killing the parent.
- To bring it online, choose one:
  - **Reboot (preferred):** a fresh boot has no old socket/parent; the candidate builds
    a new `boots/$BOOT` and is the single guardian.
  - **Reviewed same-boot attach:** only if outer verifies the live owned parent, pass
    `TT_PARENT_PID`/`TT_PARENT_BIRTH` (and optionally `TT_CHILD_PID`/`TT_CHILD_BIRTH`)
    so the guardian attaches to the existing owned parent instead of starting a new one.
    The ownership guards (`parent_owned`) still gate this; the parent is never signalled.

## 5. Rollback (outer)

The new ROOT is self-contained, so rollback never touches the sealed boot:

1. Remove/disable the new init service and clear its trigger param.
2. Optionally write a `stop` under `$ROOT` (and under `$ROOT/boots/*`) — a stop in any
   candidate boot persists across future boots and makes the guardian refuse.
3. `rollback-inert.cfg` is shipped as the inert cfg form for the service.
4. Remove `$ROOT` if desired. The sealed `r1-9763171a-preview` and its boot are untouched.

## 6. Acceptance (outer, human review — spec scenario 5)

Ground truth is a `snapshot_display` screenshot, not process liveness. Accept only when,
on a real board: Toutiao exits → a real **desktop→home icon tap** brings the feed back
(one tap → one spawn), and a reboot + manual tap also recovers; with the feed screenshot,
the child process identity, and the capture receipts all present. Do **not** claim the
random SIG11 is fixed — this candidate only adds manual reentry.

## 7. Source correspondence & integrity

- `generator/base-pins.json` — SHA-256 + provenance (V/R/base-ref) of all 19 base files.
- `generator/base-ref/` — the 3 mechanical base files (members.tsv, startup.env,
  startup.expected.sha256) pinned so the generator runs on a clean checkout.
- `candidate-payload/diffs/` — exact base→candidate unified diffs (watchdog, entry,
  config-common, recovery.cfg, members, startup, startup.expected) + the two new files.
- `candidate-payload/MANIFEST.sha256`, `generation.json` — per-file hashes + the cascade.
- Final reviewed source SHAs: watchdog-reentry.sh `bd2f83be…`, reentry-common.sh
  `43d7b073…`, reentry-seams.sh `febc7094…`.
