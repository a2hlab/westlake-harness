# U5 INVESTIGATE: application-PID evidence, not render-keyword counts

## What was wrong

cc-t3's paused `investigate.py` counted render strings across the whole hilog,
including the system compositor. It also selected `split()[1]` as PID, which is
the **time column** in `MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: message`, and assumed
the Java main TID equals PID. U5 logs explicitly show ActivityThread on a dedicated
`CM-BIGSTACK` pthread; the leader detaches before joining it. Consequently the
old `rendered(likely-lit)` and null-main-thread outputs are not valid diagnoses.
The script excerpts and source hashes are in `evidence/source-review.json`.

The cc-t3 `NULL-PRODUCERS.md` correction (`a2a0c3210`) and multidex work
(`a0c60190c`) were read first. fd-client's upstream TLS/SSLEngine failure must not
be reclassified as an accountManager null-stub; it is outside this alive/no-fatal
cohort and no changes to that work are made here.

## Selection: 66 → 5 keys

Use the original selected U5 records, exact record/log/image SHA values and outer
visual labels from `J6N4-SCORING.json`. Check t20 observed PIDs against the same
snapshot's package UID. Keep white/desktop + alive + no observed target fatal.
All 66 inclusions/exclusions are in `evidence/cohort.json`.

**Selected: 5 white, 0 desktop.** fd-gallery is excluded: PID 15650 remains alive
but another same-UID process, 15685, throws `EXTERNAL_CONTENT_URI` at hilog line
56410. They are sibling target processes, not a proved parent/child relation.
fd-mobile is alive but **black**, outside the requested white/desktop scope.
It is retained only as a boundary control. Lit aegis/anki are negative controls.

Use only target PID lines and their own TIDs, truncated at the t20 screenshot's
remote mtime (second precision), not the later end of the hilog. Organic Maps
has earlier same-UID processes without captured log lines and later restarts;
neither their missing logs nor a final signal-handler line establishes a wait.
Raw process lists have PID/PPID/UID/name, **not thread state or Java stacks**.

## Per-key findings

Every line number below refers to that key's original `hilog.txt`, whose relative
path and SHA are stored in `evidence/app-<key>.json`. Complete numbered excerpts,
per-PID last logs, Java-main TID bindings and window/frame witnesses are included.

| Key / app PID → Java main TID | Category | Last app / main observation | Decisive evidence and candidate |
|---|---|---|---|
| fd-AppManager 4371 → 4397 | Other | No separately identified app-owned logger; last process/main diagnostic :38277 describes the finished KeyStore token; another token has an active decor. | KeyStoreActivity start :34521/:35000 → finish code=0 :35732; app content window :35350; swap entry :36657. Investigate result/return-token delivery, not an assumed permission dialog. |
| fd-noice 28902 → 28926 | Caught exception | Last SubscriptionRepository stack line :44185; Java main :44142 reports ONLINE-CM getActiveNetwork online. No sampled blocked stack. | Caught cancellation :40959/:44153 wraps missing SSLSockets. Window :33564; swap entry :41856. Reuse T7d SSL fallback candidate; white-screen causality remains unproven. |
| noice 8768 → 8792 | Caught exception | Last SubscriptionRepository stack line :55858; Java main :55822 reports network-online diagnostic. | Same wrapped missing class :53346/:54009/:55825; five swap probes. This is another APK SHA, not an extra distinct application or guaranteed T7d light. |
| fd-organicmaps multiple PIDs | Other | Last identified app logger :58168 says cities boundaries unavailable; Java-main tails :62875 (6584→6597), :57793 (6644→6660), :59760 (6690→6714), :65356 (6787→6809). Earlier six PIDs have no scoped log coverage. | Splash → DownloadResourcesLegacy :20194/:58180, reverse relay :36665, finishes :20222/:36693/:58221. Async loading finishes :58166. Inspect Activity/process reuse and launch-mode relay; missing World assets/localization is not proof of network wait. |
| termux 25164 → 25189 | Other | Last app tag :17334 says properties not loaded because file is null (not a proved fatal); main :18992 shows finished/no-window/no-decor. | TermuxService requested :18139, Activity finish :18313, ability first-frame callback :18336 despite no window/swap witness. Trace service creation/bind/bootstrap and finish reason. |

**Main-thread state for all five: unknown.** These are last recorded operations,
not sampled blocking stacks. Do not rename diagnostics to an exact wait location.
App-owned logger attribution is deliberately narrow (SubscriptionRepository,
Termux, OMcore); adapter/runtime messages remain separately labeled process logs.

## Window and frame audit

| Key | Old global render matches | Foreign-PID matches | App window markers | Swap-entry samples | Explicit submit-success receipts |
|---|---:|---:|---:|---:|---:|
| fd-AppManager | 9 | 3 | 2 | 1 | 0 |
| fd-noice | 15 | 4 | 4 | 5 | 0 |
| fd-organicmaps | 24 | 8 | 4 | 2 | 0 |
| noice | 13 | 4 | 4 | 5 | 0 |
| termux | 7 | 1 | 0 | 0 | 0 |
| aegis (lit control) | 12 | 4 | 4 | 5 | 0 |
| anki (lit control) | 22 | 4 | 4 | 5 | 0 |

Counts are log witnesses, not unique windows or rendered frames. The old rule
was contaminated in every selected key. PID filtering is necessary but not
sufficient: JNI method registration, linked exception classes, swap entry and
ability lifecycle callbacks are also not frame-submission success. The two lit
controls have zero explicit submit receipts too, so absence is **unknown**, not
a diagnosed no-frame wall. Keep foreground/surface/presentation stages separate.

## Five buckets and repair candidates

`results.json` and `RULES.md` retain all five requested buckets:
**network 0 / permission-or-dialog 0 / window-without-frame 0 / caught 2 / other 3**.
Empty buckets are an evidence result, not missing work. `classify.py` implements
conservative runtime-log candidates; it does not claim a static APK can prove a
pending callback or swallowed exception.

Candidate source locations are numbered in `source-review.json`. They are
inspected source references, **not a claim that those HEADs built the deployed
U5 JAR**. `ActivityManagerAdapter.startService` discards the native return in
that source; `finishActivity` forwards token/code without the result Intent.
These justify probes, not a claim that either defect explains these screenshots.
Existing typed APP_CONTENT foreground code is another reuse candidate, not proof
the U5 artifact contains it. Native swap probe placement is similarly recorded.

## Reproduce and hand off

### Benign baseline subtraction (outer 03:47 / 03:53 additions)

`knowledge/gates/benign-log-signatures.json` contains **17 reviewed signatures**
mined from the 24 outer-reviewed lit U5 keys. Sixteen have 24 distinct-package
support; the explicit CoroutineStart probe has **10 packages / 14 occurrences**.
Each entry retains counts per key, three original PID-bound examples and full
source log/record/image hashes. The mining pass found 112 common candidates;
only this reviewed subset is enabled. Native-registration failures, arbitrary
ClassNotFound stack lines, and potential window errors are not blanket noise.

The CoroutineStart entry records cc-wiki `6b157c39d` and outer ACK(80) 03:53:38:
the adapter's primeCoroutineStart reflects the original class name, which R8 may
rename, and catches the failure. Its immediately following same-PID/TID/tag stack
is subtracted only in that caught-probe context and timestamp second. Standalone
CoroutineStart CNF remains visible: do not exempt app-origin missing classes.

Collection now subtracts exact signature matches before classification/fatal
inspection, while retaining every matched line in `benign_noise` and raw replay
events. Terminal fatal markers always survive. Registry matching is disabled for
a different generation/runtime/boot identity; this is not a gate exception table.
The five selected keys lose 18/20/45/20/26 baseline-noise lines respectively
(AppManager/fd-noice/Organic Maps/noice/Termux); **the five-way result is unchanged**.
Noice's SubscriptionRepository SSLSockets cancellation is not a benign match.

```sh
python3 benchmark/2026-10-01-u5-investigate/benign.py --u5-root "$WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep"
```

Common occurrence on lit apps means contextual baseline noise, not universal
correctness of an API. All suppressed evidence stays available for a later
causal review; an app-specific need can promote a baseline warning again.

```sh
python3 benchmark/2026-10-01-u5-investigate/test_classify.py
python3 benchmark/2026-10-01-u5-investigate/collect.py --u5-root "$WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep"
```

Collection is read-only and prints JSON. It verifies original record/log/image
hashes, keeps full-stream counts and emits sparse target-PID replay events. The
vendored app files normalize event arrays in `facts` to original line references;
the full event rows remain in `replay_events`. Tests replay those events and inject
foreign compositor lines, registration-only markers and false first-frame labels.

No runtime patch, device action, screenshot reclassification, U6 score or U7
freeze is produced. Take only `landing-paths.txt` plus this task's root README
and DIGEST line. U7 is explicitly held in this worktree by outer instruction.
