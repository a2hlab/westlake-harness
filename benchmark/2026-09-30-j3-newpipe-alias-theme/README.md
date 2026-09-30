# J3 — NewPipe bind-cause diagnostic + activity-alias target theme (base J2 0715c964)

cc-t3, 2026-09-30. Build worktree `westlake-harness-walls` (feat/bms-walls); one JAR increment on
J2 0715c964. **sha256 = `75c2068ca9818ea8a61cd2d7e258ef70b36fb426c87036f2f8e2c472d47e6697`**
(walls build-result-j3.json; jar at `vm-copies/j3-75c2068c/`). changed_existing_classes =
`{AppSchedulerBridge, PackageManagerProjectionProxy}` — still the two injection targets; both J3 fixes
are added classes / a new injection into an already-changed target.

## What was wrong before (evidence first)

The outer loop asked for three things. Reading the **ground-truth J1-final 5ea hilogs** (not code
structure) overturned two prior routing guesses about the theme wall.

### ① NewPipe PlayerService in-process bind still ITEs after the "android" package synthesis
J2's `AndroidFrameworkPackage` answers `getPackageInfo("android")` (cc-wiki's diagnosis), yet the outer
loop reports the in-process bind still throws an `InvocationTargetException` in the same millisecond.
The old failure print in `ActivityManagerBindProxy.postInProcessBind` was one line
(`[B8-AMB] in-process bind failed for <comp>: <t>`) where `<t>` is the outer ITE from the reflective
`onCreate`/`onBind` invoke, so **the real internal cause was hidden**.

Fix (diagnostic): `dumpBindFailure(comp, t)` walks the whole `getCause()` chain and prints the ROOT
cause's top 5 stack frames. The actual NewPipe fix follows once a board run shows the chain.
(`ActivityManagerBindProxy` is an added helper, so this source edit lands directly in the jar.)

### ② "vlc/fd-api theme" is TWO different walls — only fd-api is JAR-layer
I routed vlc/fd-api first as "app setTheme (non-JAR)", then corrected to "ActivityClientRecord seam
(JAR)". Both were wrong. The J1-final 5ea hilogs settle it:

**vlc — NOT JAR (resource layer).** `[B47-SLA]` and `[G2.5-SLA-PRE]` both show OnboardingActivity's
`activityInfo.theme = 0x7f1402ec` flowing INTO `LaunchActivityItem` — resolveActivityTheme already put
the correct theme on the launched Activity. The crash is a *nested forced* `ContextThemeWrapper`
(`TintContextWrapper.setTheme`) under **Theme.VLC.Transparent (0x7f1402f9)** → parent
Theme.AppCompat.Empty, where VLC attr `0x7f040072` (index 13) fails to resolve in OH's resource system.
A runtime JAR cannot make a native-unresolvable theme attr resolve → **resource-projection layer
(libresourcemanager / OhResourceProjection); route to the resource lane, not cc-t3.**
Evidence: `benchmark/2026-09-30-j1final-5ea/runs/j1final-5ea/5ea.../vlc/hilog.txt`
(`Failed to resolve attribute at index 13: 0x7f040072, theme={... Theme.VLC.Transparent ...}`).

**fd-api (com.termux.api) — JAR-fixable (the real find).** `[B5-ALIAS] alias=TermuxAPILauncherActivity
target=TermuxAPIMainActivity ordinary=false`: the launcher is an **activity-alias**. OH launches the
alias; `buildActivityInfoFromAbility → resolveActivityTheme` resolves the ALIAS's theme
(`0x1030237` = @android:style/Theme.Translucent.NoTitleBar, which makes the launcher invisible);
`LaunchActivityAliasProjection.apply` then rewrites the class to the TARGET (`TermuxAPIMainActivity`, an
`AppCompatActivity`) **but leaves the alias's non-AppCompat theme** (its own comment says theme is
untouched). AppCompat's onCreate then throws `IllegalStateException: You need to use a Theme.AppCompat
theme (or descendant)`. There is no `[B47-SLA]` for the target because it is not a separate launch — the
alias launch instantiates the target.
Evidence: `benchmark/2026-09-30-j1final-5ea/runs/j1final-5ea/5ea.../fd-api/hilog.txt`.

Fix: a NEW helper `AliasTargetTheme.apply(ActivityInfo)` re-resolves the theme for the TARGET
(`ManifestJsonFallback.activityTheme(pkg, targetActivity)`, own-or-application AppCompat theme) and sets
`launch.theme`. It is injected in `AppSchedulerBridge` immediately AFTER the existing
`LaunchActivityAliasProjection.apply` call (same ActivityInfo register). A `[B8-ALIASTHEME] <target>
theme re-resolved 0x1030237 -> 0x<X>` log confirms the swap on-board; an else-branch logs "unchanged"
if the target inherits the same theme (self-diagnosing board run).

**Build trap that forced the helper design.** `LaunchActivityAliasProjection` ships in the b5 baseline
and is in build.py's `ALREADY_SHIPPED` set, so the build KEEPS the baseline copy and SKIPS a recompiled
one (it is compiled only so callers link). A first J3 build (sha `3cfad314…`) edited that file directly
and the change was silently dropped — `changed_existing` stayed 2 and `LaunchActivityAliasProjection`
was neither added nor changed, which caught it. The real J3 (`75c2068c…`) instead adds a new helper +
one injection into AppSchedulerBridge (already a changed target), so `changed_existing` stays 2 and the
fix is actually present. Rule: **a baseline-shipped class cannot be changed by editing its source; add a
new helper and inject a call.**

### ③ Freeze draft — split blobs re-confirmed + J1-final/J2 re-verify evidence
The 3 split files' git blobs are unchanged by J3 (J3 touches `ActivityManagerBindProxy` + adds
`AliasTargetTheme`; `LaunchActivityAliasProjection` reverted to baseline). Each freeze entry now carries
`split_reverify_j1final` citing the concrete J1-final 5ea signal + the note that J2 carried the same
splits with no regression. See `benchmark/2026-09-30-jar-freeze-inventory/frozen-entries-draft.json`.

## The rule this round sets
**Route a wall by reading its hilog, never by code structure.** The theme cluster took three guesses;
only the ground-truth `[B47-SLA]`/`[G2.5-SLA-PRE]`/crash-theme lines settled that "projected the correct
ActivityInfo" (JAR can do) and "resource system resolves a forced-theme attr" (JAR cannot) are different
layers — and that an activity-alias needs its TARGET's theme, not the alias's.

## Board verify (pending outer-loop scheduling)
- **fd-api**: expect `[B8-ALIASTHEME] com.termux.api.activities.TermuxAPIMainActivity theme re-resolved
  0x1030237 -> 0x<AppCompat>` and TermuxAPIMainActivity past the AppCompat gate (lit or a new deeper
  wall). If it logs "unchanged", the app theme is itself non-AppCompat and the wall moves to resources.
- **newpipe**: read the `[B8-AMB] ... caused by: ...` chain to name the real playback-bind cause.
- **Protected group + HW**: no regression (same 17+HW set as J1-final).
- **vlc**: unchanged (routed out of JAR to the resource lane).
