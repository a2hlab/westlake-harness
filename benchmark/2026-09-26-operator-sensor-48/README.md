# #48 route C: core libandroid sensor exports

Board 61b0657200000000000000000324012c only. Independent harness branch
`test/libandroid-sensor-48`; VM source worktree `westlake-operator-sensor48`,
branch `test/operator-sensor-48`, source 72ed855566c530c46cdd5ec3f378b1b979f8bbda.
All VM commands run through `orb -m a2hlab bash -lc '<command>'`. Commit only.

`build_sensor.py` reproduced the stock core libandroid SHA
dc5eb800eb5626f41f72cb9ed8fe59f2c35151b0e8f2ee3b49cd9779886a47b4 from its
recorded link inputs. Five existing source object hashes match their manifest.
It compiled only android_sensor_noop.c and relinked only libandroid.so.
New SHA: 14fe6c92f6f034b109e5ada98a79be25df9d36efedf1024fc393fa592c67e0ee.
The exact seven new ASensor dynamic exports are present, all original exports
remain, and DT_NEEDED is unchanged. The supplied assert_libandroid_sensor.sh
passes 7/7; an independent dynamic-table comparison prevents its static-symbol
fallback from masking a missing dynamic export. Build commands and input hashes
are preserved. No full native-runtime build or downstream rebuild.

Deployment backs up core `runtime/libandroid.so` by SHA and preserves its file
label. It does not target `webview-t-lib/libandroid.so`. The same ability38-v7
operator stage, A1 ART ae2cb182, shim85c789f4 (GLES + npth refusal), mc46 bridge
d4fae8e5, npth8b8d559c, and run.sh17781b81 (four tt targets + libttcrypto-first
LD_PRELOAD) remain. Seven component hashes are checked before and after each
round. vm.max_map_count=1048576 is asserted before startup and reapplied by the
existing guardian. No system-partition or policy changes.

Five fresh starts use the exercised #49 runner with separate data/evidence.
Each round stops the guardian, kills prior app PIDs/parent, preserves all three
old profile trees, creates empty ones and launches a new parent/child. Consent
and article clicks use real uinput after visual confirmation. Original PID and
birth are bound; guardian replacement never counts as survival. Each successful
round requires a real NewDetailActivity lifecycle record, at least 180s after
detail RESUMED, readable article screenshots, no ASensor relocation failure,
no metasec-associated main exit and no original process terminal record.
Other metasec ULEs remain a separate explicit metric: even a surviving window
does not establish successful loading or elimination of the dead-thread chain.
Raw stderr, parent log, samples and matching faultlogs
are retained. The old #49 group is not mixed in: it ended 3/5 body survival,
2/5 metasec main exit and was ACK(blocked), commit1c5dad5.

The operator explicitly resumed this same candidate after the two-round
interim report: complete c-r3/c-r4/c-r5 without waiting for the symbol closure.
Stop further trials if the property ULE leads to an actual process exit. The
first two observations remain part of this five-round group; no artifact changes.
This is a finite reliability window, not a guarantee of unlimited uptime or
of successful metasec loading. Runtime exceptions remain a separate metric.

Live pointers remain `/data/local/tmp/operator45/{child.pid,parent.pid,guard.pid,child.stderr.path}`.
Stop guardian without killing app: board shell
`touch /data/local/tmp/operator45/stop; kill $(cat /data/local/tmp/operator45/guard.pid)`.
Archive root `/data/local/tmp/operator45-crashes`; old core backup subdirectory
`sensor48-original`. No automatic rollback to the old candidate is planned.

## Two-round interim result (continued by operator instruction)

|Round / original PID|Original lifetime at end s|After detail RESUMED s|ASensor relocation errors|metasec main exit|Other metasec ULE|End body|
|---|---:|---:|---:|---:|---:|---|
|c-r1 / 9704|420.82|229.424|0|0|1|readable|
|c-r2 / 19210|372.34|200.873|0|0|1|readable|

Both real-uinput trials passed the bounded body-survival/zero-ASensor-error
checks. Both still failed to load metasec because `__system_property_read` was
missing in namespace 0, causing an uncaught platform-back-handler ULE. No
metasec-associated main exit occurred within these two observation windows;
this does not remove the dead-thread-to-null-Looper mechanism observed in #49.
The two-round interim report did not establish the five-round gate; c-r3–c-r5 are now continuing on the same candidate.

Both had zero original-PID SIG11/get_meta cppcrash, zero npth diagnostic-library
refusal messages and zero sampled xasan/heap_tracker mappings. The refusal
branch remains unexercised. Each had one work_thread SIGABRT banner without a
corresponding original-main-process terminal record. Maps peaked at 11104 /
10831, RSS at 1159180 / 1202256 KiB. The sysctl stayed 1048576. All seven
deployed component hashes matched before and after both rounds.

[Second-round article screenshot](evidence/c-r2/monitor-end.jpeg).
At handoff (2026-09-26 06:12:53 CST), original child19210 and guardian19249
were alive, with the article visible. Stage:
`/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`.
Original stderr:
`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/private-tmp/adapter_child_19210.stderr`.
Current pointers may change after guardian recovery; that would not extend
the measured lifetime above. The current operator instruction continues the same candidate for c-r3–c-r5;
claude-3’s symbol-closure candidate remains a fallback if a real exit occurs.

## Continued result: c-r4 real exit; c-r5 stopped

c-r3 / original30577 survived509.15s and285.691s after detail RESUMED;
body readable. c-r4 / original10607 was last alive149.82s and dead by154.07s.
It threw the same __system_property_read ULE on platform-back-handler, then
X.DEv null-Looper construction reached the main thread and the parent reaped
exit(1). No article lifecycle opened; the attempted article input was rejected
because the bound original had exited. This is a real property-associated
process exit, not merely a nonfatal ULE. c-r5 was not started, as the operator
explicitly required stopping on this outcome. Final sensor-only result:3/4
body-window passes,1/4 metasec-related main exits,one planned round not run.
All four had zero ASensor relocation errors and zero SIG11/get_meta cppcrash;
all had one property ULE. Thus sensor alone did not make the exit deterministic.

The new user task supplies complete symbol-closure source1d4af70. That candidate
will be built and tested as a separate group/worktree, preserving these failures.
