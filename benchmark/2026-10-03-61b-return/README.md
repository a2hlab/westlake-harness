# 61b reconnect: evidence first, existing executor recovery

## Corrected assumptions

Window2 left61b **locked, detached and active_verified**, not restored. The journal is at `window2/u14-A2-20261003T131427/61b/transaction/transaction/journal.json`: the doubled `transaction` is real, from the original hook's root argument. Do not construct the shorter nonexistent path. `binding.json` pins the original journal SHA256 `f24718730ccd4165d876a411daf0d717630311de0ac2a1c5b1c20923c8ebde67`, the plan/hook/recovery/smoke, trusted wrapper/tools and U13 armed bundle.

Old boot is `2f4be4aa-e0ed-4208-8cfe-db5f1b31bee4`, read successfully immediately before the13:50 disconnect. A changed boot is evidence of a restart, **not evidence of restoration**: candidate bind layers may have disappeared. `u7_executor.py:328` checks old boot ownership during rollback; changing the journal's boot field would be incorrect. The outer explicitly approved the existing new-boot `replay_baseline` function at `scripts/lab/u7_executor.py:216`, exposed by CLI **`--restore-baseline`**, with a new journal and identical recovery checks. No new recovery implementation or boot-guard bypass is added.

The61b original signed plan, `recovery-u13.json` and restored smoke all specify runtime **`452447a4a0ba`**, boot **`ee927db88a67`**,321 assertions and319 paths. Common boards use runtime `821de739cf81`; copying that fingerprint to61b would contradict its signed identity (two retained51e1 installers). The outer explicitly confirmed61b armed `0a31ad35` equals unarmed `8861a11a` content, and instructed preserving4524. Neither variant declares a screenshot lit.

## Sequence and refusal boundary

Default mode is a disabled, local JSON preview. It does not query HDC, holder files, VM or SSH and makes no output directory. Only `--outer-execute` enables the following sequence for the full exact61b serial, never another board:

1. Check original source hashes; create a fresh attempt. Read `hdc list targets`, boot_id, uptime, complete fault-file mtime inventory and available `hilog -x`. Every shell read requires a terminal remote status marker; rc0 plus empty output is a transport failure, not success. Receive cppcrash/jscrash selected by mtime or a filename timestamp in **2026-10-03 13:45:00–14:00:00 +08:00, inclusive**. Archive original stdout/stderr, every rc, file SHA and availability. Missing logs are explicitly unknown, not proof of no crash. No device-side log clearing, dump file, mkdir or file send occurs in this step.
2. Verify the original journal is still active_verified and matches serial/old boot. Require the existing cx-t0 holder with window2 timestamp **2026-10-03T13:29:28+0800**, re-read boot for stability, then dispatch through the unchanged production `run-executor.sh` and its original VM environment.
3. Same boot: `--rollback --serial ... --lane cx-t0 --journal <original double-transaction journal> --out <fresh report>`, exactly as `window2/61b/window_hook.py:55`. New boot: `--restore-baseline --from-journal <original> --journal <fresh replay-journal.json> --serial ... --lane cx-t0 --out <fresh report>`. The existing engine verifies recorded persistent source SHAs and mount ownership; no hand-written bind fallback is provided.
4. Existing hook `--verify-base`:321 assertions,319 unique paths, `diff={}`, `absent=[]`, exact per-board runtime/boot fingerprints, current boot, fresh parent/child views and single-ART map gate. Then existing `activation_smoke.py` with the original61b restored spec: HW and ZZ controls plus every marker/view/copy check must pass. Repeat full identity/process verification after smoke.
5. Recheck current boot and original cx-t0/window2 holder; only then UNLOCK61b. Confirm rc1+empty holder. Any failure before UNLOCK leaves the original lock untouched. If the actual unlock was attempted but its follow-up query is ambiguous, report **unknown lock state**, never falsely claim the lock remained held or recovery succeeded.
6. Print, **do not execute**, the remaining fd-seal and AntennaPod sixth trial and the gate-batch application (only when all three boards are unlocked).

Any transport, file/hash, source, holder, executor, identity, process-view or smoke refusal stops immediately. Raw original outputs and `result.json` persist; no shared HDC/VM restart, candidate apply, automatic retry or unrelated board operation is attempted. A partially restored/rebooted attempt requires outer review, not deleting its journal or reusing an output directory. This wrapper is Mac-side; existing rollback/restore and process verification use a2hlab when the outer executes it, not during lane tests.

## Outer command after physical reconnect

Preview:

```sh
WORKSPACES="$HOME/orca/workspaces" bash "$HOME/orca/workspaces/westlake-harness/benchmark/2026-10-03-61b-return/return-61b.sh"
```

One-command disposition, run by the outer/cx-t0 only:

```sh
WORKSPACES="$HOME/orca/workspaces" LAB_HOME=/home/alvin MAC_HOME="$HOME" bash "$HOME/orca/workspaces/westlake-harness/benchmark/2026-10-03-61b-return/return-61b.sh" --outer-execute
```

Optional `MAC_HDC` or `--hdc` selects the Mac SDK hdc executable; default is the existing DevEco path. Optional `--out` must name a nonexistent directory. Scripts use workspace-relative or environment-derived paths, no personal home path literals. Restore and verification logs can exceed the original window; this is the explicitly authorized retained-lock recovery, not a new sampling window.

## Offline verification

`test_return.py` uses **mock HDC and mock executor**, not a real device. Known answers cover both recovery branches, evidence-before-write ordering, rc0/empty disconnects, crash interval boundaries, raw-output retention, exact source binding, original window ownership, wrong common fingerprint/count/view, smoke failures, changing boot, failed replay/rollback, ambiguous unlock and printed-only follow-ups. Tests need no ignored `.artifacts` and invoke no VM/SSH. The Rust selector is `sixty_one_b_return_guards`; `validation.json` records fresh Python/cold/Rust/lifecycle/shell/preflight results. Real recovery remains unexecuted and screenshot verdict remains outer-only.
