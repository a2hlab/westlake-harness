# T37 fast-reopen missed-edge replay

**Three observations reproduced, 0/1/0 mock spawns, all shell rc=0; the missed-click and no-manual-event cases have byte-identical loop traces.** Passing this replay proves the modeled coverage gap, not a repaired UI or the cause of the historical device white screen.

The earlier 18 safety assertions / 165 assembly checks establish neither sampling completeness nor normal-reentry liveness. This packet adds only three bounded common-function cases and reruns none of those suites.

| Case | History before / during sampling | Observed mock spawns |
|---|---|---:|
| missed_during_supervision | Child exits; desktop and manual icon occur while supervision does not sample focus. Loop receives host only. | 0 |
| desktop_then_host | Loop receives desktop, then host, then repeated host. | 1 |
| host_at_start_no_manual_event | No manual event; host already focused. Loop receives host only. | 0 |

## Exact production object and reuse

Main implementation commit: `db5ebfa0c136d41d346f5054156b05244f90f2e3`.
`common.snapshot.sh` is an unchanged byte copy of
`benchmark/2026-10-21-manual-video-regression/host-reentry-candidate/src/reentry-common-r4.sh`,
SHA-256 `b806eb6c1bb390be357f2ac689024bf3947217611bf637850cfc65e7538681c9`.
The runner rejects a mismatched pin before execution and checks unchanged bytes afterwards.

Fixture pattern reused from existing peer `replay.py`: mock sleep, post-spawn supervision and scripted focus. Its exact source hash is in `source-pins.json`. No watchdog fixture is imported. Only production common functions are sourced; every interaction seam is locally defined. Mock spawn counts a function call and changes an in-memory variable; it never launches an app. The epoch seam is a refusal stub and receives zero calls. No real process signal, proc read, socket, device, VM, environment-field read, T38 code or permission change is involved.

Production context (read-only source audit, **not executed here**): r4c watchdog SHA `c73dadb3c0d6ba082c030d7c1096810129b5afec7e3aced4d896dce86e59f0e5`, lines 627–695 supervise without calling focus sampling and sleep three seconds at line 693; lines 760–765 enter reentry only after monitoring returns. Common lines 45–46 start UNARMED; lines 97–104 consume a host without DESKTOP_SEEN. The supervision history in this replay is explicitly modeled, not a timing measurement or an execution of monitor_child.

Existing epoch fixture `tests/run-epoch-tests-r4b.sh:40,130–136,159` removes waits and delivers desktop/host only when polled, after retirement. Existing retirement suite `run-retirement-tests.sh:44,59` likewise advances scripted focus on calls. Those tests cannot lose a desktop interval between focus samples. This packet supplies the resulting host-only observation deliberately; it does not claim a complete asynchronous UI simulation.

## Why a simple initial arm or automatic restart is unsound

After `LOOP_BEGIN`, the missed-history and no-event-history raw outputs are byte-identical. Both have child=gone, no owned window, valid mock gates, and four host samples. A common-only decision based on those observations cannot recover the click history. Pre-setting DESKTOP_SEEN would qualify the first host in **both** cases; blindly restarting on child exit / host presence also admits the no-manual-event case. That would break the existing no-automatic-restart behavior. No such modification or weakened gate is implemented or executed here; further decisions belong to outer.

## Reproduction and retained originals

From this package directory: `python3 check.py --run-id run-02`.
Use a new run ID each time: existing evidence directories are never overwritten.
Original execution is `run-01/results.json`, three `run-01/*.stdout.txt`, and `execution.json`.
Raw files were opened **before** subprocess execution and written directly during execution:
`.private/run-01/<case>.stdout`, `<case>.stderr`, `<case>.command.json`, plus
`.private/runner.stdout`, `runner.stderr`, `runner.command.json`.
Public results include exact argv, rc, UTC timestamps, raw paths, byte sizes and SHA-256.
All four original stderr files are empty and remain private; they are not committed per AGENTS.
The bounded stop after four samples is a fixture termination, not a real app stop.

No production file, old test, safety gate, T38 artifact or original 18/165 evidence was modified.
No device acceptance, deployment permission or current-board-state claim is made.
