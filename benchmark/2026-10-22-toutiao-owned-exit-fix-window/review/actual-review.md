# T52 actual raw independent review

**Not a full PASS.** Candidate t30/after images remain blank. The observation exceeded the hard 180-second limit; restoration evidence is evaluated separately.

- Fixed manifest `60ccfa48e4280a9129fa1a3e9cb336313c7fa0cd2e023935a38d149b18319256`: all **2430 files** independently rehashed, zero mismatches. No live-directory or device access.
- Real lock start 21:33:29.354379 to unlock completion 21:46:59.120737: **809.766358 s** (recorded integer epoch span810s). Restoration first replacement starts at lock+527.271315s, before1200; unlock before1800. Four new boots; ready observations all within55s of their BOOT_T0.
- **391 command receipts**,389 rc0; only expected pre/post `held` calls rc1/empty. All **23 final commands rc0**; rc is not a substitute for body checks.
- Six rollback files match signed SHA/mode/owner/labels with new inodes recorded. All13 member SHA/mode/owner/labels match baseline. Runtime124 and boot36 exact path/SHA sets are byte-identical before/after. HAP/bundle/data-directory binding and ready source hashes match.
- R2 three key copies match the candidate. R4 all13 member copy hashes match baseline; final ps has guardian4026 under the exact R4 boot path, with SUPERVISOR_STARTING evidence. No separate guardian birth/exe bracket is claimed.
- Candidate events record gone4/zombie1 classifications, three process_exit/RECOVERING transitions and RETRY_LIMIT. These are not an exit-cause diagnosis or visual recovery. Independently viewed t30/after: blank; final R4 image: feed text/navigation visible, not playback or manual-close/reopen acceptance.
- obs12 starts **+183.216821s**, after screenshot **+183.808542s** from click start. These are explicit contract deviations, not rounded down to180.
- Final power evidence is `12-final/power.stdout` after override restoration:10000/10000. Final AWAKE vs preflight SLEEP is recorded, not called identical.
- Stage/tag/backup identities match bind7 (inodes213821/213823/213825). Their presence is the signed narrow retention exception; all six ROOT `.new` paths are absent. This is not permission to suppress other admission findings. T48 backup subdirectory was not individually restated in the final retained listing.

## Correction of the stop-marker review

The earlier missing-selfheal statement is withdrawn. Fixed `raw/12-final/stops.stdout` SHA `9ff6dea0b8d7ea2d7d482044282cff69b6e392476a2eeaa5821cc4d6b9ec08eb` contains selfheal48 on line2. Decoded `stops.argv` SHA `ece627f00e2d6e85a0f65c26774a8a5d1ad81657fc3144ab3cfb1cf9572043f4` has zero backslashes and the valid predicate `[ -e "$s" ] || [ -L "$s" ]`. A local synthetic existing file, using the unchanged loop body with only its input path rebound, returned PRESENT/rc0. The quoting suspicion is also withdrawn; no stop-marker defect is asserted.

## Evidence and scope

The companion `actual-review.json` contains per-file recovery results,16 replacement readbacks/guard comparisons, four boot phases, timing, all23 final rc, screenshot hashes and an exact raw evidence index. Its root alias is `$HOME/.local/share/westlake/t52-execution-outer-20261022/private-raw`; originals were not changed. No helper/admit was rerun, no device commands, no code changes, no commit/push. This is a bounded evidence review, not a deployment or broader recovery authorization.
