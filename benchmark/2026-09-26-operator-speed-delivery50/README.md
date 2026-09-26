# Operator AOT + file JIT candidate (#50)

This candidate adds application AOT and app-private file-backed JIT to `deploy/operator-selfheal-48` (`eed2d1e`). Board: `61b0657200000000000000000324012c` only. The baseline's native patches, clamp BCP/boot, native targets and LD_PRELOAD are preserved. No system partition writes, full runtime rebuild or push.

**ACK(blocked), R2=partially:** NewDetail speed and actual AOT/file-JIT acceptance are demonstrated. Stability non-regression is not demonstrated: two natural SIG11 failures in six speed attempts, including a SkiaCanvas destructor failure. A deployed self-healing speed candidate is not a clean stability acceptance.

## Build identity

The requested `integrate/toutiao-speed-aot @2eb427d` package locked the pre-clamp boot image and A1 ART. Reusing that odex on the current clamp boot would invalidate the comparison. `prepare_aot.py` freezes and hashes 39 actual runtime inputs: nine BCP jars, 27 matching boot files, libart, APK and launcher. `build_aot.py` rebuilds only application AOT using the same Westlake host dex2oat, not AOSP/hanbin oat230. Build time 62.202s, exit0; arm64, speed filter, oat247, 21 dex, PCL[], BCP checksum `i;9/2ab43e21`. Actual BCP order and logical `/system/framework/*.jar` locations are retained.

- dex2oat SHA256: `8f9592174aa9d3f8b8f7e0d2879d15c6407e3c2f9f839346b8a8523c4434c7e3`
- odex: `c7ad2a0b58dc2fe5a18e92196a37183f0d41012689c1c20ade1c500a99914a32`
- vdex: `e6f5c1aaf69bdec6975fc08c238f6090f7ef1a0e784e098c9ee35d476748106d`
- app image: `5ed9e8b2dcb44ae82808532610b26b1d48e462fecf73eaaa3c4c8395c991f3ee`

`aot/apply_speed_aot.sh` is the original installer with a new exact input/artifact lock; preflight and apply ran against the frozen inputs. No ART mismatch was whitelisted. VM build artifacts are `~/a2hlab/ws/out-speed-delivery50/speed-clamp/`; large binaries are not committed. `stage_aot.py` stages and hashes them on board; `select_arm.py` toggles the directory only while the app and parent are absent and guardian is stopped.

## JIT and guardian

`prepare_jit50.sh` comes from `fix/jit-file-cache-50 @47f0576`. After parent namespace setup and **before app spawn**, the launcher runs it through `nsenter -t <parent> -m`: reject symlink path components; mkdir `/data/data/com.ss.android.article.news/code_cache/art-volatile`; chown UID:GID20010053; chmod0700; verify exact identity. The launcher sets `WESTLAKE_OH_JIT_FILE_CACHE_DIR` to that path. Every fresh watchdog restart repeats the hook. A failed hook stops launch instead of silently claiming speed.

Actual child logs must say `using app-private unlinked file with dual RW/RX views`, not `using ART anonymous cache with RWX`; maps must include the unlinked `art-volatile/#<inode> (deleted)` file with RW and RX views of the same inode. ART must log loading `oat/arm64/toutiao.art` and map the odex executable. File presence alone is not acceptance.

The inherited watchdog retains PID/birth checks, a single supervisor lock, explicit child+parent+pidof cleanup, >1GiB available-memory gate, crash archive, bounded fresh profile rotation and no UI intervention after READY. This version also requires a recorded consent action before accepting two feed frames; otherwise an early feed flash could precede the privacy dialog. The original operator profile remains backed up. Fresh recovery loses the current disposable session's data.

## Measurement protocol and limits

Both arms use fresh profiles to match the delivered watchdog's recovery mode, one original app/parent, **guardian disabled**. This is not a warm reliability result. Each profile gets the same directory preparation but the base arm disables file JIT and hides application AOT. Physical uinput touches an inspected unobstructed feed row. First pinned article is the same NewDetail article, “一轮中秋月，照见中美两国的友好交往”. Primary latency uses `/proc/uptime` immediately before uinput to the subsequent actual NewDetail ENTRY/RESUMED, not arbitrary JSON substring counts. Body visibility is manually inspected screenshots; conservative bounds use before-capture of last blank and after-capture of first visible body.

Click occurs at least35s after feed gate, later when human visual inspection takes longer. Fresh server content can vary. Baseline r2 needed a late manual consent action after the old feed-gate race; it is retained and flagged. Speed r1 routed to ArticleInflow, excluded from NewDetail speed estimates. Speed r2 was not clicked before its300s safety timer, not counted as a natural crash or timing success. A one-shot timer bounds each trial; cleanup verifies no app/appspawn and memory headroom. Later formal rounds hold the original PID to240s; early pilot windows differ and must remain visible in the table.

Combined AOT+JIT is the measured treatment, not an isolated attribution to either component. Small samples and one article are insufficient for population crash-rate noninferiority or long-term stability. Existing survived work_thread SIGABRT banners are reported separately from process death.

## Reproduction / operation

All VM commands use `orb -m a2hlab bash -lc '<cmd>'`. Scripts are in this shared worktree's `scripts/`. `trial.py NAME start base|speed`, visually inspect `preview/NAME/feed-gate.jpeg`, then `click X Y`, `collect`, `cleanup`. Never run trial start with the guardian active. A new name is required for each new app attempt. Before speed use `select_arm.py speed`, before base use `select_arm.py base`.

`install.py` requires no app/parent and a stopped guardian, verifies inherited native baseline hashes and new AOT hashes, backs up the launcher, then installs the watchdog, JIT hook and speed launcher. `control.py start/status/stop`, `capture.py LABEL`, `audit.py LABEL` and `archive.py` maintain the evidence trail. Stop guardian by touching `/data/local/tmp/operator45/selfheal48/stop`; wait for STOPPED and lock removal. The current app intentionally remains alive; `control.py cleanup` stops it after the guardian is stopped. Dynamic IDs: `/data/local/tmp/operator45/selfheal48/instance.txt`; stderr pointer: `/data/local/tmp/operator45/child.stderr.path`.

Rollback: stop guardian and clean app/parent, `select_arm.py base`, restore the baseline run.sh from runtime `operator-speed50-launcher-backup/run.baseline.sh` and previous watchdog from that backup, then restart. Original native libraries/BCP/boot were not altered by speed deployment.

## Recorded failure, not a stability pass

speed-r3 died during bootstrap: ReferenceQueueD, SIG11/SEGV_MAPERR address8. Actual libhwui SHA `a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2`; maps file offset0x33d55c maps through executable PT_LOAD (+0x1000) to ELF0x33e55c, **android::SkiaCanvas::~SkiaCanvas()+0xfc**, `ldr x1,[x8,#8]`, LR ELF0x33e594 in the deleting destructor. This proves a null virtual-table read in destruction, not who damaged the object or whether AOT/JIT caused it. Recorder registers/maps exist; `/proc/self/mem` EACCES means no full stack. It is neither old mallocng0xd6e20 nor sigaction0x111974. The baseline guardian's previous seq9 natural crash was instead musl file0xd5e20 / ELF0xd6e20 on platform-defaul after ~2575s. Thus “no new crash class / no stability regression” remains unproven; a fast successful article cannot close that requirement.

A nonfatal `Fresco-BgExecutor` UnsatisfiedLinkError for `libstatic-webp.so` / `std::__ndk1::__shared_weak_count::__get_deleter` occurs in both base and speed logs. It is retained as a pre-existing functional limitation, not hidden behind “ULE=0”. The measured article body and illustration still render. No native-target change was made during the speed comparison.


## Before / after results (guardian disabled)

| Arm / attempt | PID | Click → NewDetail RESUMED | Body visibility interval | Original process observation |
|---|---:|---:|---:|---|
| base-r1 |27974|24.616s|40.47–51.02s|alive204.22s, planned cleanup|
| base-r2 |4499|18.248s|30.45–41.08s|alive295.56s, planned cleanup; late manual consent|
| base-r3 |23833|14.259s|20.43–26.11s|alive246.00s, planned cleanup; illustration present by after30|
| speed-r1 |32566|excluded: ArticleInflow0.575s|≤3.18s|alive141.97s, pilot cleanup|
| speed-r2 |10409|no click|no article|300s safety timer armed; gone at351.39s next observation; censored|
| speed-r3 |16927|no article|none|SIG11 at13.730687s, SkiaCanvas destructor|
| speed-r4 |18326|**0.840s**|**2.44–5.15s**|alive248.62s, planned cleanup|
| speed-r5 |29412|**0.830s**|**2.44–5.25s**|alive249.69s, planned cleanup; one feed refresh before selection|
| speed-r6 |3301|no article click|none|SIG11 at55.381924s following feed refresh, old mallocng0xd6e20|

Observed same-article NewDetail median: **18.248s (base n=3) →0.835s (speed n=2), −95.4%**. Mean19.041→0.835s. This is a small, conditional-on-opening comparison; failed/censored attempts remain in the adjacent table. There was no third valid speed timing. It is not a p90 estimate, three-round speed stability pass, or isolated AOT-versus-JIT attribution. Body is not inferred from RESUMED: the preceding screenshots were still blank.

Screenshots: [base blank at30s](evidence/base-r2/after-30.jpeg), [base body at40s](evidence/base-r2/after-40.jpeg), [speed-r4 blank at2s](evidence/speed-r4/after-2.jpeg), [speed-r4 body at4s](evidence/speed-r4/after-4.jpeg), [speed-r5 body at4s](evidence/speed-r5/after-4.jpeg). Actual capture bounds and physical touches are in each trial's `frames.json`/`input.txt`, backed by `scripts/visual-review.json` and `evidence/summary.json`.

Natural SIG11: base0/3 versus speed2/6 attempts (one Skia destructor, one mallocng; one speed attempt censored and one short pilot). **No claim that crash rate is unchanged or lower.** No observed sigaction-type fault, Layout:-79 or main-throw exit1 in these windows. Every trial has a survived work_thread SIGABRT banner; static-webp ULE occurs in both arms. Neither “all signals0” nor “all ULE0” is true.

## Resident launcher identity

- Watchdog `17bced9bce206c8b0f1f62f7fe035094cbb3b369ebe9146df9fb2073aef598be`
- run.sh `6f7c4251efdebcefd8958a3943d631fc4de1659449897c58901dd929f54ce7c6`
- JIT preparation `ad115b0b66dc1b48747142563dbdf26653c94c98c36200863eb3b1e4ca6fa28f`
- Screen gate unchanged `808f58a10cd4d9bcf35370ea87041e784757a73080ea7b47022c991c5a0360c0`

The initial install preflight rejected the intentionally edited `run.sh` against the native baseline manifest before mutation. The installer now checks native baseline files separately from the newly generated launcher; it does not waive any library/boot identity. All intended speed env differences derive from the saved original launcher. Native build pipeline was not rerun.

The post-install seq12 and later seq16 triggered `process_count_violation` (metrics2 app PIDs), were cleaned before the next launch, and are not counted as spontaneous app crashes. The evidence does not identify whether the extra short-lived PID was an orphan or an app helper, so no stronger claim is made. Existing guardian behavior is retained. The SIGSEGV recovery trial also encountered a spontaneous failure in seq15; total recovery must include those failed launches and backoff, not only the final successful startup.

seq15's spontaneous recovery failure has two recorder SIG11 events: ReferenceQueueD at musl file0xd4e1c/ELF0xd5e1c (metadata read) followed by Chrome_ProcessL with unmapped PC/LR0xffffff80ffffffd8; parent eventually reaped signal5. Those are retained as a heap/corruption failure chain, not classified solely from the final signal5 or called a harmless background abort. Attribution to the speed layer is undetermined.

## Self-healing validation after speed deployment

| Action | From | Next observed READY | Total from injected signal |
|---|---|---|---:|
| SIGKILL at165614.56 |seq13/PID7500|seq14/PID10314 at165637|**22.44s**|
| SIGSEGV at165716.06 |seq14/PID10314|seq17/PID15138 at165801|**84.94s**|

READY log clock is integer seconds (about1s resolution). The second result includes seq15's natural corruption failure, seq16 process-count cleanup and30s backoff. The guard's final `recovery_s=49` measures only from the last failed launch; **it is not the original operator interruption**. Both eventually returned to actual unobstructed feed with real titles, without manual recovery intervention. First22.44s meets approximately30s, second84.94s does not. Old version measured100.89/101.41s for the corresponding two injected signals. Small recovery counts do not establish a worst-case bound.

The recovered seq17 loaded the app image/odex and file-backed dual-view JIT again. Physical uinput at165868.54 opened NewDetail record2 RESUMED165869322 (**0.782s**, guardian-enabled functional confirmation, kept separate from the disabled-guardian comparison). [Recovered body](evidence/validation/recovered-newdetail-body.jpeg) shows title, paragraphs and illustration. Returning from the article triggered an induced-login sheet (`operator-speed-home.jpeg`, despite its provisional filename); it is not a feed success. The visible X was subsequently dismissed for operator handoff.

Each restart first recorded app/parent0, next READY captures had exactly1 app and1 parent, correct app PPid, second guardian rejectedrc2. Pre-start MemAvailable for seq14/15/17 was5852896/5850484/5849316KiB. seq16 cleanup transiently dropped to5617200KiB before returning to5849316KiB; no accumulating prior app instances in the captured window. Post-speed app RSS around1.1–1.2GiB exceeds old baseline READY samples (~0.8–0.9GiB); AOT maps and increased page cache are present, so this is not a zero-memory-cost claim. Long-term memory growth and spontaneous crash rate remain open.

Runtime: `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`. Stage: `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`. Final confirmed app15138/parent15108/guardian6520, with dynamic IDs in the instance file if recovery occurs. Child stderr is runtime `private-tmp/adapter_child_15138.stderr`; crash archives `/data/local/tmp/operator45-crashes/selfheal-<seq>-<time>/` and INDEX.

Verification: same-source oat247 inspect + installer dry-run/apply; live app-image/odex acceptance; private-directory identity and inode-linked RW/RX JIT evidence across trials and recoveries; Python compile, shell syntax, exact native baseline hashes; 560 stored/raw evidence SHA checks; HEAD blob verification after commit. No claim of full stability verification.

Final handoff screenshot: [unobstructed real feed](evidence/validation/operator-final-feed.jpeg). After closing the induced-login sheet the underlying video detail was visible; one physical back touch returned to this feed. These extra navigation frames are preserved rather than relabelled as a successful feed gate. The watchdog does not intervene after READY, so later app-induced login prompts may require operator dismissal.
