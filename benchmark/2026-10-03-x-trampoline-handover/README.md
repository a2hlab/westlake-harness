# x's trampoline hand-off: our finish() reaches OH before the next activity is registered, so AppMgr marks the app "terminating" and cold-starts XLiteActivity in a second process. The same shape is in 36 keys, most of them lit; x is white at t20 because its second cold start + 9 s bind lands just before the screenshot

#90, offline. No board touched. Run: U13 window 2, 61b, `x` (record and hilog paths in `evidence/x-timeline.txt`).
cc-wiki's reading (af8aec32de) "the hand-off to XLiteActivity is lost / it never attaches a window with content" is
narrowed here:
- XLiteActivity **is** launched, in a **new process**.
- The hilog ends 7 s before t20, so "never attaches content" is not observable from this run.

## ① Does our finish dismantle the mission? No. It marks the *app record* terminating, so the next ability goes to a new process

Timeline (`evidence/x-timeline.txt`, original line numbers; the app process is 9567):

| t (04:52) | line | event |
|---|---|---|
| 17.97 | 30796 | 9567 bind starts (StartActivity = MAIN/HOME trampoline, OH token 0x7f3387f140) |
| 27.07 | 32411 | bind returns OK, **9.1 s** later |
| 27.856 | 32734 | AMS StartAbility from our `startActivity(XLiteActivity)` → `NotifySCBPendingActivation`. XLite is now only an SCB **pending** session (952); AppMgr has no record of it yet |
| 27.857 | 32737-41 | `finish()` in StartActivity.onCreate → our `ActivityClientControllerAdapter.finishActivity` → OH `TerminateAbility` → AMS `CloseUIAbility StartActivity`, `callerRecordList is empty`, **`pending state dropped CLOSE: 9`**, **AppMS `[ARM938] ability is the last: com.twitter.android`** |
| 27.858-59 | 32743-51 | `finishActivity` runs twice: rc=0, then rc=22 (`verificationAllToken failed`; the token is already terminating, so this is a symptom) |
| 27.954 | 33379 | `SubmitLoadTask XLiteActivity`; 28.012 `startProcessName=com.twitter.android`, then **cold start** |
| 28.13 | 33738 | **new process 9779** |
| 29.06 | 36988-37003 | 9567 still reports StartActivity foreground/background (it stays alive to the end of the log) |
| 29.63 | 37227-34 | 9779 bind starts, `ScheduleLaunchAbility XLiteActivity` |
| 32.5 | — | hilog ends. t20 = 39.36 (clicked 16.49 + 22.87). foreground window = 952 (XLite); observed pids 9567 + 9779 |

**Why a second process** (OH 6.1 LTS source, `evidence/oh-source-excerpts.txt`):
1. AMS calls `PrepareCloseUIAbility` → AppMgr `AppRunningManager::PrepareTerminate`
   (`app_running_manager.cpp:912-942`). When the closing token is the **last** ability of the app record, it calls
   `appRecord->SetTerminating()` and logs `ability is the last`.
2. The close itself is then **dropped** (`ui_ability_lifecycle_manager.cpp:2091-2096`: pending state ≠ INITIAL →
   `SetPendingState(BACKGROUND)`, return). The record stays "terminating", but the process is never terminated.
3. `LoadAbility(XLiteActivity)` → `CheckAppRunningRecordIsExist` **skips records that are `IsTerminating()`**
   (lines 143 / 158) → a new app record and a new process.

**So the mission is not torn down.**
- The trampoline finished **before** the next ability existed in AppMgr. Our `startActivity` is asynchronous on OH (SCB
  pending), and the `finish()` that follows it reaches AMS first.
- In Android the started activity is already in the task when the trampoline finishes, so the process is kept.
- Result: a stranded process 9567 (a finished, windowless StartActivity) **plus** a cold-started 9779 that has to bind
  again.

**It is not x-specific. The same shape is in 36 keys** (all U12 + U13 runs: `ability is the last` + a second
`ensureBindApplication` pid):
- privacyfriendly* ×20, binaryeye, gallery, filemanager, libra, shadereditor, anki, tusky, thunderbird/k9, vlc, x;
- most of them **lit**.

The cost is one extra cold start (`evidence/second-process-cost.txt`):

| key | close → 2nd bind start | 2nd bind | close → 2nd bind done |
|---|---|---|---|
| lit splash apps (privacyfriendly2048/notes, binaryeye, gallery, libra) | 1.4–1.5 s | 0.3–0.5 s | **1.7–2.0 s** |
| anki / tusky / vlc | 1.5 s | 0.9–1.1 s | 2.3–2.7 s |
| **x** | 1.8 s | ~9 s (first bind 9.1 s) | **~11 s** → bind done ≈ 38.8, **0.6 s before t20** |

**x's white at t20 is mainly timing.** Its XLiteActivity can hardly have drawn before the screenshot. Whether it draws
afterwards is not in this hilog.

## ② category-HOME: not the discriminator

**The mapping.** `want.action=action.system.home` (OH launcher start) is mapped to an Android intent
`MAIN + category HOME` for **142 of 168** U13 runs (`B47-SLA` first intent; the other 26 have null action and
categories). That includes the lit helloworld, wikipedia and anki.

**Why it is not the cause here.** The relaunch mechanism above does not read the category.

**What it could still affect.** Apps that branch on the launch category, which cc-wiki is counting corpus-wide; not
repeated here.

## ③ Minimal fix and prediction

**Where:** the Java finish path, not the bridge scheduler.

**What.** In `adapter.activity.ActivityClientControllerAdapter.finishActivity` (oh-adapter-framework.jar 2257b835;
source `bms/src/adapter/framework/activity/java/ActivityClientControllerAdapter.java:274-295`):
- **defer** `nativeTerminateAbilityByTokenAddr` while this process has an outstanding OH start of an ability in the same
  bundle that has not reached this process yet (no `ScheduleLaunchAbility` for it);
- release the deferred terminate when that launch arrives, or after a bounded timeout (≈ 3 s), so a start that never
  lands still finishes the trampoline;
- also collapse the duplicate call: the second terminate on the same token, rc 22.

This is Android's order: the started activity exists before the trampoline is removed. AppMgr then still has a live,
non-terminating record when `LoadAbility(XLiteActivity)` runs. CheckAppRunningRecordIsExist reuses 9567, and the launch
is delivered in-process.

**Deployment choice.**
- Preferred: a **runtime-JAR proxy** (`oh-adapter-runtime.jar`, the B8-AMB pattern that already wraps
  `ActivityManagerAdapter`) over `IActivityClientController.finishActivity`, plus a marker from the
  `startActivity` / `ScheduleLaunchAbility` side. No BCP change, so no FZ-005 re-bake.
- Alternative: edit the BCP adapter itself, which needs a bake.
- The bridge (`AbilitySchedulerAdapter`, M6) is not the layer. The wrong order is decided on the Java side before any OH
  callback.

**Prediction.**

| key | with the deferred terminate |
|---|---|
| **x** | XLiteActivity is launched in 9567 ~0.1 s after the start instead of a new process ~11 s later → about 11 s before t20 to create and draw. **Lit: medium**. It is a native (injected Twitter activity, not WebView) screen; unknowns are its own init walls (network/login). No stranded duplicate process. |
| the 35 other trampoline keys (mostly lit) | first-fatal 0; each saves the 1.7–2.7 s second cold start and the stranded first process. **Regression watch:** the deferral must not block a finish whose start goes to another bundle or never lands (timeout). |
| fd-saber | 0. A single activity; its terminate is a different path (pre-`performCreate`, `callerRecordList empty`), not a trampoline |

**Cheaper check first (no code).** One long-wait capture of x (t45 / t60) on any U13+ image settles whether XLiteActivity
draws in the second process. If it does, x is "slow-white". The fix then moves it inside t20, and its value is mostly
latency for the 36 keys.

## Rules this round sets

- **Before calling a relaunch "lost hand-off", look at where the next ability is loaded and when.** On OH, a finish that
  reaches AMS while the next ability is still an SCB pending session makes AppMgr see the "last ability". It then marks
  the app terminating and cold-starts the next one elsewhere.
- **A second process is not white by itself.** 36 keys do it, mostly lit. Compare the cost (2nd spawn + bind) with the
  t20 budget.

## Files

- `evidence/x-timeline.txt`: the verbatim lines behind the table.
- `evidence/oh-source-excerpts.txt`: PrepareTerminate, CheckAppRunningRecordIsExist, CloseUIAbility.
- `evidence/second-process-cost.txt`, `evidence/trampoline-keys.txt`.
- `results.json`.
