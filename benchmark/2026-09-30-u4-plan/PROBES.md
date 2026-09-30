# Two scheduled U3 experiments, prepared offline

These temporary JARs are **not J5, not U4, and not repairs**. They derive from
pinned J3 `75c2068c`; run before U4 on a restored U3 board. Do not place them over
J5 and call that a single-variable probe. Artifacts are outside git at
`bms/src/.work/u4-probes/{A-observe,B-app-theme}/oh-adapter-runtime.jar`;
full SHA/tool inputs are in `probes/build-receipt.json`.

- A `e904a2f9...`: VLC logs ApplicationInfo theme without changing it; Termux gets
  a transparent IActivityClientController diagnostic forwarding proxy.
- B `3360482f...`: identical forwarding/logging, except VLC's ApplicationInfo.theme
  becomes **0x7f1402ec** (its APK's Onboarding theme). APK, ActivityInfo, resources,
  inflater, native and boot are not edited. No generic resource fallback.
- Both add one class `adapter.diagnostics.U4Probe` and two calls in the existing
  AppSchedulerBridge class. Every other original DEX class is unchanged modulo
  smali's encoded-default-boolean normalization. A/B differ only in the new
  helper's theme-toggle constant and consequent D8 code.

## Source / recipe, and why the observation point changed

The accepted B7 recipe is
`westlake-harness-walls/benchmark/2026-09-29-bms-link-entry-walls/build.py`, commit
`c83d80eb43e67c0c688221b7d7145e3f07b7b371`: compile one helper, merge DEX, add exact
calls, disassemble output and prove changed-existing classes. The new build uses
that procedure with source-anchored fail-closed substitutions. Forwarding and
InvocationTargetException unwrapping follow that tree's
`bms/src/adapter/framework/activity/java/ActivityManagerBindProxy.java`.

The verified source finish boundary is
`bms/src/adapter/framework/activity/java/ActivityClientControllerAdapter.java:274`:
markDestroying → findOhToken → nativeTerminateAbilityByTokenAddr → return true.
**That class is in the boot layer, not J3**. The first build correctly failed
when trying to find it in runtime DEX. We did not patch boot classes: the final
probe wraps the controller supplied by J3 AppSchedulerBridge to
LaunchActivityItem.obtain (original getInstance → move-result v39). Every call
forwards to the original object, including asBinder; return values and thrown
causes are preserved. Only com.termux is wrapped. JVM forwarding tests are not
proof that the actual Android caller will use this controller; absence of the
marker on device is **unknown**, not evidence of a different finish caller.

`probes/build.sh` runs dockbuild with existing image `a2hlab-b5-java:24.04`, pinned
J3 input and existing B7 javac/D8/smali inputs. The initial unsuffixed image tag
failed before building; corrected to the local :24.04 image. Source/build logs
and input hashes are retained. Do not rebuild J3/J5 production artifacts in place.
On a new machine copy the declared J3/tool inputs first and use a fresh out path.

## Runnable window (outer release + lock required)

Native/installer/boot remain U3 throughout; 61b is a proposed target, not an
assigned window while USB is disconnected. Total window <=30 minutes. Acquire
and confirm its full-serial lock. Capture U3 fingerprint, boot and JAR mount stack,
then run HW/ZZ baseline and clean VLC+Termux baseline with master batch. Known
random control flips require three repeats. Do not run any of this now.

Local-only readiness (already exercised; no HDC):

```sh
python3 benchmark/2026-09-30-u4-plan/probes/run.py --variant A-observe \
  --serial 61b0657200000000000000000324012c --run-id dry-a
```

Future VM commands from this worktree, once U3 is confirmed and lock held:

```sh
python3 benchmark/2026-09-30-u4-plan/probes/run.py --variant A-observe \
  --serial "$SERIAL" --run-id probe-a-1 --execute
python3 benchmark/2026-09-30-u4-plan/probes/run.py --variant B-app-theme \
  --serial "$SERIAL" --run-id probe-b-1 --execute
# Repeat the A/B pair with fresh run IDs to obtain three clean trials each.
```

The runner verifies J3 in shell and appspawn-x root, mounts **one extra layer**
without removing J2/J3, verifies the candidate in both views, runs master batch
with reinstall/hilog20/shots5,20/focus-check, and unmounts **only that owned top
layer** in finally. It restores the exact old mount stack and J3 SHA. It never
restarts foundation or kills the parent. Boot/lock loss, competing top mount,
daemon disappearance or failed readback => rollback **unverified**, halt and
report, do not strip another owner's layer. Uploaded diagnostic files remain as
evidence; they are not active after rollback. Timeout can leave an app process:
read process table, cold-stop that test app using batch's existing cleanup before
release and recheck unified state; no broad kill command.

Results under `runs/<probe-id>/apps-<serial>/<serial>/{vlc,termux}`. Preserve
`facts.txt` verbatim, t20 images and `overlay-receipt.json`. Compare A/B with
`scripts/lab/compare_runs.py`; only the runtime JAR path should differ, no reboot,
same APK and clean-install mode. A vs original U3 validates observer effect;
A vs B tests the single theme intervention. Restore U3 after each run and run
final HW screenshot/identity readback, then unlock. Do not leave the probes resident.

## VLC decision table

Evidence: N3 `evidence/vlc-theme-graph.json`, APK `c493c167...`; Onboarding's
0x7f1402ec parent chain defines background_default **0x7f040072**, while
Transparent **0x7f1402f9** / Empty **0x7f140278** do not. U2 log has correct
ActivityInfo at 36762/36766; inflation at 47600 reports Transparent. This is
not proof of a broken native resource parser.

Required observations: `[U4-VLC]` old/new IDs and appInfo identity; launch
ActivityInfo theme/class; full first inflate exception/theme chain; t20 and
process facts. Do not log Intent contents or accounts.

| Outcome | Interpretation / next action |
|---|---|
| A reproduces Transparent attr failure; B retains same ActivityInfo and only app theme changes; >=2/3 B runs pass that precise inflate wall while A fails | Application-theme-derived context participates in failure. Next trace the inflater/wrapper that consumes ApplicationInfo; this does **not** identify that object or authorize shipping the override |
| B marker confirms changed ApplicationInfo, launch still correct, but exact Transparent/attr failure remains in 3/3 | The early appInfo theme alone is insufficient (cached context, later overwrite or another wrapper); reject this proposed repair and investigate later selection |
| Wrong marker, no observed launch theme, first wall moves earlier, observer A changes baseline, or inconsistent outcomes | unknown; keep all three trials, no parser/Context root-cause assertion |
| B passes inflate but fails later | checkpoint passage only, not lit unless reviewed t20 shows VLC's own screen |

The helper intentionally does **not** replace inflater factories or write a fake
attribute. This intervention is cheaper than new boot tracing, and discriminates
the app-theme source hypothesis without pretending to observe every Context.

## Termux decision table

U3 archived log: service instantiated (18550), LocalBinder connected (18551),
finishActivity→OH TerminateAbility rc0 (18561). No caller stack, so PTY, renderer
and bind failure theories are unproved.

Required: `[U4-TERMUX] controller proxy installed`, `[U4-TERMUX-FINISH]` with
token identity/result code/thread, following `U4 finish caller` stack up to the
first app frame; correlate same PID/time with bindService and unchanged
TerminateAbility rc. The proxy records synchronously on the calling thread and
forwards without suppressing finish. Capture three A trials (B is unnecessary).

| Outcome | Interpretation / next action |
|---|---|
| Stack contains com.termux caller immediately above Activity.finish, same PID/token sequence, original delegate rc0 | App initiated finish; inspect **that actual method/branch in the pinned APK/source**, not a guessed permission or PTY workaround |
| Stack instead shows adapter/framework caller with no Termux caller | Framework/adapter initiated; inspect that frame and its condition, preserve original exception |
| OH finish observed without marker, proxy not installed, token/PID mismatch, or lost stack | unknown / different path or probe coverage failure; do not conclude the app did not call finish |
| Marker but no corresponding delegate completion, or A causes a new exception/control failure | Observer invalid; immediate diagnostic-layer rollback, keep baseline classification |

Success here means **caller identified**, not Termux lit. Neither experiment
changes U4 predictions until the observations and screenshots are reviewed.
