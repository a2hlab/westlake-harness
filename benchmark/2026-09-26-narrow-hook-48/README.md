# #48 narrowed seven-library refusal: warm validation blocked

R2: partially. Only board `61b0657200000000000000000324012c` was used. No guardian, no #50 file-backed JIT, no rebuild, no system-partition writes. Consent/profile retained. Each round began with no app/appspawn-x PIDs; both original processes were cleaned after observation. This is not operator acceptance: no article body or NewDetail lifecycle was obtained.

| Round | Child / parent | Observed original lifetime | Outcome | Visible content |
|---|---|---|---|---|
| narrow-r1 | 1721 / 1670 | 240.009 s; last sampled alive 237.240 s | Alive until planned cleanup; no recorded SIG11/exit(1) | Real unobstructed feed at 80 s; later unsolicited login screen |
| narrow-r2 | 7292 / 7259 | Last alive 17.380 s, dead by 20.729 s | Parent reports signal 11; recorder captures ChromiumNet0 | Host screen, before feed |

No physical article click was actually injected in either round. In r1 the interactive operation was attempted after the bounded window and rejected; this is a test execution gap, not an application click latency result. R2 exited before feed. Accordingly no <=15 s article assertion is available and no old article screenshot is substituted.

## Deployment

Westlake fix `e55b30a`, upstream harness analysis `0b1a8d0`. Source `~/a2hlab/tmp/warmrefuse48-narrow-out/libwebview_bionic_shim.so`, new SHA256 `dc4f5e6fd66fa8e6793d1c0d181b1436b743669534d1fd311f7724e77da61e35`. Old SHA `06375dc1aaa924bc79622c2deedf4c2e80815ab5e3e8305d515d3cb6869c38df` backed up under `/data/local/tmp/operator45-crashes/narrow48-original/libwebview_bionic_shim.so.<old-sha>` before overwrite. Seven component hashes are retained in each round's evidence. Metasec 1021a058, mc46 bridge, patched npth, passive recorder ART, tt targets/preload, map_count 1048576 and run.sh remain unchanged. No guardian was restarted.

Runtime `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`; stage `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`. Candidate remains installed, app and parent stopped; `/data/local/tmp/operator45/stop` remains present. Final MemAvailable 5937964 KiB, both pidof lists empty.

## Failure evidence for claude-3

R2 recorder `event-1c7c-1d97-1`: PID7292, TID7575, thread `ChromiumNet0`, SIGSEGV/SEGV_MAPERR, fault `0x71f292f33205c4ca`, PC `0x7fa25cee1c`, LR `0x7fa25ceb44`. Musl SHA `fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2`. Mapping and PT_LOAD conversion yield PC file offset `0xd4e1c` / ELF vaddr `0xd5e1c`, LR file offset `0xd4b44` / ELF vaddr `0xd5b44`. Fault instruction is `ldr x13, [x0, #16]`, preceded by metadata pointer XOR. The nearby objdump label `wcsxfrm` is not a resolved private function name. Do not claim an exact allocator caller or corruption source without further symbol/source analysis.

Metadata, siginfo, ucontext and complete 3548-line maps are saved. Stack read failed with mem_open_errno 0xd (EACCES); no .stack/full native backtrace is available. This is a different observed site/thread from earlier npth-worker null-write trap. Parent signal and recorder prove the fault even though child.stderr has no conventional `Fatal signal 11` banner.

R1 has libjato.so mapped at all 20/60/190 s samples despite membership in shim refusal list. Source loader logs explicitly name it; see `loader-route-notes.txt`. Therefore shim refusal is not effective across all load routes. R2 crash maps contain none of the seven refused libraries, so this crash cannot be assigned to mapped jato on present evidence. libhotfix-opt is mapped in R2; neither round shows the prior main class-init exit(1).

R1 also has uncaught `Chrome_ProcessLauncherThread` RuntimeException: `Illegal meta data value: the child service doesn't exist`, while the original app remains alive. This is not interpreted as article success. The upstream gate reports PASS on R2 despite the recorder fault: its conventional crash-analysis/banner checks miss this evidence. Strict report includes recorder metadata, lifetime, parent status, maps and visual results; acceptance is false.

## Review and reproduction

[Unobstructed real feed, not article](evidence/narrow-r1/during-80.jpeg), [final login screen](evidence/narrow-r1/before-cleanup.jpeg), [crash metadata](evidence/narrow-r2/faults/event-1c7c-1d97-1.txt), [address analysis](evidence/narrow-r2/crash-analysis.json), [strict R2 result](evidence/narrow-r2/strict-review.json), [component hashes](evidence/narrow-r2/component-hashes.txt).

VM evidence: `~/a2hlab/board/61b0657200000000000000000324012c/narrow48`. Every VM command uses `orb -m a2hlab bash -lc '<cmd>'`. `warm48.py <new-name> confirm-warm` preserves app state, requires empty pid lists, launches one app and schedules bounded cleanup at 240 s (emergency one-shot termination at 248 s, never restart). Every HDC operation has a <=55 s host timeout. `input` and `article` check original PID/birth/deadline; only real `uinput -T -d x y -u x y` is used if those gates pass.

`verify.py` checks all evidence SHA256s and decompressed originals; `--git` also verifies HEAD blobs. `review.py` and `report.py` preserve failed acceptance; screenshots require human review. Next work belongs to crash diagnosis and loader route coverage, not another declaration of reliable delivery.
