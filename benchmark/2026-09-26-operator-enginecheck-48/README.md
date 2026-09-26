# #48 hollow hook-engine warm experiment

**ACK(blocked), R2=partially.** Three of five warm attempts completed the nominal 360-second navigation window; r1 and r5 ended in native SIG11 before the feed. The three surviving attempts opened both ArticleInflowActivity and NewDetailActivity with real uinput. No mallocng crash was observed in this sample, but this is not a five-of-five reliability pass or proof that all heap corruption has been eliminated.

## Configuration and deployment

Only board `61b0657200000000000000000324012c`. Independent branch `test/hollow-engines-warm-48`. Consent retained, both restart guardians stopped, one original child per round, no replacement rounds, no AOT/JIT speed layer. Every round began with empty app/appspawn PID lists and >1GiB MemAvailable; cleanup killed the child and parent before evidence collection.

The only deployment change was replacing these two app-native binaries:

| Library | Original SHA256 | Deployed SHA256 |
|---|---|---|
| libbytehook.so | 238e7bc3e0c36247de86fe80453d596503ec0c45bc3ece578fc351d638506d61 | fbb761a0f0d16342f9c63ff94af52b7d6377fda2def7c3f14950139907ea1baa |
| libshadowhook.so | 88351a015be00254f961d5c559187513f8a657a40fb9d13f50b5d0733d7e9cbf | 34378f5c2e2f7f4b418a332018916d488fcbabdf68109836bc83b74bc6f53e3c |

Actual prefix: `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/`; app namespace prefix: `/data/local/tmp/asx/lib/arm64-v8a/`.

Both original files were first backed up to `/data/local/tmp/operator45-crashes/enginecheck48-original/`, pulled and hashed. Candidate copies were checked before deployment. Claude-3's `assert_hollow_engines.sh` passed on the exact candidate files: all nine hook/unhook entries plus ELF/SONAME checks (`static-assert.txt`). Original sizes, UID20010053 and mode0644 were preserved. The patch source and safety hypothesis are inherited at `47993ae`; this experiment does not independently prove every possible caller safe.

Unchanged: shim85c789f4, npth hollow9966e296, memsponge2f066332, monitorcollector f3918bdc, sysopt c92d0ea5, metasec1021a058, mc46 bridge, tt targets/LD_PRELOAD, map_count1048576, clamp BCP jar ea5d8b27 plus matching boot image, run.sh ffb324e4 (JIT file cache unset). Baseline34 hashes checked before/after deployment; final36 include both engines.

## Five consecutive attempts

| Round | Child / parent | Observation seconds | Last live sample seconds | Outcome | Article evidence | Guard |
|---|---|---:|---:|---|---|---:|
| r1 | 29356 /29329 | 20.684 | 17.373 | ChromiumNet0 SIG11, sscronet null-vtable read | No feed/body | 0 |
| r2 | 30535 /30510 | 360.003 | 359.581 | Planned cleanup, no SIG11/exit1 | ArticleInflow + NewDetail body/photo | 8 |
| r3 | 7829 /7793 | 360.008 | 357.707 | Planned cleanup, no SIG11/exit1 | ArticleInflow body/photo; NewDetail short text, comments network error | 9 |
| r4 | 15381 /15354 | 360.004 | 358.620 | Planned cleanup, no SIG11/exit1 | ArticleInflow + NewDetail body/photo | 9 |
| r5 | 23183 /23156 | 20.771 | 17.427 | platform-handle SIG11, musl sigaction write-out | No feed/body | 0 |

The observation timer is not the exact death time. CRASH42 monotonic time minus `/proc/stat` birth gives r1 fault at ~17.910s and r5 ~17.539s. The nominal 360s tests sample process identity every few seconds; the table explicitly gives the last live sample. All three surviving originals are demonstrated above180s and are killed at the scheduled window, not restarted by a guardian.

Across all five: no Layout -79, parent exit(1), or logged UnsatisfiedLinkError. r2/r3/r4 retain the known early work_thread SIGABRT banner while the same child continues; this is not a claim of zero signals. Native SIG11 appears in parent + recorder even when child has no Fatal11 banner.

## Physical input and screenshots

No i/c injection. Clicks use `uinput -T -d x y -u x y`; scrolls use `uinput -T -m 600 1550 600 450 500`. Coordinates were chosen from actual screenshots after dismissing splash ads; no login overlay covered the article taps. Each surviving round had two article opens, a physical return and an ArticleInflow scroll; r3/r4 also had NewDetail scroll input. Screenshots named `inflow-body` or `article-after-10s` are not automatically treated as success: early captures can still show feed. Verified bodies are listed below.

| Round | Feed before ArticleInflow | ArticleInflow body | Feed before NewDetail | NewDetail body |
|---|---|---|---|---|
| r2 | [feed](evidence/engine-r2/feed-ready.jpeg) | [paragraphs + image](evidence/engine-r2/inflow-body.jpeg) | [feed](evidence/engine-r2/returned-feed.jpeg) | [paragraphs + image](evidence/engine-r2/newdetail-body.jpeg) |
| r3 | [feed](evidence/engine-r3/gate-now.jpeg) | [paragraphs + image](evidence/engine-r3/inflow-body.jpeg) | [feed](evidence/engine-r3/returned-feed.jpeg) | [short text; comments error](evidence/engine-r3/newdetail-retry.jpeg) |
| r4 | [feed](evidence/engine-r4/feed-ready.jpeg) | [paragraph + photos](evidence/engine-r4/inflow-late.jpeg) | [feed](evidence/engine-r4/returned-feed.jpeg) | [paragraphs + image](evidence/engine-r4/newdetail-body.jpeg) |

These are six article views across three rounds, not six unique stories: r2/r4 NewDetail is the same Xinhua story. r3 NewDetail has readable title and two-paragraph short news text, but the comments region reports a network error even after retry; do not call the whole network surface clean. `guard-lifecycle.txt` contains anchored ENTRY/RESUMED lines, not settings-JSON substring counts. `inputs.jsonl` records physical coordinates/uptime. r4 `newdetail-scrolled.jpeg` was requested after scheduled cleanup and is excluded from functional evidence. A late r2 extra swipe was rejected by the input deadline, not executed.

## Failures and limits of causal inference

- **r1**: CRASH42 `event-72ac-73ab-1`, ChromiumNet0, SEGV_MAPERR at0x28. Exact sscronet SHA38f0dd42; PT_LOAD maps file offset0x28a21c to the same ELF address. Instruction `ldr x8,[x8,#40]`, preceded by loading the object's virtual table. LR0x28a20c. This is a null virtual-table read, not a demonstrated mallocng trap. The library is stripped; the distant preceding dynsym is not the function name. See [analysis](evidence/engine-r1/crash-analysis.json), [disassembly](evidence/symbols/sscronet-symbolized.txt), raw recorder/maps under `faults/`.
- **r5**: CRASH42 `event-5a8f-5b4c-1`, platform-handle, SEGV_ACCERR. musl file0x110954 → ELF0x111954 = **sigaction+0x184**, instruction `stp q0,q1,[x19,#96]`; LR ELF0x111918. This remains a sigaction output-write failure even though it is not the older0x111974 instruction and not npth-worker. See [analysis](evidence/engine-r5/crash-analysis.json), [disassembly](evidence/engine-r5/event-5a8f-5b4c-1-musl-pc-disassembly.txt).

Both have registers and complete maps (3920/3813 lines), but stack-memory access failed EACCES; no complete caller backtrace is available. No mallocng metadata fault was observed in this sample. The data do **not** select a clean causal branch: multiple article views work, but two early native failures remain. They do not prove a NET/GFX hook load-bearing, prove an exclusively non-hook writer, or establish permanent heap safety. Exact r1/r5 evidence was handed back to Claude-3 on the board.

## Loaded identity and final board state

All five have both patched engines in actual maps, inode137370/137195, linked to preflight and postflight SHA checks. r2 additionally has `live-engine-identity.txt`, hashing through `/proc/30535/root/data/local/tmp/asx/...`; r3/r4 have `maps20/60/190/330-engine-identity.txt` through their own process roots. These give file identity in the actual namespace, not merely a candidate directory. `engine-mapping-excerpts.txt` preserves the matching map lines. There is no observation of actual hook invocations, so file patch correctness plus mapping is the scope of this assertion.

All four preexisting protective libraries are mapped in r1–r4; r5 maps npth/memsponge/monitorcollector but not sysopt. Missing early-loaded items are not upgraded to a JNI pass simply because ULE is absent. No engine/npth load failure was logged.

Final app/appspawn PID lists empty, guardians both stopped/no lock, map_count1048576, consent untouched; hollow+clamp+patched engines remain installed for diagnosis. No system partition writes. No speed layers. Final36 hashes pass in `evidence/final-check/`.

## Reproduction and verification

All VM work uses `orb -m a2hlab bash -lc '<command>'`. VM evidence root is `~/a2hlab/board/61b0657200000000000000000324012c/enginecheck48`. `scripts/warm48.py <unused-round-name> confirm-warm` is the consent-preserving mode; other inherited modes reset profiles and were not used. HDC calls have hard deadlines at most55s. The one-shot board timer only kills the original PID/birth and parent; it never restarts. Existing deployment helper is one-use and refuses an existing backup directory.

`analyze_fault.py`, `summarize_engines.py`, `verdict.py`, `final_state.py`, and `export_clamp.py` produce classifications, audited identity, final hashes and raw/gzip manifest. `python3 verify.py` checks every raw/stored SHA; `--git` checks committed HEAD bytes. Patched `.so` candidates are included explicitly; original backups remain board+VM and the original handoff commit983d2c7. No push.
