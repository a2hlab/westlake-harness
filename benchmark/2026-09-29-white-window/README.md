# Item 61: nine white startup windows, before Activity launch

The previous `alive at 15 s` category hid two independent failure tracks. **9/9 assigned processes reach main-thread application binding, but none records `ScheduleLaunchAbility`, an Activity launch transaction, or a VSync request. Seven explicitly fail application binding; two return OK. Eight have later AppMS `Add Ability Stage TimeOut!` receipts.** These observations place the common missing launch marker before rendering; they do not establish a common VSync deadlock. Evidence is indexed below with original file/line references.

**Rule established:** inspect both Android application binding and the OH AbilityStage/ability dispatch handshake. Search delayed service errors across the next capture, joining exact PID + UID + package. A per-app directory contains whole-board hilog; its directory name is not process attribution. The successful baseline delivers `ScheduleLaunchAbility` at line 3988 while bind completes at line 4307: these tracks overlap and must not be forced into a serial ladder.

Item 62 follow-up: [AbilityStage native handshake, B5 bytecode and generation mismatch](ABILITY-STAGE.md).

## Input identity and scope

- Analysis base: `456e56ca`; no device execution, VM writes, deployment, commit or push.
- Read-only Mac copy supplied by outer: `/Users/zhaoyue/orca/workspaces/vm-copies/b4-48-unknown22-61b-20260929T1015/`. In this report `key/hilog.txt:N` means that root plus the indicated file and original line.
- VM original: `/home/zhaoyue/a2hlab/board/b4-48-unknown22-61b-20260929T1015/`.
- Nine `record.json` files match the pinned #48 key/package/UID/PID/activity/timing fields in [probe48-targets.json](evidence/probe48-targets.json). Every log also contains exactly one matching `initChild: proc=<package>` for the expected PID. Full hashes, sizes, original line counts and the 22-file delayed-error search inventory are in [results.json](results.json).
- `H:N` below means `../2026-09-28-bms-route-deploy/spawn-ab/evidence/helloworld/hilog.txt:N`, PID 25183, board 5ea. Target PID observations are from board 61b. Baseline and #48 are different runs/generations; marker differences alone cannot identify a binary defect.
- Board clocks differ: HelloWorld records `09-28`; #48 records `01-02` and service freeze receipts identify year 1970. Preserve those clocks; compare ordering/deltas within each capture, not epoch equality with the runner's 2026 metadata.
- Coverage is **9/13 white-window apps**. `fd-binaryeye`, `fd-mobile`, `localsend`, `noice` have no assigned #48 logs here. #51 logs were not supplied/read; its local `alive16_shots.py` captures focus/screenshots/records and contains no hilog collection. No diagnosis is extrapolated to those four.
- Initial OrbStack access failed, then the Mac copy resolved access: [access.txt](evidence/access.txt). Raw 133 MB input stays outside Git; small numbered excerpts are retained here.

## Successful HelloWorld reference

See [helloworld.txt](evidence/helloworld.txt) and the original H log. These are observed events, not assertions that every application logs its own lifecycle methods.

| Track / stage | Original line and timestamp | Observation |
|---|---|---|
| Attach | H:3966, 18:29:35.822 | `attachApplication ENTRY` |
| Launch application / main-thread bind | H:3977, H:3985, .825–.826 | Binder callback posts work; main looper executes it |
| Ability dispatch (parallel to binding) | H:3988, .826; H:4022, .833 | `ScheduleLaunchAbility` then `LaunchActivity transaction scheduled` |
| Bind success | H:4307, .892 | `handleBindApplication returned OK` |
| Activity lifecycle | H:4403, .908; H:4506, .942 | HelloWorld `MainActivity.onCreate()` / `onResume()` |
| VSync initialization / request / callback | H:4541, .943; H:4616, .984; H:4631, .989 | Real execution markers, excluding registered method names |
| App window / content node | H:4644, .995; H:4732, 18:29:36.006 | `WMClient.createSession`, self-drawing content child |
| Resume draw listener / persistent surface | H:4866, .040; H:4935, .066 | First-frame listener, persistent SurfaceControl |
| EGL / first-frame notification | H:5215, .143; H:5422, .188 | EGLSurface returned, `AbilityTransitionDone(state=9) rc=0` |

The first-frame callback is a log milestone; screenshots remain the visual verdict. `ClassNotFoundException: adapter.activity.AppSchedulerBridgX` at H:4837 occurs before the successful callback H:5422, so the presence of an exception alone is not a failure classifier. `content_capture -> null` also appears in the healthy reference at H:4448/H:4504/H:5219.

## Per-app last activity and first missing step

All nine have zero target-PID observations for `ScheduleLaunchAbility`, `LaunchActivity transaction scheduled`, the main sentinel, resumed draw listener, VSync initialization/request/callback, app `createSession`, content Surface, persistent SurfaceControl, `SetSurfaceNode`, EGLSurface creation and first-frame notification. Their last observed lifecycle **dispatch** is application binding; no executed Activity lifecycle callback is observed. Do not count provider `onCreate` stack frames as Activity `onCreate`.

The earliest missing **common baseline launch marker** is `ScheduleLaunchAbility` (H:3988). The seven explicit bind failures are an additional, earlier Android initialization failure, not proof of why OH failed to dispatch an ability. Each row links a numbered excerpt; numbers in the table are original `key/hilog.txt` line numbers.

| App / PID | Last bind outcome; original lines | Concrete bind failure or remaining uncertainty | Last target log; board time |
|---|---|---|---|
| [ooniprobe](evidence/ooniprobe.txt) / 7679 | FAILED at 24278; cause/context 24303 | Startup provider `getProviderInfo` → `NameNotFoundException` | 24308; 01-02 07:26:24.524 |
| [fd-etar](evidence/fd-etar.txt) / 10812 | FAILED at 27361; cause/context 27375 | Classloader namespace: nonexistent `/system/app/ws.xsoh.etar/lib/armeabi-v7a` | 27385; 01-02 07:28:34.596 |
| [fd-fluffychat](evidence/fd-fluffychat.txt) / 13057 | FAILED at 27236; cause/context 27262 | Startup provider `getProviderInfo` → `NameNotFoundException` | 27267; 01-02 07:30:05.271 |
| [fd-immich](evidence/fd-immich.txt) / 15265 | FAILED at 28422; cause/context 28447 | Startup provider `getProviderInfo` → `NameNotFoundException` | 28452; 01-02 07:31:35.715 |
| [fd-kitchenowl](evidence/fd-kitchenowl.txt) / 17320 | FAILED at 27544; cause/context 27569 | Startup provider `getProviderInfo` → `NameNotFoundException` | 27574; 01-02 07:32:59.462 |
| [fd-minetest](evidence/fd-minetest.txt) / 19483 | FAILED at 27148; cause/context 27167 | FileProvider: missing metadata for `net.minetest.minetest.fileprovider` | 27174; 01-02 07:34:28.403 |
| [fd-stk](evidence/fd-stk.txt) / 26286 | OK at 33894; cause/context 33912 | Bind OK; coroutine priming CNFE is explicitly logged non-fatal; ability dispatch absent | 33914; 01-02 07:39:09.794 |
| [burgerking](evidence/burgerking.txt) / 27467 | FAILED at 34280; cause/context 34294 | Classloader namespace: nonexistent `/system/app/com.emn8.mobilem8.nativeapp.bk/lib/armeabi-v7a` | 34304; 01-02 07:39:59.095 |
| [mindustry](evidence/mindustry.txt) / 29878 | OK at 33759; cause/context 33777 | Bind OK; coroutine priming CNFE is explicitly logged non-fatal; ability dispatch absent | 33779; 01-02 07:41:37.366 |

The final target lines for seven apps are the `content_capture` stub diagnostic; Etar/Burger King end with bind exception stack frames. Whole-board logging continues **14.578–14.856 s** after the last target line, so these are not just files ending immediately on the exception (per-file `target.last` vs `file_last` in results). Silence does not prove a dead thread: idle polling, dropped logs and uninstrumented work still require #60 stack evidence.

**Four provider component failures:** OONI, FluffyChat, Immich and KitchenOwl fail while installing `androidx.startup.InitializationProvider`, with `ApplicationPackageManager.getProviderInfo` in the cause stack (e.g. OONI:24292–24306). This is distinct from “provider class absent”: the provider's own `onCreate` was executing. Check component lookup and returned ProviderInfo/metadata before trying rendering changes.

**One FileProvider failure:** Minetest:27162–27172 shows `FileProvider.getFileProviderPathsMetaData`/`parsePathStrategy`/`attachInfo` failing during provider installation. It proves the authority/metadata query failed, not that the APK lacks the XML resource. The exact implementation-side omission needs source/APK confirmation.

**Two namespace failures:** Etar:27375 and Burger King:34294 explicitly name a nonexistent `armeabi-v7a` search directory. That error is the demonstrated classloader creation blocker. It does not prove that an empty directory repairs ABI compatibility; verify installed ABI and nativeLibraryDir provenance in the repair task.

**Two bind-success controls:** STK:33894 and Mindustry:33759 return OK; their `primeCoroutineStart` failures are explicitly `(non-fatal)` at STK:33896 / Mindustry:33761. Both continue to the later `content_capture` diagnostic (STK:33914 / Mindustry:33779). Do not classify that optional coroutine class lookup as their launch-stopping error. Neither has a later ability launch marker in its assigned capture.

## Delayed AppMS evidence: a shared handshake failure in eight

[delayed-ams-timeouts.txt](evidence/delayed-ams-timeouts.txt) retains exact PID + UID + package joins. The **first `Add Ability Stage` half-timeout is ~30 s after `ScheduleLaunchApplication`**, beyond the nominal 15 s survival observation. Later captures provide the missing time coverage. The second timeout type is `Start Process Specified Ability TimeOut!`, also attributed to the same identities.

| Target | Add Ability Stage half-timeout source:line | Start Process Specified Ability half-timeout source:line |
|---|---|---|
| ooniprobe | `opencamera/hilog.txt:8075` | `opencamera/hilog.txt:23377` |
| fd-etar | `fd-feeder/hilog.txt:4425` | `fd-feeder/hilog.txt:51589` |
| fd-fluffychat | `fd-im-vector-app/hilog.txt:4683` | `fd-im-vector-app/hilog.txt:34512` |
| fd-immich | `fd-k9/hilog.txt:6721` | `fd-k9/hilog.txt:46833` |
| fd-kitchenowl | `fd-libre/hilog.txt:6475` | `fd-libre/hilog.txt:37553` |
| fd-minetest | `fd-saber/hilog.txt:6869` | `fd-saber/hilog.txt:26622` |
| fd-stk | `burgerking/hilog.txt:7923` | `burgerking/hilog.txt:33781` |
| burgerking | `ppsspp/hilog.txt:6645` | `ppsspp/hilog.txt:31216` |
| mindustry | Not captured | Not captured |

This is positive evidence of the service waiting for lifecycle completion, including STK despite its successful bind. It narrows the common investigation to **AbilityStage completion / specified-ability handshake → ability dispatch**, not VSync. It does **not** identify which deployed callback, reply, binder transaction or generation caused the missing completion. Mindustry is the last trial in this input set; no corresponding delayed timeout was captured, so its shared-handshake diagnosis remains a hypothesis.

The checked-out source already documents/implements the intended replies: `bms/src/adapter/framework/activity/jni/app_scheduler_adapter.cpp:448–460` calls `addAbilityStageDone`, and `:838–852` handles the specified-ability reply. These are source inspection leads, not proof that #48 ran those exact bytes. The local Java source at `activity/java/AppSchedulerBridge.java:270–328` also differs in line layout from the logged `ensureBindApplication(...:311)` and contains no `primeCoroutineStart`; do not equate current source with the deployed #48 jar.

## Requested rendering / timeout checks

- **Activity:** no app Activity lifecycle execution observed; provider lifecycle stack frames are preserved as failure context only. Last scheduler event is bind failure/success per table.
- **Choreographer/VSync/RequestNextVSync, skipped frames, app ANR and binder timeout:** zero matching execution messages in all nine target PID streams; counts and first/last buckets are in results. This excludes other PIDs and does not assert the absence of a global service failure.
- **WindowManager/SceneSession:** each target has 12 setup/window-service messages ending at `J_after_installWindowManagerStub`, but zero `WMClient.createSession`/`SetSurfaceNode` runtime markers. Package-associated SceneBoard `OnStartAbilityBySpecified`/session records are retained separately; a starting/system window is not app Surface evidence (e.g. STK:29823 vs STK:33894).
- **RenderService:** no target-attributed render-service error matched the recorded patterns. Whole-board RenderService/SceneBoard traffic cannot be assigned to an app by capture directory alone. The positive AMS timeout receipts above take precedence over a speculative renderer diagnosis.
- **Log integrity limits:** no stack dump was collected here; no guarantee of lossless logging, no new visual review, and no claims about post-capture execution. Baseline lacks an `ability_stage` marker too, so that marker alone is not used as a cross-generation absence test.

## Handoff to item 60

These are historical #48 observations. If #60 runs a later B6/restored generation, compare its own deployed hashes and fresh PID/log evidence before applying this diagnosis; this report does not establish that the current board still has the same defect.

1. Use **STK** as the control for the shared dispatch problem: bind returns OK and its PID later has an explicit Add Ability Stage timeout. Compare live main/binder stacks with AMS stage state and deployed bridge reply behavior. An idle main looper can be consistent with no ability transaction delivered; it is not automatically an app deadlock.
2. For **Mindustry**, check the same handshake but retain `unverified` until its own AMS/stack evidence agrees. Do not substitute STK's timeout for Mindustry's missing receipt.
3. Treat the seven bind exceptions as concrete additional blockers: provider component lookup (4), FileProvider metadata (1), classloader search directory (2). Completing OH dispatch alone does not establish successful Android application initialization.
4. Only move the common investigation downstream to VSync/Surface after observing `ScheduleLaunchAbility` and actual Activity launch/resume in the same target process. In the reference, delivery and bind are concurrent; compare both tracks.

## Reproduction and verification

```sh
python3 benchmark/2026-09-29-white-window/analyze.py \
  --input-root /Users/zhaoyue/orca/workspaces/vm-copies/b4-48-unknown22-61b-20260929T1015 \
  --output /tmp/white-window-repro
python3 -m unittest discover -s benchmark/2026-09-29-white-window -p 'test_*.py' -v
cargo test --manifest-path tools/spec-checks/Cargo.toml white_window_offline -- --exact
```

The analyzer opens input files read-only and does not issue subprocess/device commands. Tests cover the known baseline lines, PID/registration/stack false positives, unavailable/incorrect identities, the seven-vs-two bind split, eight positively attributed delayed timeouts, and regeneration/hash checks of the supplied captures. Hash-reproduction test explicitly skips if the external copy is unavailable; a skip is not fresh source verification. See [validation.txt](evidence/validation.txt).

Validation: 5/5 Python checks passed with no skips, the Rust wrapper passed, and agent-spec parse/lint scored 1.0. The lint/test lifecycle passed 3/3 scenarios ([lifecycle.json](evidence/lifecycle.json)); these are extraction/provenance checks, not independent proof of the causal interpretation. `git diff --check` passed.

**R2:** log identities, quoted events, stage counts and the eight timeout joins **verified** offline. Mechanism attribution to an exact missing handshake implementation is **partially** established (service timeout confirmed; defective deployed callback/reply unknown). Mindustry's same-cause hypothesis, the other four apps and repair effectiveness are **unverified**. No new screenshot/LIT claim. Outer owns the commit.
