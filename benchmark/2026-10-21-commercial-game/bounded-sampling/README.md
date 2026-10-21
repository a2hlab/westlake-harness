# COMMERCIAL-G07 — per-shard bounded startup sampling in board_run (offline)

Contract: `specs/commercial-game-round1/t7-bounded-sampling.spec.md` @ `4fee4336c4`. Source base: main-tree
`scripts/lab/board_run.py` blob `ed2b360b86` (identical in this worktree). No device, no REA.

## What changed

`board_run.py` hard-coded every shard to `--reinstall --hilog --shots 5,20` with bms_batch's default 15 s wait, so a
slow first start (Genshin initialization) was cold-stopped after the 20 s shot. A shard may now set:

- `wait_seconds` — finite number in (0, 120]; passed as `--wait`.
- `shots` — nonempty list (≤ 32) of strictly increasing finite numbers in (0, 120]; passed as `--shots a,b,c`.
- If both are set, `wait_seconds` must be ≥ the last shot.

Validation runs for every shard right after plan loading — before `execution_enabled`, `--dispatch`, the lock or any
subprocess — and refuses with the field name and `no lock taken`. `bool`, strings (e.g. `"5,20;reboot"`), `NaN`
and `Infinity` (which `json.loads` accepts) are rejected. Argv construction moved into `shard_command()`; without
the new fields it returns exactly the old command (no `--wait`). The 120 s cap is stricter than bms_batch's own
300 s `shot_offsets` limit. bms_batch, lock, smoke gate and restore wiring are unchanged.

Genshin follow-up shard: `"wait_seconds": 60, "shots": [5, 20, 60]` → `--shots 5,20,60 --wait 60` plus the
original `--execute --reinstall --hilog --stop-new-keys-at`. Control groups keep their sampling.

## Tests (real argv, offline)

`test_board_run_sampling.py` (5/5): default argv equals the literal pre-G07 construction (with and without cutoff);
60 s case argv and acceptance by `bms_batch.shot_offsets`; fractional/shots-only; 18 invalid values each refused
naming the field, plus wait < last shot; `main()` and `main(--dispatch)` raise REFUSE with `subprocess.run/Popen`
patched to fail, and no output directory is created. Existing `scripts/lab/tests/test_board_run.py` 25/25 (its
detach test mocks `Popen`; the printed pid is fake). Rust: `cargo test --test commercial_game_bounded_sampling`.
Receipts: `$COMMERCIAL_G07_PRIVATE` = `$HOME/.local/share/westlake/commercial-game-20261021/bounded-sampling/raw/`.
