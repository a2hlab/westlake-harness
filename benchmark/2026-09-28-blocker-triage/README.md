# T0: current-attempt forensics and gated board admission

The original sweep confused live processes and RenderService nodes with visible app UI, matched its own log command, and deleted the stderr evidence. T0 now captures exact child/runtime evidence before cleanup and requires external image review. **Stopped under blackboard #16: the user moved all three boards to the BMS route on OH 7.0.0.38. Both boards completed 13 controls + markor (28 captures total). The 43-app survey was not started. No further writes to 5ea or 61b are authorized.**

The first experiment failed the installed-host identity gate. [Original report](evidence/initial-host-blocked-README.md) and [original results](evidence/initial-host-blocked-results.json) remain historical evidence. Under explicit #11 authorization, both assigned boards received a data-preserving host replacement; [deployment receipts](host-restore/README.md) include HAP hashes, versions and 61b clock synchronization. Runtime, framework and APK payloads were not changed.

## Deployment and admission

| Board | Framework | Current control run | State |
|---|---|---|---|
| `5ea34a4500000000000000001123012c` | `framework-2` | `cx10-controls-20260928-1648` | 13 controls + markor captured; 307/307 deployed hashes unchanged; external review pending |
| `61b0657200000000000000000324012c` | `framework-1` | `cx10-controls-bytes-20260928-1710` | 13 controls + markor captured after clock synchronization; 307/307 hashes unchanged; external review pending |

Both framework inventories contain the same 306 files. The installed host must match `8cfa5bb1eb1a26fa69dbfd5618cecf0aefb282f6035aa9af24dcb9f96eb81267`. Admission requires matching before/after deployed hashes, 13 image signatures with `verdict=lit`, and markor with `verdict=not-lit`. Each signature binds serial, run, key, screenshot SHA-256, reviewer and a visible criterion. Missing signatures grant no admission. The outer loop owns visual verdicts; scripts never infer LIT from logs or process state.

61b originally reported January 1970. All pre-sync attempts are retained but invalidated as `clock_skew`. The first post-sync run stopped at Amaze because hilog contained non-UTF-8 bytes. It is retained as interrupted; decoding now keeps original bytes on the VM, records their SHA-256 and uses replacement decoding for text filtering. No failed attempt is silently upgraded or overwritten.

61b's broker/keeper/watchdog had already been disabled under #9/#11. The [current inventory](runs/cx10-controls-bytes-20260928-1710/61b0657200000000000000000324012c/interference-audit/inventory.json) found zero known writer processes and no matching active system/vendor init configurations. Stop markers for keeper and watchdog exist. The collector checks exact full serial attachment and cx-t0 lock ownership before every board command. A failure interrupts that attempt and leaves remaining keys not-run.

## Collection and evidence

[manifest.json](manifest.json) freezes 43 blocked app keys and 13 controls, including package, APK hash, launch Activity and input-metadata hash. Each launch copies its input into `~/a2hlab/ws/out-appsweep-t0-<run>/<serial>/<key>/`; shared app inputs stay read-only. All attempts are retained under [runs](runs). Screenshots use `<run>/<serial>/<key>.jpeg` and require successful snapshot, launch-time freshness, size and received hash checks.

ART's complete SIGQUIT dump is in `<runtime>/private-tmp/adapter_child_<pid>.stderr`, delimited by `----- pid <pid> at ...` and `----- end <pid> -----`. Two bounded captures are at least five seconds apart. The Java main thread is identified by `ActivityThread.main`, not its name: Wikipedia calls it `Thread-2`. Its `MessageQueue.nativePollOnce`/`Looper` wait is normal idle. Markor exited before capture but its exact runtime stderr remained readable; `/proc/<pid>/root` did not. Both stack attempts explicitly record `capture-failed: child-exited`.

Markor's current stderr contains an uncaught Chrome process-launch exception and a subsequent `CrBrowserMain` fatal signal. These are candidate markers, not proof of a causal runtime defect. `confirmed` remains empty without same-attempt causal evidence. The common `WESTLAKE-ICU u_setDataDirectory symbol not found` warning is preserved as a background observation because it also appears in the Wikipedia control. It is not promoted into an app-specific blocker.

RS `allInfo` package content queues are bound to the current child using WindowManagerService's PID and window entry. Both raw dumps are archived. A render node is an observation only; it never skips stack capture or grants a visual verdict.

Full stderr and binary transport logs remain on the VM. Git contains short diagnostic excerpts, original source line numbers and full-source hashes; stack and RS evidence are small text files. Cleanup accepts only exact runtime/stage paths from the current reports after export, rejects all `c91d26bf` paths, and records protected directory listings and content hashes before/after. Shared LocalSend inputs and a pre-existing other-lane output are independently hashed around cleanup/shards.

## Effective record selection and checks

`t0_summarize.py` recomputes candidates from archived evidence. Only completed attempts with fixed package/APK/Activity identity, an admitted board, matching payload identity and no invalidation are eligible. For each key, the latest `(finish_epoch, run_id, serial)` wins deterministically; all earlier/interrupted/rejected attempts remain in `attempts`. `no-marker` is an honest observation. At least 39 of 43 keys need non-capture-failed observations; named root causes have no quota.

Rust selectors call production Python collection, batch, interpretation and admission functions. Negative controls replace production operations with deliberately broken behavior and require assertion failures. Simulated lock and detach transport tests exercise `Board.shell` and the production batch driver without disconnecting physical devices. Their results are offline regression evidence, distinct from actual board captures and external image review. Repository baseline: 69 tests, 67 pass and 2 skip (latest run after restoration). Current lifecycle: **10 pass / 4 fail / 0 skip / 0 pending_review**. The four failures are 43-app observations, seven pure-Java coverage, external control signatures, and complete 43-app merging. They represent unfinished acceptance, not passing results. [Lifecycle](evidence/current-lifecycle.json), [fresh explain](evidence/current-explain.md), [per-selector verdicts](evidence/current-verdicts.json), [offline negative controls](evidence/current-offline-negatives.txt). The historical lifecycle in `evidence/lifecycle.json` applies only to the original host-blocked experiment.

R2 remains **partially**: host restoration, clock repair and minimal capture feasibility are verified; complete 43-app observations were cancelled by #16 and external board admission was never granted. [Current generated results](current-results.json) and [review request](review-request.json) expose the remaining gates.

## Stop and handover (#16)

No blocked-app shard was launched. All 28 current control images are linked in [review-images.md](review-images.md); [review-request.json](review-request.json) preserves their identities and hashes without fabricated verdicts. Both current control runs passed deployed before/after hash audits. The 5ea cleanup removed 28 exact current paths and preserved existing c91d26bf content hashes. The 61b cleanup timed out after 120 seconds while reading protected content hashes, before reaching force-stop or removal; its runtime/stage directories remain. No retry was made after the route switch. Original raw stderr and transport bytes remain on the VM.

The prepared 22/21 split in [shard-plan.json](shard-plan.json) is historical planning only. It is **not authorization to resume** on the boards, which are handed back for flashing. The collector and checks describe the OH 6.1.0.31 experiment and cannot be treated as validation of the new OH 7.0.0.38 route. [Stop record](stop-record.json).

Subsequent dispatch #19 changed the new BMS deployment target back to the existing OH 6.1.0.31 firmware (no flashing), in a separate worktree. It does not resume this T0 survey or alter these historical verdicts.
