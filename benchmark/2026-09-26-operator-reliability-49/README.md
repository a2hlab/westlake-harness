# #49 operator reliability: A1 plus npth hook refusal

Board61b0657200000000000000000324012c only. Independent worktree and branch
`test/operator-reliability-49`, based on the #48 operator experiment. Only commit,
no push. All VM commands use `orb -m a2hlab bash -lc '<command>'`.

Per the superseding operator instruction, A1 r4/r5 finish first. Then the
prebuilt shim from `~/a2hlab/ws/out-npthrefuse49/libwebview_bionic_shim.so`
(westlake b14e4d0, SHA85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a)
replaces GLES-only ecc7b12c, with original SHA backup and file label preserved.
No compilation, source-SDK modification, policy change, or system-partition write.
A1 libart ae2cb182, mc46 bridge, npth ret patch, tt targets and libttcrypto-first
LD_PRELOAD remain. Exact run.sh SHA17781b81 includes those routing settings.
All six component paths/hashes are checked before every start and after observation.

`round49.py` adapts the already exercised #48 isolated runner. Each round stops
the guardian, kills the original parent and all Toutiao PIDs, preserves the prior
three data trees, creates fresh data, starts a new parent/child, and restarts the
3-second guardian. A2 symlink preseed is disabled. Guardian archives failures and
cleans orphan Toutiao processes before recovery. Recovery never counts as survival
of the bound original PID/birth. max_map_count1048576 is set and asserted before
launch; guardian reapplies it on recovery. Consent and article selection use real
uinput, only after screenshots establish the UI state.

Final group:5 fresh starts, each original instance >180s on a video article,
readable body screenshots, no metasec-associated main exit and no heap-corruption
SIG11. Original-PID faultlog paths, child.stderr, parent.log, maps/RSS samples,
refusal logs and uptime-aligned lifecycle records are retained. The supplied
assert_heap_corruption_gone.sh is preserved verbatim; it treats refusal counts
as informational. Zero refusal messages will be reported as unexercised, not
proof that the refusal code blocked a real request. No claim that a finite
five-round window establishes unlimited uptime or causally identifies the source
of a preexisting heap corruption.

Original #45 stage/runtime paths and stop controls remain unchanged. Live pointers:
`/data/local/tmp/operator45/{child.pid,parent.pid,guard.pid,child.stderr.path}`.
Stop guardian while keeping app: board shell `touch /data/local/tmp/operator45/stop`,
then `kill $(cat /data/local/tmp/operator45/guard.pid)`.
Original shim backup: `/data/local/tmp/operator45-crashes/reliability49-original/`.
The #48 rollback utility is not executed; the operator explicitly requested A1 retained.

The five-round gate is blocked: final-r1 and final-r3 reproduced the
metasec-associated main-thread exit. Both failed relocation at
`ASensorManager_getDefaultSensor`, then platform-back-handler threw ULE,
`X.DEv` attempted to create a Handler with a null Looper, ActivityThread.main
returned, and the parent reaped exit(1). This is not an errno13 failure, but
it is still the failed-back-thread-to-main-exit chain. A1's earlier five
surviving windows did not establish elimination of that chain.

Final-r2 survived 652.61s total and 255.394s after detail RESUMED. Its body and
video cover remained visible at the end. Consent and article timing varied
with UI readiness/manual observation; this is not a matched timing A/B.
Final-r3 displayed its consent dialog after an initial feed screenshot, so
the first article input was unsuccessful; the later consent input is recorded
separately. No input is sent to guardian replacements.

All five rounds are complete. Evidence is exported with raw/decompressed SHA and
committed-HEAD verification via `verify.py --git`. Historical #48 evidence is
separate. Refusal coverage and heap outcomes are separate from metasec exits.

## Final five-round result: blocked, R2 partially

|Round / original PID|Last alive age s|End check age s|Detail RESUMED window s|metasec → main exit(1)|Body at end|
|---|---:|---:|---:|---:|---|
|final-r1 / 26917|188.91|193.20|0.000|1|not opened|
|final-r2 / 2331|652.61|652.61|255.394|0|readable|
|final-r3 / 16393|148.37|152.25|0.000|1|not opened|
|final-r4 / 21769|398.37|398.37|189.958|0|readable|
|final-r5 / 31132|395.68|395.68|213.162|0|readable|

3/5 completed the article survival window. 2/5 exited via ASensor relocation failure → dead platform-back-handler → null Looper → main return. All five had one platform-back-handler ULE and one work_thread SIGABRT banner; the latter did not mean the original app exited by SIGABRT. No original-PID SIG11/get_meta cppcrash was observed. All five had zero refusal messages and zero sampled xasan/heap_tracker mappings: actual refusal requests remain unverified.

[Final article screenshot](evidence/final-r5/monitor-end.jpeg). 147 evidence files verified against raw/decompressed SHA and HEAD. Six component hashes were checked before/after each round. The original instances in rounds 2/4/5 survived their windows; later deliberate teardown for the next trial is not a crash. New user route C is a separate worktree/group; all old failures remain in this report.
