# Diagnostic maintenance plan v3 (spec t48 aa86e07f2) — six ROOT control files on 5cd (plan only; no device write)

Basis:
- T47 package `benchmark/2026-10-22-toutiao-diagnostic-package/package-01/` (main 9e05b0c1e3);
- T46-P2 13-member evidence;
- a fresh read-only check this round: raw under `$HOME/.local/share/westlake/t48p-maint-readonly-20261022/`,
  MANIFEST 4217a0bbb46139c4679dcb19aba286f2f555effb13a3e9f66c78b50996d003e0.

Not used: T38 donor/reentry, rejected debug paths, guardian restarts, third-party kills, owner-gate relaxation, init
cfg edits, stop clearing, a new executor.

## 1. Reader isolation — outer proposal checked against source: ACCEPTED
- `boot-entry.sh:6` sources `config-common.sh` **before** `boot-entry.sh:12` (`mkdir boots`), before the member copy,
  and before `exec entry.sh`.
- `config-common.sh:12` fails `STARTUP_NOT_APPROVED` unless `STARTUP_ENABLED=1`, after checking that
  expected = sha(env) (`:6-10`).
- So a boot with a matching disabled env exits before creating `boots/<boot>` or starting any entry/guardian.
- The isolation proof for a maintenance boot is:
  - a new boot_id;
  - the `boots/` name list after the reboot equals that phase's pre-list, so nothing new appears (the R3 pre-list
    already contains the R2 directory);
  - **no `boots/<new boot>` directory**;
  - a sampled `ps` with no process running *this ROOT's* `entry.sh`/`watchdog.sh` for the current boot. Other normal
    services, including other appspawn-x, may exist.
- The REFUSE stderr sink is unknown (T45-A). The isolation argument rests on the verified source, the disabled
  env/expected hashes, the new boot and the absent boot directory, not on a seen refusal line.
- Also: in the current boot the old executor 3978 has exited (T45-A), but "no reader alive now" is only a sample.
  Hence the maintenance boot.

Sequence, at most 4 normal reboots, each `hdc -t <serial> target boot`:

| step | write (each via fresh stage → `.new` → same-dir rename) | reboot | must hold after reboot |
|---|---|---|---|
| M1 | `startup.env` ← maint-forward, then `startup.expected.sha256` ← its SHA | R1 | new boot, no new boots dir (isolated) |
| C1 | watchdog, route-b-owner, entry, members (T47 candidate) | — | — |
| C2 | `startup.env` ← candidate-enabled, then expected **last** | R2 | new boots dir; copied members SHA = candidate |
| M2 | `startup.env` ← maint-reverse (= T47 exact disabled) + expected | R3 | isolated again |
| B1 | watchdog, route-b-owner, entry, members ← T47 `rollback/` | — | — |
| B2 | `startup.env` 44993dbc… then expected 05c12ce3… **last** | R4 | new boots dir runs baseline; 13 members + 9 controls = T46-P2 |

## 2. Observation (after R2) and restore check (after R4)
After R2:
- Confirm a normal desktop (layout + `snapshot_display`, T44 rules).
- Tap the Toutiao icon once, normally, located from a fresh layout.
- Check that the candidate boot's copied members equal the candidate SHAs.
- Read `boots/<boot>/{state,events.log,guardian-refusal-*.jsonl}`.
- If no refusal appears within 120 s, record "not observed". This is not proof of absence.

After R4:
- Confirm a normal desktop.
- Tap the Toutiao icon once, normally.
- Verify that the new `boots/<R4 boot>` holds the baseline member copies and that `events.log` shows the original
  guardian actually started.
- A missing directory or missing events means the restore is **not** complete.

## 3. File handling
- Stage `/data/local/tmp/diag-maint-t48-20261022-1748/`, device backup
  `/data/westlake-demo/toutiao/recovery-attempts/diag-maint-t48-20261022-1748/backup/` (outside ROOT), and
  `ROOT/.<name>.new` are all created fresh.
- Parent directory identity (dev/ino/mode/uid/gid plus `ls -Zd` of `/data/local/tmp` and `…/recovery-attempts`) is
  read at preflight and rechecked before each write; a mismatch stops the window.
- **Refuse** if a path already exists or is a symlink.
- Preserve the original mode/uid/gid and SELinux label `u:object_r:data_file:s0` per file (`chmod`/`chown`/`chcon` on
  `.new` before the rename), then read back stat + `ls -Z` + SHA.
- New inodes are recorded; restoring the old inode is not required.
- Originals are backed up locally (T47 `rollback/`, byte-exact) and on device (the backup copy is SHA-verified).

## 4. Time and failure rules
- Window ≤1800 s from LOCK.
- Start the restore (M2) no later than 1200 s.
- Each boot wait ≤180 s, per the RUNBOOK normal reboot: `hdc target boot`, then the target is present again, the boot_id is new and the desktop check passes. No separate reboot trial.
- Before each write phase, enter it only if the remaining budget covers that phase plus a full restore (M2+B1+B2+R3+R4).
- A lost receipt or missing marker means: read-only check of the current file SHAs and boot to determine the phase.
  **Never blind-resend.**
- A stop marker present before or after any reboot means: stop, keep the lock, report. **Never clear it.**

## 5. ready source — found, fresh SHA now on device
- `/system/etc/init/00_westlake_u13_recover-v3.cfg` (897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762)
  → `/data/westlake-demo/u13/boat-v2-20261013-r4/recover-v3-boat.sh`.
- Device SHA 291451a1a3b821a5527e3c8619d932664d047e25116e9c653d185d2ea5ee878f, the same as the repo
  `…/final-v2-candidate-r2/r4-reference/recover-v3-boat.sh`.
- L224–229: after the Boat bind it sets `sys.westlake.demo.u13.ready=true` and the trigger
  `westlake-u13-toutiao-overlay-start 1`.
- This boat-chain script is not modified. If R1–R4 do not show ready=true, the window stops at that reboot.

## 6. Bytes (full SHA-256; local only, in `bytes/`; no deployment)
| set | startup.env SHA | expected-file SHA (its content = the env SHA) |
|---|---|---|
| maint-forward (baseline, ENABLED 1→0) | d1452d77c0bf654ca6164a3a66082cbee8467238fa430232efb484db9af72476 | d764a774a40c1e1e3a110358f037e142d79522905a6e4d563bd293ffbda9d2bf |
| candidate-enabled (T47, ENABLED 0→1) | 465f5fbe33c6777dadd9f8563e5450b7319f87d18fc69820cabdbad01fbbe0c2 | 49424def57d8f8b9dd96861cdebfc3b86b30d935bf86c5af3974ce30dc947a3e |
| maint-reverse (= T47 exact) | 8e60a99dd81ddc25e3084902d0d95eb8ea2866a9aa1c30dce7b3f5b9f966b8f0 | b43d886b70bd07a040c4fc3403231f1a7d2a07092ccdd642472212576919553b |
| baseline (restore target) | 44993dbc61116a4e67936ddc09af2ca7e19c9b2454599e16da7a2b907681b34a | 05c12ce34fea0a7a3746b4fe7c40b0cb676968ded8b1c21218fafca54a98b037 |

Each env differs from its source only in the `STARTUP_ENABLED` line.

| file | candidate SHA | baseline SHA |
|---|---|---|
| watchdog.sh | bcae2c697ae5ee6e31c836cd38d322d5120a87ffa74f1d35d2c88acca7be818e | 2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a |
| route-b-owner.sh | fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58 | 6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c |
| entry.sh | 1f16bc6b10a306abd1afab88cfcd26801910388da5b057bc1e6084f219da30c8 | 81dd055764b0737f497d1dd9fb8358dd42521360bc6e359c9428c9b2ac8b21a1 |
| members.tsv | 04aa24cf06bef10bcaf765f6e26cfb55922af3ddeb95ee3f624af95838579fae | 328f0af2e95f6d0e33112628706544262c1f80aa1b623a4b987d7f8f129169f8 |

## Restore branches (decided by the read-back phase only)
| verified phase | restore |
|---|---|
| before M1 or M1 partial | write baseline env 44993dbc then expected 05c12ce3; verify like R4 if a reboot happened |
| after M1/R1, before C1 | baseline env + expected (**not** maint-reverse: its members SHA 04aa would mismatch the baseline members) → reboot → verify |
| C1 partial or done, before C2 | B1 rollback of the four files → baseline env + expected last → reboot → verify (the env is still disabled, so isolation holds) |
| C2 partial: bodies and members are candidate, env is candidate-enabled, expected is still maint-forward or its write is incomplete | treat as **not disabled**: write maint-reverse env + expected → read back a match → R3 → verify the R3 new boot and isolation → B1 → B2 → R4 → verify |
| C2 done / R2 or later | M2 (read back a match) → R3 → verify the R3 new boot and isolation → B1 → B2 → R4 → verify |
| M2 partial or M2 written | finish M2 and read back a match. Files written ≠ R3 done → R3 → verify isolation → B1 → B2 → R4 |
| B1/B2 partial | only if R3 completion (a new boot after M2 plus the isolation read-back) is on record: continue B1 → B2 → R4. Otherwise do **not** continue B1; go back to the M2 row |
| unknown (lost receipt) | read-only SHA of the six files + boot_id + boots list → choose a branch; never guess, never blind-resend |

Rule: B1 never resumes from "first file whose SHA ≠ target" alone. It needs a recorded R3 completion.

## Fresh read-only state (this round: 6 read-only commands, 0 writes; boot 8b64b087, no lock)
- All six ROOT files, both init cfgs and the recover script have SHA and stat equal to the known values.
- Labels: ROOT, `boots` and the six files are `data_file`; both cfgs are `system_etc_file`.
- `ROOT/stop`, `selfheal48/stop` and every `boots/*/stop`: ABSENT (the glob matched nothing). 36 boot directories at this read (informational only).

## Evidence scope (A / after R2 / after R4)
- runtime 124 + boot image 36 (T44 argv);
- host HAP SHA and `bm dump` identity; datadir/filesDir stat;
- both init cfg SHAs; recover script SHA;
- 13 members + 9 controls stat/SHA/label;
- `boots/` names and stop checks;
- `param get sys.westlake.demo.u13.ready`;
- power values; a `ps` sample; the new boot's state files.

## Still to bind
- Outer window signature. The `STARTUP_APPROVED_BY` literal is historical and grants nothing.
- Fresh admission and the parent directory identity, both read at window preflight.

Already bound: the stage/backup name `diag-maint-t48-20261022-1748`, and the boot wait per the RUNBOOK normal
`target boot` + new boot_id + desktop check, ≤180 s.

Reusable entries: recorder `$HOME/.local/share/westlake/t48p-maint-readonly-20261022/tools/rec.py`, `board_note.sh`,
`hdc file send/recv`, the T44 power/desktop steps.
