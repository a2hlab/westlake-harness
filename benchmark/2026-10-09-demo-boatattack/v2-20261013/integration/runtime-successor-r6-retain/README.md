# Bounded f28 experiment with root-stepped Boat input — disabled

The previous supplement rejected a new `WATER_FACING_COURSE` prerequisite before any five-touch evidence. That prerequisite is not a t2b acceptance rule. This sibling removes it; it does not claim that the original R6 partial result or the timed-out supplement passed.

Real source: main `outer/r6-interactive-readonly`, boot `14a4b932-f396-40fa-864c-543c47b99875`, restored947 and four actual controls. Reviewed40f0 successor and landed19b3 rebind are reused. Three atomic source replacements, seven binds, full319, all backups/preimages, partial-bind recovery, snapshot/policy and HW/ZZ remain. No runtime rebuild or61b operations. The generated hook and runner are new siblings, not modifications of a running or frozen window.

## Root execution sequence

Run on Mac with `WORKSPACES` and `MAC_HOME` set. After landing, regenerate under main, using the actual capture (or a NEW capture if the board has rebooted again). Do not execute the T4 review example as a main-bound plan.

```sh
I="$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration"
O="$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer"
python3 "$I/runtime-successor-r6-followup/rebind.py" --capture-root "$O/r6-interactive-readonly" --out "$O/r6-interactive-derived" --prepare-out "$O/r6-interactive-main"
python3 "$I/runtime-successor-r6-retain/prepare_retain.py" --window "$O/r6-interactive-main"
```

Root reviews and signs the newly generated `authorization.required.json` in a separate file. Original holder, static evidence, both coldboot permissions, independent request/hook pins and20+10 deadlines are unchanged. Additional fields:

- `allow_retain: true`, `retain_scope: "bounded-experiment-not-promotion"`.
- `retain_until_epoch <= min(experiment_expires_epoch, rollback_expires_epoch - 600)`.
- `recovery_watch.registered: true`, `responsible: "outer(codex)"`, `start_by_epoch <= retain_until_epoch`, `plan` exactly the generated pinned `recovery_plan`, and `registration: {path, sha256}` of root's actual timer/observer registration receipt. No registration means no retention. These are root attestations, not an autonomous timer supplied by this package.

Root MUST register the recovery observer in the same window. It must start recovery by `start_by_epoch` unless root has explicitly handed the exact retained boot/deployment to a NEW independent batch authorization after actual game PASS and T0 fresh337 admission. Expiry of this experiment never authorizes eight full128 windows. Retain is not promotion or seal acceptance.

After root supplies the independent file and full SHA:

```sh
export R6_AUTH="$O/ROOT_SIGNED_EXPERIMENT.json"
export R6_AUTH_SHA=ROOT_COMPUTED_FULL_SHA
python3 "$WORKSPACES/westlake-harness/scripts/lab/board_run.py" "$O/r6-interactive-main/board-run.disabled.json"
```

The old board_run does not enforce the decorative `execution_enabled` field itself; the pinned hook authorization does. Never run these plans with placeholders. After-lock applies three sources, snapshots/policy-checks, coldboots and verifies319/7bind/3source, then launches Boat under the original APK/UID/PID/birth/parent/geometry guards. The original3+6+6+15 capture cadence stays; there is NO reset or heading precondition. The input phase only waits for root's local step files, within the original240-second runner budget. Up to20 entries, including `finish`; no arbitrary coordinates/commands.

At `run/boat/record.json` status `WAITING_FOR_ROOT_STEP`, read `ready.jpeg`. Root may now request left first, inspect `step-1-after.jpeg`, then right and inspect the next image. Repeat only the commands needed to establish steering and LAP; water/land state is observed, not assumed.

```sh
R="$O/r6-interactive-main/run/boat/record.json"
python3 "$I/runtime-successor-r6-retain/step.py" --record "$R" --action left --write
# Read image and wait for next_step to advance, then:
python3 "$I/runtime-successor-r6-retain/step.py" --record "$R" --action right --write
# Same interface: --action accelerate or --action reset.
python3 "$I/runtime-successor-r6-retain/step.py" --record "$R" --action finish --disposition retain --write
# Choose --disposition rollback instead to request original recovery.
```

The helper defaults to preview, pins actual record identity, publishes one immutable local request atomically and has no HDC code. Each device input uses the existing source-derived command with boot/child/PID/birth/parent, all seven child-view SHAs and geometry rechecked. No process kill/relaunch occurs between steps. Timer expiry, missing input, failed guard or failed HW/ZZ runs original947 recovery. Success only produces `BOUNDED_EXPERIMENT_NOT_PROMOTED`, with `game_pass: false`; root visual judgment is a separate attachment.

## Mandatory recovery on expiry or failure

Automatic failure uses the original before-unlock source rollback, snapshot/policy, coldboot947,319/7bind/3source and HW/ZZ. After successful temporary retention, root's registered observer runs the generated recovery plan. It uses the same original transaction/backups; never fresh-install or overwrite a mapped source inode. Recovery gets a new lock, both phase auth pins and its own output root. Its final hook checks actual recovery HW/ZZ and read-only full identity; failure retains the lock.

Root creates a new independently pinned authorization from the same request, `allow_retain: false`, and `recovery_receipt: {path: .../run/retained.json, sha256: ACTUAL_SHA}`. Original origin boot stays14a4; current boot is read by the existing executor. Root sets valid recovery deadlines and does not mutate prior authorization or receipts.

```sh
export R6_RECOVERY_AUTH="$O/ROOT_SIGNED_RECOVERY.json"
export R6_RECOVERY_AUTH_SHA=ROOT_COMPUTED_FULL_SHA
python3 "$WORKSPACES/westlake-harness/scripts/lab/board_run.py" "$O/r6-interactive-main/recovery-board-run.disabled.json"
```

Direct hook entry under an already valid root-held window is `retain_hooks.py recover-retained --request .../request.json --authorization ... --authorization-sha256 ...`. The independent recovery plan performs original HW/ZZ once in the rollback body and again at the ordinary board_run smoke gate; this conservative duplication keeps the unmodified board_run contract. Original `closed.json` is preserved; later recovery writes `recovery-closed.json`. No timer process is started by offline preparation. Root owns registration, observation and timely dispatch.

## T0 handoff

Use `SYNC-T0.md`. Keep the existing full337 artifact proof and its eight-window driver; do not rebuild or bypass identity. `retained.json` indexes exact enabled plan, transaction, intents/placements, original apply rc/raw, boot intent/result,319/7bind/3source and HW/ZZ. Actual game PASS plus first-window popup PASS and NEW independent fresh337 admission remain prerequisites to batch promotion. A successful experiment-retain receipt alone is insufficient.

Local verification: seven targeted tests, actual runner CLI preview (zero device commands), real five-key input resolves and original62-target snapshot validator. Human and live execution remain pending. No device commands were run by T4.
