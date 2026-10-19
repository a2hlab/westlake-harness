# ACK — toutiao icon-reentry (inner CC), token ACK(91-1919-icon)

Offline delivery only. No device operations by this lane; board not touched; not deployed.
Not a crash fix — adds manual desktop→home icon reentry on top of the sealed 61b baseline.

## Delivered (this lane's scope: parser, generator, base inputs, tests, docs, manifest/diffs, spec selector)

- Adopted the outer-reviewed WMS parser verbatim into `src/reentry-seams.sh`
  (`febc7094b9d90b6a8c6c305199395d92da1ccde42d2b82b8c2754f0cb60f9d04`). Left the
  adapter-owned `src/reentry-common.sh` (`43d7b073…`) and `src/watchdog-reentry.sh`
  (`bd2f83be…`) unchanged.
- `generator/derive-candidate.sh` + `base-pins.json` + `base-ref/` — deterministic,
  clean-checkout generator; verifies 19/19 base pins (V 12 + R 4 + base-ref 3); never
  reads untracked capture-feed; default DISABLED; `--enable --approved-by 'outer(codex)'`
  to arm; refuses non-`icon-manual-` ROOT and `--enable` without approval.
- `candidate-payload/` — committed DISABLED payload (21 files, 15 members) with
  `MANIFEST.sha256`, `generation.json`, base→candidate `diffs/`, `build.log`.
- Tests: `tests/run-parser-tests.sh`, `tests/run-reentry-tests.sh`, `tests/run-all.sh`,
  `tests/outer-fixtures/actual-61b-locked.wms.txt`, raw `tests/last-run.log`.
- Spec selector `tools/spec-checks/tests/toutiao_icon_reentry.rs` (transcalls run-all.sh).
- Docs: `README.md`, `OPERATIONS.md` (deploy/arm/rollback + restart/first-launch
  boundary), `CHECKPOINT.md`.

## Offline results (raw: tests/last-run.log)

- WMS parser: **21 passed, 0 failed** (real locked dump + synthetics + error paths).
- Reentry state machine: **29 passed, 0 failed** on `sh` and `dash`.
- Generator smoke + SHA cascade linkage: **PASS** (21 files; members==STARTUP_MEMBERS_SHA;
  startup.expected==sha(startup.env); entry.sh carries candidate watchdog sha; disabled).
- `cargo test --test toutiao_icon_reentry`: **ok, 1 passed**.
- `agent-spec lint t1-reentry.spec.md`: **100%** (det/test/cov 100%, ≥0.7 gate).

## Candidate SHAs

- ROOT `/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r1`
- watchdog.sh `bd2f83be…`, members.tsv `6d96deca…`, startup.env `da40b9c2…`,
  startup.expected `da40b9c2…`.

## Pending (outer / real board)

- Spec scenario 5: real-board screenshot acceptance (crash→manual tap→feed; reboot→manual
  tap→feed) with process identity + capture receipts.
- Outer cfg deploy/arm/rollback transaction under board lock.
- On same boot, parent 11444 is alive: bring online via **fresh boot only** (the sole
  execution path this round; no reviewed attach implementation exists, so none is
  offered) — never clear the socket or signal the parent (OPERATIONS §4).
- Deploy binds to the real transaction `benchmark/2026-10-19-toutiao-icon-deploy/`
  (`prepare.py` + `deploy.py`): existing cfg `/system/etc/init/01_westlake_u13_toutiao.cfg`
  keeps service/trigger/permissions, only the boot-entry path is repointed; the payload's
  `recovery.cfg` is not installed; rollback restores `before.cfg` and never deletes the
  candidate ROOT evidence (OPERATIONS §3, §5).

Commit SHA: see board line (committed on branch `analysis/toutiao-icon-reentry-20261019`, not pushed).
