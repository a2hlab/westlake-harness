# #48 hollow + Layout clamp: five warm rounds

**Blocked: native crashes still prevent reliable delivery.** The clamp runs on board and restores degenerate width. A physical touch now opens an ArticleInflow article with visible title, paragraph text and image, and NewDetail articles are readable. The five-round result retains every failure; no restarted process or replacement round counts toward survival.

Board `61b0657200000000000000000324012c` only. Independent branch `test/layout-clamp-48`; no push. R2=partially for the overall acceptance. Deployment hashes, real inputs, screenshots, lifecycles, process samples and native crash snapshots are recorded; source of memory corruption is **not established**.

## Five-round result

| Round | child / parent | Observed seconds | Result | Guard hits | Article evidence |
|---|---|---:|---|---:|---|
| r1 | 28986 / 28965 | 240.007 | alive, scheduled cleanup | 8 | NewDetail body |
| r2 | 3574 / 3541 | 240.009 | alive, scheduled cleanup | 6 | TikTok route; no article body |
| r3 | 9048 / 9015 | 20.770 | SIG11, SQLite measureAllocationSize | 0 | no feed/article |
| r4 | 10955 / 10934 | 17.451 | SIG11, musl metadata read0xd5e1c | 0 | no feed/article |
| r5 | 12342 / 12318 | 360.008 | alive, scheduled cleanup | 8 | ArticleInflow + NewDetail bodies |

**3/5** meet ≥180s survival. No Layout -79 or parent exit(1) was observed in these five windows. Guard fired22 times across the three surviving rounds. The exact old PCs0xd6e20 and0x111974 are absent, **but two other SIG11 failures remain**, including a musl heap metadata path. Three readable articles were captured across r1/r5. This is not5/5 delivery.

r2 also logged three ULE lines: TTPlayer._setSupprotSampleRates (two repeated lines) and android.media.MediaPlayer.native_init. The original process survived; video functionality was not accepted. These are not npth JNI errors, and the report does not claim ULE=0 globally. All four protected libraries mapped in r1/r2/r3/r5; the early r4 crash maps only show npth and monitorcollector among those four, not memsponge/sysopt.

## Deployment

Unchanged hollow native recipe: shim85c789f4, npth9966e296, memsponge2f066332, monitorcollector f3918bdc, sysopt c92d0ea5; mc46 bridge, metasec1021a058, tt targets/LD_PRELOAD and map_count1048576 retained. run.sh SHA remains ffb324e4 and explicitly unsets JIT file cache. No app speed-AOT or JIT layer was installed. Consent/data were preserved.

The actual BCP jar `fw/adapter-runtime-bcp.jar` changed from
`5731db00562e3b814cfb4d4e32703c40c9e8726a022b28da155fd040fb59019a` (198155B) to
`ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e` (202502B).
The supplied surgical patch is retained under `patch/`, with notes and repeated 9/9 static checks.

Runtime: `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`, privately mounted as `/data/local/tmp/asx` by source_app_namespace. All nine original fw jars and 27 boot files were backed up on board **before replacement** at `/data/local/tmp/operator45-crashes/clamp48-original/`, and pulled to VM `~/a2hlab/board/<serial>/clamp48/deployment/original-fw-boot.tar`. All pulled files match the board backup SHA list.

The build uses the exact board BCP inputs in unchanged order and logical locations, westlake host dex2oat, arm64, compiler-filter=verify, base0x70000000. Nine rebuilt OAT headers are **247**. Patched jar plus 27 matching boot files were staged, hashed, then copied together into the stopped actual app runtime; all 28 deployed hashes were verified and checked again before each round. The original candidate framework directory is not overwritten.

The first host build crashed in CreateRuntime because the host-only `libmap32bit.so` environment used by prior #38 builds was omitted. Restoring that existing host environment gave a successful 4.994s build. Both host logs and tool/environment SHA are retained. This host failure is separate from board round SIG11 and is not an app sample. No native-runtime rebuild was performed.

## Evidence and round protocol

`evidence/final-acceptance.json` contains the final table, guard counts, activity lifecycles, exceptions, maps coverage and manually reviewed article screenshots. Each `clamp-rN/` has preflight/component hashes, PID/birth, samples, input uptimes, screenshots, child/parent logs, cleanup and crash snapshots. `articles.json` links each article to its route/feed/body screenshot.

Guardians remain stopped. Each round starts only with empty app/appspawn pidof and >1GiB MemAvailable, launches one parent/child, then kills its app/parent on completion or failure and confirms cleanup. All HDC operations have deadlines ≤55s. r1/r2 used240s observation; after the r2 route miss, r3–r5 used360s maximum for screenshot-gated two-route coverage, with a one-shot368s kill timer. The two early failures remain in the five-round denominator.

One extra live r1 library-probe command timed out at10s due to a broad grep. It was terminated; the official round's liveness and full maps collection succeeded. That probe is not presented as evidence of JNI success. A late r2 input request was rejected by the driver's deadline gate and sent no touch. Full inputs/operations show these limitations.

All actions are real `uinput -T -d x y -u x y`; r2 also used physical swipes. No i/c injection. The first r2 card attempt routed to TikTokActivity while the feed had moved; r2 is not counted as article functionality.

## Confirmed functionality and limits

- r1: feed card→NewDetail, paragraph body and image, `clamp-r1/article-body.jpeg`.
- r5: ordinary feed card at(380,825), uptime137732.34→**ArticleInflowActivity**, RESUMED137748128. `clamp-r5/inflow-late.jpeg` shows title, paragraph text and large photo. The earlier `inflow-body.jpeg` is still loading and is **not** the successful body evidence.
- r5: physical back→feed screenshot→pinned article at(380,580), uptime137857.63→NewDetail, RESUMED137865144. `clamp-r5/newdetail-body.jpeg` shows multiple paragraphs and image.

These are three distinct readable articles across **two** rounds, not three successful rounds. The early-r5/second-click timings are retained for traceability, not an AOT/JIT performance claim.

The deployed marker is exactly `[OH_WSA-relayout] DEGENERATE session rect width clamped [#48 Layout:-79 guard]` (lowercase `clamped`). Guard context shows session1x1920 becoming useWH1200x1920 and valid merged bounds. It is not enough to find the marker as a DEX string; these are runtime child log lines. r3/r4 die before guard/route coverage and cannot be called clamp-positive samples.

## Native failure evidence

- **r3**: bd_tracker_w:13, parent confirms signal11. Recorder PC0x7f939c75ec/LR0x7f939c75e4, invalid address0xa1f1dfa40000007e. Actual `liboh_android_runtime.so` SHA8ab6742d matches the symbol file. Mapping/PT_LOAD conversion: file0x865ec→ELF0x875ec, **SQLite measureAllocationSize**, `ldr w9,[x8]`; x8 is loaded from the db object's offset760. `runtime-symbolized.txt` has the full local disassembly. This locates the invalid read, not who corrupted the pointer.
- **r4**: pool-4-thread-2, signal11, musl **ELF0xd5e1c/LR0xd5b44**, metadata invalid-read path. It is not PC0xd6e20, but is a heap-path failure and must not be excluded from reliability accounting.
- Both recorders saved registers, siginfo and complete maps, but mem_open EACCES prevented stack memory capture: **no complete native backtrace**.
- No conclusion that the jar caused these failures: there is no unpatched/rebuilt control arm, and both die before the clamp marker. Equally, hollow's earlier finite clean window cannot establish permanent heap safety.
- work_thread SIGABRT banners in surviving rounds remain listed as the known early background event. Do not report all Fatal signals=0.

## Reproduction / rollback boundary

Scripts run in VM via `orb -m a2hlab bash -lc '<cmd>'`. `prepare_boot48.py` is intentionally one-time and refuses an existing backup; `build_boot48.py` uses actual backed-up inputs; `deploy_boot48.py` requires stopped processes and original backup. Do not rerun the deployment blindly. For any future authorized rollback, restore original adapter jar and matching **entire original boot set** together while stopped; preserve app data and native patches. No rollback is performed by this report.

`export_clamp.py` exports logs/metadata/screenshots with a raw/gzip SHA manifest. Large original/candidate boot binaries remain in the VM and board backup, indexed by SHA; they are not duplicated in git. `verify.py --git` checks committed evidence byte-for-byte. The final board has no app/parent or guardian; candidate jar/image and warm consent remain in place for outer review.
