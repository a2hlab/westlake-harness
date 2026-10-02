# Who terminated the activity: fd-saber + x alive-white

#90, offline, no board (window4 running — not touched). Follow-up to `u13-white-saber-x`: both keys publish a window
but render ~0 frames because the activity ends up `mFinished=true, mWindowAdded=false` before adding a decor. This traces
*who* finishes it. (`evidence/who-terminates.txt` has the two timelines with hilog line refs.)

## ① x — app trampoline self-finish; the gap is ours (we don't bring up the next activity)
`com.twitter.android.StartActivity` is a **MAIN / category-HOME trampoline**: it `startActivity(com.twitter.x.lite.XLiteActivity)`
then `finish()`s itself — normal Android behavior. In the log:
- `AMS: CloseUIAbility com.twitter.android/.StartActivity` + `OH_ACCAdapter finishActivity: OH TerminateAbility(0x7f3387f140) rc=0→rc=22`
  with `TerminateAbilityWithFlag verificationAllToken failed` (the finishing trampoline token can't be verified — symptom).
- **Simultaneously** `AMS: PendingSessionActivation / RequestSceneSession abilityName:com.twitter.x.lite.XLiteActivity` —
  the *real* next activity is requested (new SceneSession 952).
- But the finished trampoline reaches `RESUMED` already `mFinished=true, mWindowAdded=false, decorClass=null`, then the
  **process relaunches** (2nd `ensureBindApplication`, pid 9779). XLiteActivity never attaches a decor/window with content.

**Verdict:** the finish is the **app's own trampoline** (`StartActivity.finish()`, normal); **we fail to carry the
hand-off to the real activity** — XLiteActivity is requested but the process relaunches instead of bringing it up with
content → white. This confirms the dispatch hypothesis ("splash/trampoline normal behavior, we didn't bring up the next
Activity"). `verificationAllToken failed` is a symptom of our token/mission-record handling on the finishing trampoline,
not an AMS-initiated kill. (AOSP: a trampoline's `startActivity(real); finish();` brings the real activity up in the same
task; here the hand-off is lost across our relaunch.)

## ② fd-saber — single activity, terminated pre-window by the adapter/AMS token path (not a proven Flutter self-finish)
fd-saber has **one** activity (`com.adilhanney.saber.MainActivity`) and **no** trampoline / next-activity (no
`PendingSessionActivation` for a second activity). So its finish **cannot** be "startActivity(next)+finish". The sequence:
- `OH_AppSchedulerAdapter ScheduleLaunchAbility MainActivity … want.action=action.system.home token=0x7f3387f140` →
  `AFTER scheduleTransaction OK`.
- `AMS: CloseUIAbility com.adilhanney.saber/.MainActivity`, **`callerRecordList is empty`**, `OH_ACCAdapter finishActivity:
  OH TerminateAbility(0x7f3387f140) rc=0`, then `StartAbilityInner verificationAllToken failed` /
  `StartAbilityByFreeInstall error:2097205` — **around launch, before `performCreate`**.
- `performCreate MainActivity` then `RESUMED` on a *different* token (`Binder@7f79af4`), but `mFinished=true,
  mWindowAdded=false, decorClass=null`.

**Verdict:** **not** a Flutter self-finish — there is no Flutter-abandon marker, and the OpenGLWrapper / `EglWrapperLayer
Init Failed` load failures are concurrent, not the finisher. The OH ability token is terminated via the **adapter/AMS
token-verification path** (`callerRecordList is empty` → `verificationAllToken failed`), which leaves the Java activity
already-finished when it reaches RESUMED, so it never adds its window → white.

### `[B8-IMPELLER] EnableImpeller=false` source
Not in `bms/src` and not in the runtime `18763dd4` `.so` strings — it is emitted by a **B8 bind-fix** (the compiled
bind-fix layer, `oh-adapter-runtime.jar` family, same `B8*` layer as `[B8-WEBVIEW]`/`[B8-AMB]`). It forces Flutter **off
Impeller** (Vulkan — `load libvulkan.so failed`, unsupported on route-A) **onto the GL backend**; but GL also fails to
load (`OpenGLWrapper: Failed to load GLES library`), so Flutter has no working renderer — no frames to draw. This explains
why there is nothing to draw, but it is **not shown to be what finishes the activity** (that is the token path above).

## Common signature (discriminating vs lit)
Both: launch intent **category HOME** (not LAUNCHER); AMS `callerRecordList is empty` + `verificationAllToken failed` on
the OH ability token; the Java activity reaches `RESUMED` but `mFinished=true, mWindowAdded=false, decorClass=null`. Lit
refs (helloworld/zigzag) have **`verificationAllToken failed` = 0** (`u13-white-saber-x`), so this signature is
discriminating. It points at an **adapter/AMS mission/caller-record (token-verification) gap**, common to both; x
additionally needs the trampoline → real-activity hand-off.

## ③ Minimal on-board experiment (≤10 min; for a U14/U15 window; do not open a window)
**Goal:** definitively attribute each finish — app `Activity.finish()` vs adapter/AMS terminate — and (x) confirm the
lost trampoline hand-off.
- **Instrument (1 line, behind a flag):** in `OH_ACCAdapter.finishActivity(...)` add `new Throwable("WHO-FINISH").printStackTrace()`
  (or `Thread.dumpStack()`), gated by a debug prop so it only logs; rebuild the runtime/JAR for the experiment image.
- **Run:** relaunch **x** and **fd-saber** on 61b, 90 s hilog each (ride a U14/U15 window; no dedicated lock).
- **Criteria:**
  - If the `WHO-FINISH` stack shows **app code** (`…StartActivity.onCreate → Activity.finish`) → **app self-finish** —
    expected for x (trampoline). Then also assert: does `XLiteActivity` reach `performCreate` **with `mWindowAdded=true`**
    in the same (non-relaunched) process? If **no** → the trampoline hand-off is the gap (fix target).
  - If the stack shows **the adapter/AMS terminate path with no app frame** (token-verification / `verificationAllToken
    failed` → terminate) → **adapter/AMS finish** — expected for fd-saber (single activity). Then the fix target is the
    mission/caller-record so the token verifies and the window attaches.
- **Fallback (no instrumented image):** co-run a known-lit app (helloworld) in the same window and confirm it has
  `verificationAllToken failed = 0` and `mWindowAdded=true` while x/fd-saber have the failure — i.e., reproduce the
  discriminator on the current image (purely read-only; no code change), which supports the token-path reading without
  the stack.
- **Rollback:** the instrumentation is log-only behind a prop; drop the prop / revert the one line.

## This round's rule
"Who finishes" is answered by *when* the terminate fires relative to `performCreate` and by whether a **next activity** is
requested: x terminates its trampoline while requesting the real activity (app finish, lost hand-off); fd-saber terminates
its only activity **before** `performCreate` with `callerRecordList empty` (adapter/AMS token path). A concurrent failure
(here GL/Vulkan not loadable) is not automatically the finisher — attribute the finish to the call that actually fires it.

## Files
- `evidence/who-terminates.txt` — the two timelines (hilog line refs), the common signature, the `[B8-IMPELLER]` source.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board (window4 running — untouched); no push. The attribution is static from the U13 hilogs; the final
app-vs-adapter proof for fd-saber needs the ③ instrumented run. Sources read read-only: the U13 run hilogs
(`westlake-harness-u7-executor/.../window2-61b`), the runtime `18763dd4` (`westlake-inputs/generations`), the adapter
source (`westlake-harness/bms`).
