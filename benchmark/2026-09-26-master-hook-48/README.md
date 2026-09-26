# #48 hook API master switch: five consecutive warm starts fail

ACK(blocked). R2=partially: five warm trials, deployment, cleanup and fault records verified; >=180 s stability failed 0/5, article body 0/5, exact hook bypass/corruptor unverified. No operator handoff.

Only board `61b0657200000000000000000324012c`; no guardian; consent and app data retained; single original app per round. Start required empty app and appspawn-x pid lists and >1 GiB MemAvailable. Each spontaneous exit was recorded before cleaning its original parent and verifying empty pid lists. No trial reached the planned 240 s cleanup. No #50 file-backed JIT, AOT, additional native rebuild, system-partition change or patch substitution was introduced.

| Round | Child / parent | Last alive → confirmed dead (s) | Recorded failure | Body |
|---|---|---:|---|---|
| master-r1 | 25895 / 25862 | 14.015 → 17.317 | SIG11, PushThreadHandl, libhilog file 0x11050 | No |
| master-r2 | 27054 / 27021 | 10.504 → 14.475 | SIG11, platform-io-thr, musl ELF 0xd6e20 | No |
| master-r3 | 28080 / 28050 | 20.465 → 24.577 | SIG11, platform-io-thr, musl ELF 0xd6e20 | No |
| master-r4 | 29578 / 29547 | 64.921 → 68.255 | SIG11, viewPool-thread, musl ELF 0xd6e20 | No |
| master-r5 | 31876 / 31831 | 17.320 → 20.661 | SIG11, platform-io-thr, musl ELF 0xd6e20 | No |

Times are process liveness samples relative to spawn/driver start, not precise native fault timestamps. Recorder monotonic_ns and original process birth ticks are retained for separate alignment. All five parent logs explicitly report `child <original-pid> killed by signal 11`; none reports original-child exit(1). R4 has two SIG11 snapshots from the same thread/site, not two trials. No Java main exception / hotfix class-init exit was observed before the native failures.

## Functional evidence

There is no article screenshot. All five runs failed before a successful unobstructed feed gate or article operation. R1/R2/R3/R5 screenshots show the host. R4 reached MainActivity RESUMED and the Moutai splash advertisement; the attempted skip at (1100,60) was rejected by the original-PID alive gate because the process had already died. No uinput command was actually sent in these trials. There are no line-start NewDetail lifecycle entries. Therefore these failures are not attributable to a login overlay eating article clicks, and they do not measure click latency. No previous article image is reused.

[Latest reached UI: R4 splash ad, not article](evidence/master-r4/gate-2.jpeg); [R5 host screen](evidence/master-r5/during-10.jpeg).

## Deployment and provenance

Westlake `971f36eea789f6784bf5f4f7b11176d43e39425c`, upstream harness `b1602d1`. Source `~/a2hlab/tmp/warmrefuse48-filter-out/libwebview_bionic_shim.so`, full SHA256 **e692f8fd3bd569f3c7057ca2c037fdc3268b2d3031d4f2fe3942b1a34b56576b**. Previous dc4f5e6f SHA **dc4f5e6fd66fa8e6793d1c0d181b1436b743669534d1fd311f7724e77da61e35** backed up before overwrite under `/data/local/tmp/operator45-crashes/master48-original/libwebview_bionic_shim.so.<old-sha>`.

Each round independently checked all seven component hashes. mc46 bridge, npth8b8, metasec1021 safe-value stub, passive recorder ART, core libandroid and run.sh unchanged; tt/preload/max_map_count retained. New shim's nine GLOBAL hook exports and filter strings pass upstream static gate. Run.sh explicitly LD_PRELOADs ttcrypto, native-network compat, then the shim, and also sets WESTLAKE_ANDROID_NATIVE_PRELOAD to the shim. Full fault maps contain the shim in all five runs. Stale payload hashes inside the historic config.json are not used as deployment proof; live per-round SHA output is authoritative.

Runtime `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`; stage `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`. Original stderr files are under runtime/private-tmp/adapter_child_<pid>.stderr; complete per-round copies and parent logs are archived here. Candidate remains installed, app and guardian stopped, shared `/data/local/tmp/operator45/stop` present. Final MemAvailable 5864348 KiB; app and appspawn-x pid lists empty.

## Crash handoff to claude-3

R2/R3/R4/R5 record SIGSEGV at **musl ELF vaddr 0xd6e20**, file offset 0xd5e20, fault address zero. Disassembly is the previously observed mallocng metadata-check crash instruction `strb wzr,[x14]` after `mov x14,xzr`. Musl file SHA `fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2`. The nearby exported `wcsxfrm` label is not the private function name. LR differs: R2/R4 ELF 0xd6c54; R3/R5 ELF 0xd6a18. Victims platform-io-thr / viewPool-thread do not identify the corrupter.

R1 is distinct: PushThreadHandl, SEGV_ACCERR, address 0x18000004, PC 0x7fa20d2050 / LR 0x7fa20d2000 in `/system/lib64/chipset-sdk/libhilog.so`, file offsets 0x11050 / 0x11000. No local ELF conversion or full caller resolution is asserted for this DSO; do not label this fifth crash mallocng from the thread alone.

Six metadata + siginfo + ucontext + complete maps sets captured across five trials (R4 two events). All failed stack-memory reads with EACCES, so **no complete native backtrace** is available. Child.stderr lacks the usual Fatal signal 11 banner in all five; parent wait status plus passive recorder confirms the failures. Maps are copied via board regular files or recorder, not truncated /proc downloads.

monitorcollector and both hook engines are mapped in every fault. jato is present in R2–R5, memsponge in R3–R5. This confirms monitors now load rather than being refused, but **does not prove their actual calls bind to the interposers**. There is no runtime hook-call trace/count in this shim. The captures do not identify a direct-dlsym bypass or prove all routes are filtered. Next diagnostic should inspect actual hook function pointers/bindings (including handle-based dlsym and namespace lookup), or instrument real hook engines. Do not assert that maps names the corrupting library or re-add libraries speculatively.

[Five-round machine summary](evidence/five-rounds.json); [R2 first mallocng event](evidence/master-r2/crash-analysis.json); [R4 both events](evidence/master-r4/crash-events.json); [R1 distinct fault](evidence/master-r1/crash-analysis.json); [R5 exact metadata](evidence/master-r5/faults/event-7c84-7d8e-1.txt).

## Validation / scripts

Every VM command uses `orb -m a2hlab bash -lc '<cmd>'`. warm48.py retains consent with `master-rN confirm-warm`, limits every HDC call to <=55 s, checks original PID and birth before any input, and installs a one-shot emergency termination (no automatic restart). Observation target 240 s, fallback kill 248 s; all faults here happened much earlier. Each round is launched explicitly, then cleaned and reviewed before the next.

`review.py` checks recorder signals, parent exit status, original lifetime, complete maps and manually inspected image labels; `report.py` additionally requires actual article input and exact line-start detail lifecycle. `analyze_fault.py` preserves every event, performs maps/PT_LOAD translation for the known exact musl binary and records raw metadata. The upstream static gate alone is not runtime acceptance; after feeding crash-analysis.json all five upstream board gates also fail.

`verify.py --git` checks archived bytes, decompressed-original SHA256s and committed HEAD blobs. Python scripts were syntax checked; no software behavior fix was made or independently unit tested in this task. Full five-round board evidence is the validation artifact.
