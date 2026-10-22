# T52 independent raw acceptance checklist

Status: **PENDING ACTUAL RAW REVIEW**. This is a local static checklist, not admission, execution authority, full contract PASS, or a white-screen fix claim. Main inspected at `c2bc266eb82ab162224d5888a530400e75c708aa`. The reviewer performed zero device operations and did not access the executor's live output or lock. No helper was executed or modified.

The plan is signed conditionally on fresh admission. `admit.py` is a snapshot comparator, not a transaction/closure verifier. Its rc0 must not be promoted to window success. This checklist follows the contract evidence distinction used by the agent-spec tool-first workflow; no lifecycle/test verdict is claimed.

## Fixed source references

Paths below are relative to main, not this older worktree.

| Source | SHA256 |
|---|---|
| `specs/toutiao-video-playback/t52-owned-exit-fix-window.spec.md` | `2b58cc45f33ddafd0e354083bfa53c642973dbc14777661c8ca8b54269a4a0f5` |
| `benchmark/2026-10-22-toutiao-owned-exit-fix-window/plan.json` | `e59fe6df68b39515602d125197303689413d641573f5d7ff580157279ac7966b` |
| `benchmark/2026-10-22-toutiao-owned-exit-fix-window/outer-review.json` | `f9eeaf28494801e62112144f5b964b83b058529bb8f24e4e3773c5b3b7af9157` |
| `benchmark/2026-10-22-toutiao-owned-exit-fix-window/tools/admit.py` | `decb0f6bf8eaccd1d6123fc43f045ef113e6a80d78e5dba2e469b495589ea5bf` |
| `benchmark/2026-10-22-toutiao-owned-exit-fix-window/tools/env.sh` | `a0f74a41742f42050c970351f4aae051409befb95192c0018161fb04b7c1ed73` |

`outer-review.json` binds plan `e59fe6df…`, env helper `a0f74a41…`, board `5cd1e3dd00000000000000000923012c`, lane `herdr-t52`, and a single bounded window. Actual raw is expected under `$HOME/.local/share/westlake/t52-owned-exit-fix-window-20261022/raw` (`tools/env.sh:4`); receipt paths must be supplied by the executor, not invented from the table below.

## Review each obligation against actual raw

All boxes are deliberately unchecked. For each, record raw relative paths, SHA, start/end time, actual rc and observed result. Missing, truncated or ambiguous output is UNKNOWN, never an inferred PASS. Check command bodies as well as transport rc; retain every failed attempt.

| Check | Required actual evidence / decision |
|---|---|
| [ ] Input and fresh admission | Exact signed plan/helper/package receipt/source-lock and 12 candidate/rollback bytes; fresh serial and boot `1b1febea-2d14-4717-8770-7b2de4cbcfbf`; complete nine controls/13 members, ready cfg/script, HAP b189, UID/token, directory identities, power, stop markers and absent new tag. Review every snapshot command rc separately. Historical preparation is not lock-time admission. |
| [ ] LOCK origin | Actual successful `board_note lock` argv/start/end/rc and holder `herdr-t52`; reconcile `LOCK_EPOCH` with that real acquisition, never shell restart or later phase. Before-lock held rc1/empty is separate from held-by-us evidence. Bind4 must precede creation; the lock receipt must precede the first write. |
| [ ] Every write | Enumerate mkdir/chmod/backup, transfer, replacement, env/expected, reboot, UI/power writes from original argv. Each needs its own rc/body, guard evidence where required, and readback. Do not use the last wrapper rc. Nonzero/unknown writes require read-only state determination, not inferred resend authority. Check actual budget before mkdir/backup (guard4 alone has no budget test). |
| [ ] Stage/backup and metadata | Original absence/non-symlink proof; bind4 then bind7 identity/labels; six backup SHA equal rollback. Each replacement uses fresh temp/stage names and records final SHA, mode 550 or 440 as specified, UID/GID 0:0, label and actual new inode. Parent identities stay bound; a new file inode is not inherently drift. |
| [ ] Per-phase boot | Build a chronological P0/R1/R2/R3/R4 ledger from boot UUID/uptime/time raw and PHASE_BOOT updates. Each performed reboot has target rc, BOOT_T0 and terminal observation within 180 seconds; no resend after unknown. R1/R3 require new boot, ready=true, unchanged boots list, absent new boot directory and no process referencing ROOT. Isolation marker files alone are insufficient. |
| [ ] Candidate binding | Four candidate bodies match T51; candidate-enabled env SHA `06b743715795db47a7623f624b22bf317dcf4d3f571101e78e9e5e168883140f` and expected-file SHA `64de20fe9e945a70a4d25819db60decafde02a81a4fe837d80fbe70e90a09a43` are different from the disabled package pair. Verify expected *content* separately. Bind actual R2 boot copies of watchdog/owner/entry, members/config references and observed guardian process to this boot; ROOT hashes alone do not prove executed copies. |
| [ ] Observation | Actual desktop layout/window/screenshot supports the exact target and one candidate icon click; observation <=180 seconds. Attribute events/refusals by boot/instance/sequence/time. No natural exit means NOT TRIGGERED, not exit-classification success. READY/RECOVERING/classifier text never substitutes for pixels. |
| [ ] 1200/1800 deadlines | From the one real LOCK origin compute actual restoration start <=1200 seconds and unlock <=1800; enumerate actual reboots (<=4). Check per-action remaining budget, not only the helper's 120/60-second threshold. Retain any deadline violation rather than resetting epoch. |
| [ ] Six controls / 13 members restored | Exact six rollback SHA and env/expected order; complete 13-member target set (four controlled script members plus nine additional members), path-by-path SHA/mode/owner/labels. Record actual new inodes. Baseline boot-entry/config/init must remain unchanged. Selected counts or nine additional-member lines do not alone establish all required metadata. |
| [ ] Runtime124 / boot36 / host | Exact path sets and 124/36 complete SHA rows against pinned preimage, with successful original command receipts; no missing/duplicate paths. HAP, bundle UID/token, data directory identity, ready cfg/script and ready=true must match on final boot. |
| [ ] Final UI and power | R4 actual baseline copies, one normal icon tap, original SUPERVISOR_STARTING; final screenshot bytes/hash/time, matching boot/window context and human visual verdict. White remains WHITE. Verify final power Timeout=10000ms and OverrideTimeout=10000ms from valid PowerManagerService output and compare the agreed power preimage; help text or old snapshot is not evidence. |
| [ ] Closure / retained objects | Six `.new` paths absent; old stop/boot/audit/lock/data objects retained. T52 stage/backup may remain only with exact path, identity, metadata and reason, separately from stale temps; T48 objects unchanged. Actual unlock rc plus subsequent held rc1/empty, final times and unresolved findings are required. Restoration, visual outcome and task acceptance are separate verdicts. |

## Three material gaps in the current admit helper

1. **Failure does not propagate through exit status or command receipts.** `tools/admit.py:11–13,35–36` appends `problems` and writes JSON but never exits nonzero for failed checks. It reads only stdout (`:7`), not original rc/stderr/argv/time. `env.sh:28–42` also does not stop after every snapshot call. A successful process exit or plausible stdout is therefore not admission success. Inspect the full JSON and each raw receipt; stdout is truncated to 900 characters at `:36`. This does not negate the separate explicit rc checks in guard/put/rboot.

2. **Some predicates are reported or loosely matched, not object-bound.** Ready is only recorded (`admit.py:23`), boot is only recorded (`:34`), and lock/serial are not checked there. Labels use a count of nine matching prefixes (`:21`), not an exact path-to-label map; ready source hashes and HAP/data directory fields use substring presence (`:22,27–28`). An incorrectly associated line or wrong ready/boot can escape those checks. Review exact paths, expected values and fresh per-phase identity; independent guard receipts can supply evidence, but must actually exist for this run.

3. **Snapshot coverage and final-stage semantics are insufficient for closure.** `admit.py:17–20` covers nine controls plus nine additional members; `env.sh:32` collects labels for six controls/three directories, not all 13 members. No admit check verifies running boot copies, deadlines, screenshots, unlock, or the whole transaction. `admit.py:32` rejects every `EXISTS`, although final snapshots intentionally may retain the signed new stage/backup (`plan.json: restore_verification / outer-review.json: retained_objects`). Do not suppress all findings or relabel `report` as PASS: evaluate retained paths as the explicit narrow exception, while independently retaining `.new` absence and all other checks. Supply existing actual raw for uncovered obligations; if absent, report UNKNOWN rather than requesting new device tests through this review.

## Handoff

Await the outer-provided fixed actual raw/index before filling results. This checklist introduces no device test, orchestration, authority, exception, or code change. No commit/push. Reviewer outcome remains **PENDING**, including restoration and final image judgment.
